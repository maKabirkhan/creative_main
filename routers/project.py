from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from app.helpers.security import get_current_user
from app.schemas.project import ProjectResponse, CreateProjectRequest
from app.helpers.validators import validate_required_field
from app.helpers.db import supabase

router = APIRouter()


PROJECT_LIMITS = {
    "free": 5,
    "starter": 15,
    "professional": 25,
    "agency": float('inf'),  # Unlimited
    "enterprise": float('inf')  # Unlimited
}

def get_user_current_plan(user_id: str) -> str:
    """
    Get the user's current active subscription plan.
    Returns 'free' if no active subscription found.
    """
    response = (
        supabase.table("subscriptions")
        .select("tier, end_date, status")
        .eq("user_id", user_id)
        .order("start_date", desc=True)
        .limit(1)
        .execute()
    )

    if not response.data:
        return "free"

    sub = response.data[0]
    
    # Check if subscription is still active
    end_date = datetime.fromisoformat(sub["end_date"].replace("Z", ""))
    is_active = end_date > datetime.utcnow() and sub.get("status") == "active"

    return sub["tier"] if is_active else "free"


def reset_projects_count(user_id: str):
    """
    Reset the lifetime projects created counter to 0.
    This is called when a user upgrades their subscription.
    """
    print(f"🔄 Resetting projects_count for user {user_id}")
    
    try:
        result = supabase.table("users") \
            .update({"projects_count": 0}) \
            .eq("id", user_id) \
            .execute()
        
        print(f"✅ Counter reset successful")
        print(f"   Rows affected: {len(result.data) if result.data else 0}")
    except Exception as e:
        print(f"❌ Error resetting projects_count: {str(e)}")
        raise


def get_projects_count(user_id: str) -> int:
    """
    Get the lifetime count of projects created by user.
    This reads from the users table's projects_count field.
    """
    try:
        response = supabase.table("users") \
            .select("projects_count") \
            .eq("id", user_id) \
            .execute()
        
        if not response.data:
            print(f"⚠️ WARNING: No user found with id {user_id}")
            return 0
        
        count = response.data[0].get("projects_count", 0)
        print(f"📊 Current projects_count for user {user_id}: {count}")
        return count if count is not None else 0
    except Exception as e:
        print(f"❌ Error getting projects_count: {str(e)}")
        return 0


def increment_projects_created(user_id: str) -> int:
    """
    Increment the lifetime projects created counter.
    Returns the new count.
    """
    # Get current count
    current_count = get_projects_count(user_id)
    new_count = current_count + 1
    
    print(f"🔢 Incrementing projects_count for user {user_id}")
    print(f"   Current count: {current_count}")
    print(f"   New count: {new_count}")
    
    # Update the counter
    try:
        result = supabase.table("users") \
            .update({"projects_count": new_count}) \
            .eq("id", user_id) \
            .execute()
        
        print(f"✅ Update result: {result.data}")
        
        if not result.data:
            print(f"⚠️ WARNING: No rows updated for user {user_id}")
            # Verify the user exists
            user_check = supabase.table("users").select("id").eq("id", user_id).execute()
            print(f"   User exists: {bool(user_check.data)}")
    except Exception as e:
        print(f"❌ Error updating projects_count: {str(e)}")
        raise
    
    return new_count


def check_project_limit(user_id: str, current_plan: str) -> tuple[bool, int, int]:
    """
    Check if user has reached their LIFETIME project creation limit.
    Returns: (can_create: bool, projects_created: int, limit: int)
    """
    projects_created = get_projects_count(user_id)
    limit = PROJECT_LIMITS.get(current_plan, 5)  # Default to free plan limit
    
    can_create = projects_created < limit
    
    return can_create, projects_created, limit


