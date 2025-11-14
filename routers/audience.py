from fastapi import APIRouter, HTTPException, Depends, Query, Body
from typing import Optional, Dict, Any
from app.helpers.security import get_current_user
from app.helpers.db import supabase
router = APIRouter()
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from typing import Optional, Dict, Any
from datetime import datetime

@router.get("/")
def get_audiences(
    current_user: dict = Depends(get_current_user),
    audience_id: Optional[int] = Query(None, description="Get a specific audience by ID")
):
    """
    Get all audiences related to the current user.
    
    - If `audience_id` is provided → return a specific audience (must belong to the user).
    - If not provided → return all audiences for the current user.
    """
    try:
        if audience_id:
            query = (
                supabase.table("audiences")
                .select("*")
                .eq("id", audience_id)
                .eq("user_id", current_user["id"])
                .execute()
            )

            if not query.data:
                raise HTTPException(status_code=404, detail="Audience not found")

            return {"audience": query.data[0]}

        # ✅ Get all audiences for this user
        query = (
            supabase.table("audiences")
            .select("*")
            .eq("user_id", current_user["id"])
            .order("created_at", desc=True)
            .execute()
        )

        return {"audiences": query.data, "count": len(query.data)}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while fetching audiences: {str(e)}"
        )


@router.put("/{id}")
def update_audience(
    id: int,
    payload: Dict[str, Any] = Body(..., description="Fields to update in audience"),
    current_user: dict = Depends(get_current_user),
):
    """
    Update an existing audience.
    - Only allows updating audiences belonging to the current user.
    """
    try:
        audience = (
            supabase.table("audiences")
            .select("user_id")
            .eq("id", id)
            .execute()
        )
        if not audience.data:
            raise HTTPException(status_code=404, detail="Audience not found")

        if audience.data[0]["user_id"] != current_user["id"]:
            raise HTTPException(status_code=403, detail="Not authorized to update this audience")

        payload["updated_at"] = datetime.utcnow().isoformat()

        response = (
            supabase.table("audiences")
            .update(payload)
            .eq("id", id)
            .execute()
        )
        return {"message": "Audience updated successfully", "audience": response.data[0]}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while updating audience: {str(e)}"
        )


@router.delete("/{id}")
def delete_audience(
    id: int,
    current_user: dict = Depends(get_current_user),
):
    """
    Delete an audience by ID.
    - Only allows deletion if the audience belongs to the current user.
    """
    try:
        audience = (
            supabase.table("audiences")
            .select("user_id")
            .eq("id", id)
            .execute()
        )
        if not audience.data:
            raise HTTPException(status_code=404, detail="Audience not found")

        if audience.data[0]["user_id"] != current_user["id"]:
            raise HTTPException(status_code=403, detail="Not authorized to delete this audience")

        supabase.table("audiences").delete().eq("id", id).execute()
        return {"message": "Audience deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while deleting audience: {str(e)}"
        )
