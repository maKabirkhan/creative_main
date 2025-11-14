from fastapi import APIRouter, HTTPException
from app.helpers.db import supabase
from typing import List
from dotenv import load_dotenv
from app.schemas.persona_lib import PersonaLibraryResponse

load_dotenv()

router = APIRouter()

@router.get("", response_model=List[PersonaLibraryResponse])
def get_persona_library():
    try:
        response = supabase.table("persona_library").select("*").execute()
        if not response.data:
            raise HTTPException(status_code=404, detail="No personas found")
        
        # Transform the data to ensure gender is a list
        transformed_data = []
        for persona in response.data:
            if persona.get('gender') and isinstance(persona['gender'], str):
                persona['gender'] = [persona['gender']]
            elif not persona.get('gender'):
                persona['gender'] = []
            transformed_data.append(persona)
        
        return transformed_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch personas: {str(e)}")