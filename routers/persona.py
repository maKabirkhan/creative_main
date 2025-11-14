from fastapi import APIRouter, HTTPException, Depends, Query
import logging
from app.helpers.security import get_current_user
from app.service.persona_service import PersonaService
from typing import Optional
from datetime import datetime
from app.helpers.db import supabase
from app.schemas.audience import CreateAudienceRequest
from fastapi import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()
persona_service = PersonaService()


@router.post("/create")
def create_persona(
    request: CreateAudienceRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Create a new persona using OpenAI to generate realistic persona fields
    or manual input. Audience data is NOT saved in the database anymore.
    """
    try:
        input_data = request.dict()

        persona = persona_service.create_persona(current_user["id"], input_data)

        return {"persona": persona}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while creating persona: {str(e)}"
        )

@router.post("/save")
def save_persona(
    persona_data: dict,
    current_user: dict = Depends(get_current_user)
):
    """
    Save a persona (merged with audience data) for the current user.
    - Checks for duplicate audience_name under the same user.
    - Stores all persona + audience fields into the `personas` table.
    """

    try:
        audience_name = persona_data.get("audience_name")
        if not audience_name:
            raise HTTPException(status_code=400, detail="audience_name is required")

        user_id = current_user["id"]

        existing = supabase.table("personas")\
            .select("id")\
            .eq("user_id", user_id)\
            .eq("name", audience_name)\
            .execute()

        if existing.data:
            raise HTTPException(
                status_code=400,
                detail=f"Persona with name '{audience_name}' already exists for this user"
            )

        # Handle gender as list
        gender_value = persona_data.get("gender")
        if gender_value is not None and not isinstance(gender_value, list):
            gender_value = [gender_value] if gender_value else []

        persona_payload = {
            "user_id": user_id,
            "name": audience_name,
            "audience_type": persona_data.get("audience_type"),
            "geography": persona_data.get("geography"),
            "age_min": persona_data.get("age_min"),
            "age_max": persona_data.get("age_max"),
            "income_min": persona_data.get("income_min"),
            "income_max": persona_data.get("income_max"),
            "gender": gender_value if gender_value is not None else [],
            "purchase_frequency": persona_data.get("purchase_frequency"),
            "interests": persona_data.get("interests") if isinstance(persona_data.get("interests"), list) else [],
            "life_stage": persona_data.get("life_stage"),
            "category_involvement": persona_data.get("category_involvement"),
            "decision_making_style": persona_data.get("decision_making_style"),
            "min_reach": persona_data.get("min_reach"),
            "max_reach": persona_data.get("max_reach"),
            "efficiency": persona_data.get("efficiency"),
            "platforms": persona_data.get("platforms") if isinstance(persona_data.get("platforms"), list) else [],
            "peak_activity": persona_data.get("peak_activity"),
            "engagement": persona_data.get("engagement"),
            "clarity": persona_data.get("clarity"),
            "relevance": persona_data.get("relevance"),
            "distinctiveness": persona_data.get("distinctiveness"),
            "brand_fit": persona_data.get("brand_fit"),
            "emotion": persona_data.get("emotion"),
            "cta": persona_data.get("cta"),
            "inclusivity": persona_data.get("inclusivity"),
        }

        response = supabase.table("personas").insert(persona_payload).execute()

        if not response.data:
            raise HTTPException(status_code=400, detail="Failed to save persona")

        return {
            "message": "Persona created successfully",
            "persona_id": response.data[0]["id"],
            "user_id": user_id
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while saving persona: {str(e)}"
        )

@router.get("/")
def get_personas(
    current_user: dict = Depends(get_current_user),
    id: Optional[int] = Query(None, description="Optional persona ID")
):
    """
    Get personas for the current user.
    - If no params: Returns all personas for the user
    - If id: Returns specific persona (if belongs to user)
    """
    try:
        query = (
            supabase.table("personas")
            .select("*")
            .eq("user_id", current_user["id"])
        )

        if id:
            query = query.eq("id", id)

        response = query.order("created_at", desc=True).execute()

        if not response.data or len(response.data) == 0:
            if id:
                raise HTTPException(status_code=404, detail="Persona not found for this user")
            return {"personas": [], "count": 0}

        if id:
            return {"persona": response.data[0]}

        return {
            "personas": response.data,
            "count": len(response.data)
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while fetching personas: {str(e)}"
        )


@router.put("/{persona_id}")
def update_persona(
    persona_id: int = Path(..., description="ID of the persona to update"),
    persona_data: dict = None,
    current_user: dict = Depends(get_current_user)
):
    """
    Update an existing persona (merged model).
    - Only allowed if persona belongs to current user.
    """
    try:
        existing = (
            supabase.table("personas")
            .select("*")
            .eq("id", persona_id)
            .eq("user_id", current_user["id"])
            .execute()
        )
        if not existing.data:
            raise HTTPException(status_code=404, detail="Persona not found for this user")

        # Handle gender as list in updates
        if "gender" in persona_data:
            gender_value = persona_data["gender"]
            if gender_value is not None and not isinstance(gender_value, list):
                persona_data["gender"] = [gender_value] if gender_value else []

        persona_data["updated_at"] = datetime.utcnow().isoformat()

        response = (
            supabase.table("personas")
            .update(persona_data)
            .eq("id", persona_id)
            .execute()
        )
        if not response.data:
            raise HTTPException(status_code=400, detail="Failed to update persona")

        return {
            "message": "Persona updated successfully",
            "persona": response.data[0]
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while updating persona: {str(e)}"
        )

@router.delete("/{persona_id}")
def delete_persona(
    persona_id: int = Path(..., description="ID of the persona to delete"),
    current_user: dict = Depends(get_current_user)
):
    """
    Delete an existing persona.
    - Only allowed if persona belongs to current user.
    """
    try:
        # Ensure persona belongs to user
        existing = (
            supabase.table("personas")
            .select("id")
            .eq("id", persona_id)
            .eq("user_id", current_user["id"])
            .execute()
        )
        if not existing.data:
            raise HTTPException(status_code=404, detail="Persona not found for this user")

        response = (
            supabase.table("personas")
            .delete()
            .eq("id", persona_id)
            .execute()
        )
        if not response.data:
            raise HTTPException(status_code=400, detail="Failed to delete persona")

        return {"message": "Persona deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while deleting persona: {str(e)}"
        )