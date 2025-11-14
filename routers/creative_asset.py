from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from datetime import datetime
from typing import List
from app.helpers.security import get_current_user
from app.helpers.db import supabase
import boto3
import uuid
import os
import httpx

router = APIRouter()

s3_client = boto3.client(
    "s3",
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    region_name=os.getenv("AWS_REGION")
)
S3_BUCKET = os.getenv("AWS_S3_BUCKET")

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "gif", "mp3", "wav"}

def get_asset_type(extension: str) -> str:
    if extension in {"jpg", "jpeg", "png", "gif"}:
        return "IMAGE"
    elif extension in {"mp3", "wav"}:
        return "AUDIO"
    else:
        return None

@router.post("/")
def create_creative_asset(
    project_id: int = Form(...),
    file_name: List[str] = Form(None), 
    video_name: List[str] = Form(None),
    text_name: List[str] = Form(None),
    ad_copy: List[str] = Form(None),
    voice_script: List[str] = Form(None),
    file_url: List[str] = Form(None),
    files: List[UploadFile] = File(None),
    meta_data: List[str] = Form(None),
    current_user: dict = Depends(get_current_user),
):
    """Upload creative assets (image/audio/video/text) linked to a Project"""

    # ============================================
    # VALIDATION PHASE - All checks before any processing
    # ============================================
    
    # 1. Validate project ownership
    project_resp = (
        supabase.table("projects")
        .select("id, user_id")
        .eq("id", project_id)
        .eq("user_id", current_user["id"])
        .execute()
    )
    if not project_resp.data:
        raise HTTPException(
            status_code=404, 
            detail=f"Project {project_id} not found or not owned by user"
        )

    # 2. Check subscription tier
    subscription_resp = (
        supabase.table("subscriptions")
        .select("tier, status")
        .eq("user_id", current_user["id"])
        .eq("status", "active")
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    
    user_tier = subscription_resp.data[0]["tier"].lower() if subscription_resp.data else "free"
    
    if user_tier == "free" and file_url:
        raise HTTPException(
            status_code=403, 
            detail="Video uploads are not available on the free plan. Please upgrade to access this feature."
        )

    if not files and not file_url and not ad_copy:
        raise HTTPException(
            status_code=400, 
            detail="No creative assets provided. Please provide at least one of: files, file_url, or ad_copy"
        )

    if files:
        if not file_name:
            raise HTTPException(
                status_code=400, 
                detail="file_name is required when uploading files"
            )
        
        if len(file_name) != 1 and len(file_name) != len(files):
            raise HTTPException(
                status_code=400, 
                detail=f"file_name count mismatch: provided {len(file_name)} names for {len(files)} files. Provide either 1 name for all files or {len(files)} names."
            )
        for file in files:
            extension = file.filename.split(".")[-1].lower()
            file_type = get_asset_type(extension)
            if file_type not in ["IMAGE", "AUDIO"]:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Invalid file type for '{file.filename}'. Only IMAGE or AUDIO files are allowed."
                )

    if file_url:
        if not video_name:
            raise HTTPException(
                status_code=400, 
                detail="video_name is required when providing file_url"
            )
        
        if len(file_url) > 1:
            raise HTTPException(
                status_code=400,
                detail=f"Only one video upload is allowed. You provided {len(file_url)} videos."
            )
        
        if len(video_name) != len(file_url):
            raise HTTPException(
                status_code=400, 
                detail=f"video_name and file_url count mismatch: provided {len(video_name)} names for {len(file_url)} URLs"
            )

    if ad_copy:
        if not text_name:
            raise HTTPException(
                status_code=400, 
                detail="text_name is required when providing ad_copy"
            )
        
        if len(ad_copy) > 1:
            raise HTTPException(
                status_code=400,
                detail=f"Only one text asset is allowed. You provided {len(ad_copy)} text assets."
            )
        
        if len(text_name) != len(ad_copy):
            raise HTTPException(
                status_code=400, 
                detail=f"text_name and ad_copy count mismatch: provided {len(text_name)} names for {len(ad_copy)} ad copies"
            )
        
        if voice_script and len(voice_script) > 1:
            raise HTTPException(
                status_code=400,
                detail="Only one voice_script is allowed per request"
            )

    total_assets = (len(files) if files else 0) + (len(file_url) if file_url else 0) + (len(ad_copy) if ad_copy else 0)
    if meta_data and len(meta_data) != total_assets:
        raise HTTPException(
            status_code=400,
            detail=f"meta_data count mismatch: provided {len(meta_data)} metadata entries for {total_assets} total assets"
        )

    
    creative_assets_to_insert = []

    if files:
        for idx, file in enumerate(files):
            extension = file.filename.split(".")[-1].lower()
            file_type = get_asset_type(extension)

            # Get name: use single name for all or specific name per file
            name_for_file = file_name[0] if len(file_name) == 1 else file_name[idx]

            # Upload to S3
            key = f"creative-assets/{uuid.uuid4()}.{extension}"
            s3_client.upload_fileobj(file.file, S3_BUCKET, key)
            uploaded_file_url = f"https://{S3_BUCKET}.s3.amazonaws.com/{key}"

            creative_assets_to_insert.append({
                "project_id": project_id,
                "type": file_type,
                "name": name_for_file, 
                "file_url": uploaded_file_url,
                "ad_copy": None,
                "voice_script": None,
                "meta_data": meta_data[idx] if meta_data and idx < len(meta_data) else None,
                "uploaded_at": datetime.utcnow().isoformat()
            })

    if file_url:
        file_offset = len(files) if files else 0
        creative_assets_to_insert.append({
            "project_id": project_id,
            "type": "VIDEO",
            "name": video_name[0],
            "file_url": file_url[0],
            "ad_copy": None,
            "voice_script": None,
            "meta_data": meta_data[file_offset] if meta_data and file_offset < len(meta_data) else None,
            "uploaded_at": datetime.utcnow().isoformat()
        })

    if ad_copy:
        file_offset = (len(files) if files else 0) + (len(file_url) if file_url else 0)
        creative_assets_to_insert.append({
            "project_id": project_id,
            "type": "TEXT",
            "name": text_name[0],
            "file_url": None,
            "ad_copy": ad_copy[0],
            "voice_script": voice_script[0] if voice_script and len(voice_script) > 0 else None,
            "meta_data": meta_data[file_offset] if meta_data and file_offset < len(meta_data) else None,
            "uploaded_at": datetime.utcnow().isoformat()
        })

    try:
        response = supabase.table("creative_assets").insert(creative_assets_to_insert).execute()
        return {
            "message": "Creative assets created successfully", 
            "assets": response.data,
            "count": len(response.data)
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Database error while creating assets: {str(e)}"
        ) 