@router.post("/projects", response_model=ProjectResponse)
def create_project(
    request: CreateProjectRequest, 
    current_user: dict = Depends(get_current_user)
):
    """Create a new project for the authenticated user"""

    validate_required_field(request.name, "name")
    validate_required_field(request.brand, "brand")
    validate_required_field(request.product, "product")
    validate_required_field(request.product_service_type, "product_service_type")
    validate_required_field(request.category, "category")
    validate_required_field(request.market_maturity, "market_maturity")
    validate_required_field(request.campaign_objective, "campaign_objective")
    validate_required_field(request.value_propositions, "value_propositions")
    validate_required_field(request.kpis, "kpis")
    validate_required_field(request.kpi_target, "kpi_target")

    try:
        user_id = current_user["id"]
        
        # 🔒 Check user's subscription plan and LIFETIME project limit
        current_plan = get_user_current_plan(user_id)
        can_create, projects_created, limit = check_project_limit(user_id, current_plan)
        
        if not can_create:
            limit_text = "unlimited" if limit == float('inf') else str(limit)
            raise HTTPException(
                status_code=403,
                detail={
                    "message": f"Lifetime project limit reached for {current_plan} plan",
                    "current_plan": current_plan,
                    "projects_created_lifetime": projects_created,
                    "plan_limit": limit_text,
                    "upgrade_required": True,
                    "note": "This limit counts all projects ever created, even if deleted"
                }
            )
        
        # 🔎 Check if project with same name already exists for this user
        existing_project = supabase.table("projects") \
            .select("id") \
            .eq("user_id", user_id) \
            .eq("name", request.name) \
            .execute()

        if existing_project.data and len(existing_project.data) > 0:
            raise HTTPException(
                status_code=400,
                detail=f"A project with the name '{request.name}' already exists for this user"
            )

        # Prepare project data
        project_data = {
            "user_id": user_id,
            "name": request.name,
            "brand": request.brand,
            "product": request.product,
            "product_service_type": request.product_service_type,
            "category": request.category,
            "market_maturity": request.market_maturity,
            "campaign_objective": request.campaign_objective,
            "value_propositions": request.value_propositions,
            "media_channels": request.media_channels,
            "kpis": request.kpis,
            "kpi_target": request.kpi_target,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }

        response = supabase.table("projects").insert(project_data).execute()

        if not response.data:
            raise HTTPException(status_code=400, detail="Failed to create project")

        # ✨ INCREMENT the lifetime counter AFTER successful creation
        new_count = increment_projects_created(user_id)

        created_project = response.data[0]
        
        # 📊 Get updated project limits after creation
        limit_text = "unlimited" if limit == float('inf') else limit
        remaining = "unlimited" if limit == float('inf') else max(0, limit - new_count)
        
        # Return project with updated limit info
        return {
            **created_project,
            "plan_info": {
                "current_plan": current_plan,
                "projects_created_lifetime": new_count,
                "projects_limit": limit_text,
                "projects_remaining": remaining
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while creating the project: {str(e)}"
        )


# Optional: Add an endpoint to check project limits
@router.get("/projects/limits")
def get_project_limits(current_user: dict = Depends(get_current_user)):
    """Get the user's lifetime project creation count and limits"""
    user_id = current_user["id"]
    current_plan = get_user_current_plan(user_id)
    can_create, projects_created, limit = check_project_limit(user_id, current_plan)
    
    limit_text = "unlimited" if limit == float('inf') else limit
    
    return {
        "current_plan": current_plan,
        "projects_created_lifetime": projects_created,
        "plan_limit": limit_text,
        "can_create_more": can_create,
        "remaining": "unlimited" if limit == float('inf') else max(0, limit - projects_created)
    }



@router.get("/projects")
def get_user_projects(
    project_id: str = Query(default=None),
    current_user: dict = Depends(get_current_user)
):
    """
    Get all projects for the authenticated user,
    or a specific project if project_id is provided.
    """
    try:
        query = supabase.table("projects").select("*").eq("user_id", current_user["id"])

        if project_id:
            query = query.eq("id", project_id)

        response = query.order("created_at", desc=True).execute()

        if project_id:
            if not response.data:
                raise HTTPException(status_code=404, detail="Project not found for this user.")
            return {"project": response.data[0]}

        return {
            "projects": response.data,
            "count": len(response.data)
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while fetching projects: {str(e)}"
        )

@router.put("/projects/{project_id}", response_model=ProjectResponse)
def update_project(
    project_id: int,
    request: CreateProjectRequest,
    current_user: dict = Depends(get_current_user)
):
    """Update an existing project (only by the creator)."""
    try:
        existing = supabase.table("projects").select("*").eq("id", project_id).eq("user_id", current_user["id"]).execute()
        if not existing.data:
            raise HTTPException(status_code=404, detail="Project not found or you don't have permission to update it.")

        update_data = request.dict(exclude_unset=True)
        update_data["updated_at"] = datetime.utcnow().isoformat()

        response = supabase.table("projects").update(update_data).eq("id", project_id).eq("user_id", current_user["id"]).execute()

        if not response.data:
            raise HTTPException(status_code=400, detail="Failed to update project")

        return ProjectResponse(**response.data[0])

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while updating the project: {str(e)}"
        )

@router.delete("/projects/{project_id}")
def delete_project(
    project_id: int,
    current_user: dict = Depends(get_current_user)
):
    """Delete a project (only by the creator)."""
    try:
        existing = supabase.table("projects").select("id").eq("id", project_id).eq("user_id", current_user["id"]).execute()
        if not existing.data:
            raise HTTPException(status_code=404, detail="Project not found or you don't have permission to delete it.")

        response = supabase.table("projects").delete().eq("id", project_id).eq("user_id", current_user["id"]).execute()

        if not response.data:
            raise HTTPException(status_code=400, detail="Failed to delete project")

        return {"message": "Project deleted successfully", "deleted_id": project_id}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while deleting the project: {str(e)}"
        )