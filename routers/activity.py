from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime, timezone, timedelta
from app.helpers.db import supabase
from app.helpers.security import get_current_user
from dateutil import parser
import httpx

router = APIRouter()

def parse_datetime(dt_str: str):
    if not dt_str:
        return None
    try:
        return parser.isoparse(dt_str)
    except Exception:
        pass
    try:
        return datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S.%f%z")
    except Exception:
        pass
    try:
        return datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S%z")
    except Exception:
        return None

def human_readable_time(dt_str: str) -> str:
    dt = parse_datetime(dt_str)
    if not dt:
        return "unknown time"

    now = datetime.now(timezone.utc)
    delta = now - dt

    if delta < timedelta(minutes=1):
        return "just now"
    elif delta < timedelta(hours=1):
        minutes = delta.seconds // 60
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    elif delta < timedelta(days=1):
        hours = delta.seconds // 3600
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    else:
        days = delta.days
        return f"{days} day{'s' if days != 1 else ''} ago"

def normalize_timestamp_for_dedup(dt_str: str) -> str:
    parsed = parse_datetime(dt_str)
    if not parsed:
        return dt_str
    normalized = parsed.replace(microsecond=0)
    return normalized.isoformat()

from time import sleep

def supabase_query_with_retry(query_func, max_retries=3, delay=1):
    """Execute a Supabase query with retry logic for network errors"""
    for attempt in range(max_retries):
        try:
            return query_func()
        except (httpx.ReadError, httpx.ConnectError, httpx.TimeoutException) as e:
            if attempt < max_retries - 1:
                print(f"Network error on attempt {attempt + 1}/{max_retries}: {e}")
                sleep(delay)
                continue
            else:
                raise HTTPException(
                    status_code=503,
                    detail="Service temporarily unavailable. Please try again later."
                )
        except Exception as e:
            raise

# Then use it in your endpoint:
@router.get("/")
@router.get("/{project_id}")
def get_activity(project_id: str = None, user: dict = Depends(get_current_user)):
    user_id = user["id"]
    activities = []
    seen_creative_timestamps = set()

    # Fetch personas with retry
    persona_res = supabase_query_with_retry(
        lambda: supabase.table("personas").select("*").eq("user_id", user_id).execute()
    )

    for persona in persona_res.data or []:
        ts = persona.get("created_at") or datetime.now(timezone.utc).isoformat()
        activities.append({
            "event": "Audience defined",
            "timestamp": ts,
            "time_ago": human_readable_time(ts),
            "audience_name": persona.get("name", "Unnamed Audience")
        })

    # Fetch projects with retry
    def fetch_projects():
        project_query = supabase.table("projects").select("*").eq("user_id", user_id)
        if project_id:
            project_query = project_query.eq("id", project_id)
        return project_query.execute()
    
    project_res = supabase_query_with_retry(fetch_projects)

    for project in project_res.data or []:
        ts = project.get("created_at") or datetime.now(timezone.utc).isoformat()
        activities.append({
            "event": "Project created",
            "timestamp": ts,
            "time_ago": human_readable_time(ts),
            "project_name": project.get("name", "Untitled Project")
        })

        # Fetch creative assets with retry
        try:
            creative_res = supabase_query_with_retry(
                lambda: supabase.table("creative_assets").select("*").eq("project_id", project["id"]).execute()
            )
        except HTTPException:
            print(f"Warning: Failed to fetch creative assets for project {project['id']}")
            continue

        for creative in creative_res.data or []:
            ts = creative.get("created_at") or datetime.now(timezone.utc).isoformat()
            ts_normalized = normalize_timestamp_for_dedup(ts)
            if ts_normalized in seen_creative_timestamps:
                continue
            seen_creative_timestamps.add(ts_normalized)

            activities.append({
                "event": "Creative uploaded",
                "timestamp": ts,
                "time_ago": human_readable_time(ts),
                "creative_name": creative.get("name", "Unnamed Creative")
            })

    def sort_key(a):
        parsed = parse_datetime(a["timestamp"])
        return parsed if parsed else datetime.min.replace(tzinfo=timezone.utc)

    activities.sort(key=sort_key, reverse=True)

    return {
        "user_id": user_id,
        "project_id": project_id or None,
        "activities": activities
    }