@router.get("/{project_id}")
def list_creative_assets(
    project_id: str,
    current_user: dict = Depends(get_current_user)
):
    """List all creative assets for a project belonging to the authenticated user"""

    try:
        project_resp = supabase.table("projects").select("*") \
            .eq("id", project_id).eq("user_id", current_user["id"]).execute()

        if not project_resp.data:
            raise HTTPException(status_code=404, detail="Project not found or not owned by user")

        response = supabase.table("creative_assets").select("*") \
            .eq("project_id", project_id).order("uploaded_at", desc=True).execute()

        return {
            "assets": response.data,
            "count": len(response.data)
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while fetching creative assets: {str(e)}"
        )

from time import sleep

@router.put("/{project_id}")
def update_creative_assets(
    project_id: int,
    file_name: List[str] = Form(None),
    video_name: str = Form(None),  # Single value for YouTube
    text_name: str = Form(None),   # Single value for text
    ad_copy: str = Form(None),     # Single value for text
    voice_script: str = Form(None), # Single value for text
    file_url: str = Form(None),    # Single YouTube URL
    files: List[UploadFile] = File(None),
    meta_data: List[str] = Form(None),
    delete_asset_ids: str = Form(None),  # JSON string of IDs e.g., "[1,2,3]" or single ID "123"
    current_user: dict = Depends(get_current_user),
):
    """
    Update creative assets for a project.
    - For IMAGE/AUDIO: Can add multiple new files, delete existing ones
    - For VIDEO (YouTube): Only one video allowed - will replace if exists
    - For TEXT: Only one text asset allowed - will replace if exists
    - delete_asset_ids: JSON string of asset IDs to delete, e.g., "[1,2,3]" or single ID "123"
                       Supports all types: IMAGE/AUDIO/VIDEO/TEXT
    """
    
    # Parse delete_asset_ids from string to list of integers
    parsed_delete_ids = None
    if delete_asset_ids:
        try:
            # Try parsing as JSON array first
            import json
            parsed_delete_ids = json.loads(delete_asset_ids)
            if not isinstance(parsed_delete_ids, list):
                # If single value, convert to list
                parsed_delete_ids = [int(parsed_delete_ids)]
            else:
                # Ensure all elements are integers
                parsed_delete_ids = [int(id) for id in parsed_delete_ids]
        except (json.JSONDecodeError, ValueError):
            # Try parsing as single integer
            try:
                parsed_delete_ids = [int(delete_asset_ids)]
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail="delete_asset_ids must be a valid JSON array of integers (e.g., '[1,2,3]') or a single integer"
                )
    
    # Verify project ownership
    project_resp = (
        supabase.table("projects")
        .select("id, user_id")
        .eq("id", project_id)
        .eq("user_id", current_user["id"])
        .execute()
    )
    if not project_resp.data:
        raise HTTPException(
            status_code=404, 
            detail=f"Project {project_id} not found or not owned by user"
        )

    # Check subscription tier for video uploads
    subscription_resp = (
        supabase.table("subscriptions")
        .select("tier, status")
        .eq("user_id", current_user["id"])
        .eq("status", "active")
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    
    user_tier = subscription_resp.data[0]["tier"].lower() if subscription_resp.data else "free"
    
    if user_tier == "free" and file_url:
        raise HTTPException(
            status_code=403, 
            detail="Video uploads are not available on the free plan. Please upgrade to access this feature."
        )

    results = {
        "created": [],
        "updated": [],
        "deleted": []
    }

    # Check if user provided any data at all
    if not any([files, file_url, ad_copy, parsed_delete_ids]):
        raise HTTPException(
            status_code=400,
            detail="No data provided. Please provide at least one of: files, file_url, ad_copy, or delete_asset_ids"
        )
    
    # Validate dependencies between fields
    if file_name and not files:
        raise HTTPException(
            status_code=400,
            detail="files must be provided when file_name is specified"
        )
    
    if files and not file_name:
        raise HTTPException(
            status_code=400,
            detail="file_name is required when uploading files"
        )
    
    if video_name and not file_url:
        raise HTTPException(
            status_code=400,
            detail="file_url must be provided when video_name is specified"
        )
    
    if file_url and not video_name:
        raise HTTPException(
            status_code=400,
            detail="video_name is required when file_url is provided"
        )
    
    if text_name and not (ad_copy and voice_script):
        raise HTTPException(
            status_code=400,
            detail="Both ad_copy and voice_script must be provided when text_name is specified"
        )
    
    if (ad_copy or voice_script) and not text_name:
        raise HTTPException(
            status_code=400,
            detail="text_name is required when ad_copy or voice_script is provided"
        )
    
    if ad_copy and not voice_script:
        raise HTTPException(
            status_code=400,
            detail="voice_script must be provided when ad_copy is specified"
        )
    
    if voice_script and not ad_copy:
        raise HTTPException(
            status_code=400,
            detail="ad_copy must be provided when voice_script is specified"
        )

    # Handle asset deletion (supports all types: IMAGE/AUDIO/VIDEO/TEXT)
    if parsed_delete_ids:
        # Verify that all assets to be deleted belong to this project
        assets_to_delete = (
            supabase.table("creative_assets")
            .select("id, type, file_url")
            .eq("project_id", project_id)
            .in_("id", parsed_delete_ids)
            .execute()
        )
        
        if len(assets_to_delete.data) != len(parsed_delete_ids):
            found_ids = [asset["id"] for asset in assets_to_delete.data]
            missing_ids = [aid for aid in parsed_delete_ids if aid not in found_ids]
            raise HTTPException(
                status_code=404,
                detail=f"Assets with IDs {missing_ids} not found in project {project_id}"
            )
        
        for asset in assets_to_delete.data:
            if asset["file_url"] and asset["type"] in ["IMAGE", "AUDIO"]:
                # Extract S3 key from URL and delete from S3
                try:
                    s3_key = asset["file_url"].split(f"{S3_BUCKET}.s3.amazonaws.com/")[1]
                    s3_client.delete_object(Bucket=S3_BUCKET, Key=s3_key)
                except Exception as e:
                    # Log but don't fail if S3 deletion fails
                    print(f"Failed to delete S3 object: {e}")
        
        delete_response = (
            supabase.table("creative_assets")
            .delete()
            .in_("id", parsed_delete_ids)
            .execute()
        )
        results["deleted"].extend(delete_response.data)

    if files:
        for idx, file in enumerate(files):
            extension = file.filename.split(".")[-1].lower()
            file_type = get_asset_type(extension)
            
            if file_type not in ["IMAGE", "AUDIO"]:
                raise HTTPException(
                    status_code=400, 
                    detail="Only IMAGE or AUDIO allowed for file uploads"
                )

            name_for_file = file_name[0] if len(file_name) == 1 else (
                file_name[idx] if idx < len(file_name) else None
            )
            if not name_for_file:
                raise HTTPException(
                    status_code=400, 
                    detail="Not enough file_name values for files"
                )

            key = f"creative-assets/{uuid.uuid4()}.{extension}"
            s3_client.upload_fileobj(file.file, S3_BUCKET, key)
            uploaded_file_url = f"https://{S3_BUCKET}.s3.amazonaws.com/{key}"

            asset_data = {
                "project_id": project_id,
                "type": file_type,
                "name": name_for_file,
                "file_url": uploaded_file_url,
                "ad_copy": None,
                "voice_script": None,
                "meta_data": meta_data[idx] if meta_data and idx < len(meta_data) else None,
                "uploaded_at": datetime.utcnow().isoformat()
            }
            
            response = supabase.table("creative_assets").insert(asset_data).execute()
            results["created"].extend(response.data)

    if file_url:
        existing_video = (
            supabase.table("creative_assets")
            .select("id, file_url")
            .eq("project_id", project_id)
            .eq("type", "VIDEO")
            .execute()
        )

        video_data = {
            "project_id": project_id,
            "type": "VIDEO",
            "name": video_name,
            "file_url": file_url,
            "ad_copy": None,
            "voice_script": None,
            "meta_data": meta_data[0] if meta_data else None,
            "uploaded_at": datetime.utcnow().isoformat()
        }

        if existing_video.data:
            # Update existing video
            video_id = existing_video.data[0]["id"]
            response = (
                supabase.table("creative_assets")
                .update(video_data)
                .eq("id", video_id)
                .execute()
            )
            results["updated"].extend(response.data)
        else:
            response = supabase.table("creative_assets").insert(video_data).execute()
            results["created"].extend(response.data)

    if ad_copy:
        existing_text = (
            supabase.table("creative_assets")
            .select("id")
            .eq("project_id", project_id)
            .eq("type", "TEXT")
            .execute()
        )

        text_data = {
            "project_id": project_id,
            "type": "TEXT",
            "name": text_name,
            "file_url": None,
            "ad_copy": ad_copy,
            "voice_script": voice_script,
            "meta_data": meta_data[0] if meta_data else None,
            "uploaded_at": datetime.utcnow().isoformat()
        }

        if existing_text.data:
            text_id = existing_text.data[0]["id"]
            response = (
                supabase.table("creative_assets")
                .update(text_data)
                .eq("id", text_id)
                .execute()
            )
            results["updated"].extend(response.data)
        else:
            response = supabase.table("creative_assets").insert(text_data).execute()
            results["created"].extend(response.data)

    if not any([results["created"], results["updated"], results["deleted"]]):
        raise HTTPException(
            status_code=400, 
            detail="No creative assets provided for update"
        )

    return {
        "message": "Creative assets updated successfully",
        "results": results,
        "summary": {
            "created_count": len(results["created"]),
            "updated_count": len(results["updated"]),
            "deleted_count": len(results["deleted"])
        }
    }

@router.get("/images/{project_id}")
def list_project_images(
    project_id: str,
    current_user: dict = Depends(get_current_user)
):
    """List only IMAGE creative assets for a project belonging to the authenticated user"""
    
    max_retries = 3
    retry_delay = 1  # seconds
    
    for attempt in range(max_retries):
        try:
            # Verify project belongs to current user
            project_resp = supabase.table("projects")\
                .select("id")\
                .eq("id", project_id)\
                .eq("user_id", current_user["id"])\
                .execute()

            if not project_resp.data:
                raise HTTPException(
                    status_code=404, 
                    detail="Project not found or not owned by user"
                )

            # Fetch only image assets
            response = supabase.table("creative_assets")\
                .select("*")\
                .eq("project_id", project_id)\
                .eq("type", "IMAGE")\
                .order("uploaded_at", desc=True)\
                .execute()

            return {
                "images": response.data,
                "count": len(response.data)
            }

        except (httpx.ReadError, httpx.TimeoutException) as e:
            if attempt < max_retries - 1:
                print(f"Retry {attempt + 1}/{max_retries} after error: {e}")
                sleep(retry_delay)
                continue
            else:
                raise HTTPException(
                    status_code=503,
                    detail="Service temporarily unavailable. Please try again."
                )
        except HTTPException:
            raise
        except Exception as e:
            print(f"ERROR: {type(e).__name__}: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"An error occurred: {str(e)}"
            )
        
@router.post("/replace/{project_id}/{asset_id}")
def replace_image_asset(
    project_id: int,
    asset_id: int,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    """Replace an existing IMAGE asset with a new uploaded file (must belong to given project)"""
    
    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    asset_resp = (
        supabase.table("creative_assets")
        .select("id, project_id, type, file_url")
        .eq("id", asset_id)
        .execute()
    )
    if not asset_resp.data:
        raise HTTPException(status_code=404, detail="Asset not found")

    asset = asset_resp.data[0]

    if asset["project_id"] != project_id:
        raise HTTPException(status_code=400, detail="Asset does not belong to the given project")

    project_resp = (
        supabase.table("projects")
        .select("id")
        .eq("id", project_id)
        .eq("user_id", current_user["id"])
        .execute()
    )
    if not project_resp.data:
        raise HTTPException(status_code=403, detail="Project not owned by user")

    if asset["type"].lower() != "image":
        raise HTTPException(status_code=400, detail="Asset is not an IMAGE type")

    if not file.filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    
    extension = file.filename.split(".")[-1].lower()
    if extension not in {"jpg", "jpeg", "png", "gif", "webp"}:
        raise HTTPException(status_code=400, detail=f"File type .{extension} not allowed. Allowed types: jpg, jpeg, png, gif, webp")

    old_url = asset.get("file_url")
    if old_url:
        try:
            old_key = old_url.split(f"https://{S3_BUCKET}.s3.amazonaws.com/")[-1]
            s3_client.delete_object(Bucket=S3_BUCKET, Key=old_key)
        except Exception as e:
            print(f"Warning: Failed to delete old file: {str(e)}")
            
    try:
        new_key = f"creative-assets/{uuid.uuid4()}.{extension}"
        
        file.file.seek(0)
        
        s3_client.upload_fileobj(file.file, S3_BUCKET, new_key)
        new_file_url = f"https://{S3_BUCKET}.s3.amazonaws.com/{new_key}"

        update_resp = (
            supabase.table("creative_assets")
            .update({
                "file_url": new_file_url,
                "uploaded_at": datetime.utcnow().isoformat()
            })
            .eq("id", asset_id)
            .eq("project_id", project_id)  
            .execute()
        )

        if not update_resp.data:
            raise HTTPException(status_code=400, detail="Failed to update asset in database")

        return {
            "message": "Image asset replaced successfully", 
            "asset": update_resp.data[0]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to replace image: {str(e)}")