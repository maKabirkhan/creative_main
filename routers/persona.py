from fastapi import APIRouter, HTTPException, Request, Form
from typing import Optional
import openai
import os
from schemas.persona import (
    EvaluateRequest,
    AdEvaluationResponse)

from helpers.persona import validate_base64, evaluate_single_image

router = APIRouter()


openai.api_key = os.getenv("OPENAI_API_KEY")


@router.post("/evaluate", response_model=AdEvaluationResponse)
async def evaluate_ad(
    request: Request,
    image1: Optional[str] = Form(None),
    image2: Optional[str] = Form(None),
    image3: Optional[str] = Form(None)
):
    """
    Evaluate 3 Facebook ad creative images separately (all required).
    
    Accepts TWO formats:
    
    FORMAT 1 - JSON (application/json):
    {
        "image1": {"image_data": "base64_string"},
        "image2": {"image_data": "base64_string"},
        "image3": {"image_data": "base64_string"}
    }
    
    FORMAT 2 - Form Data (multipart/form-data):
    - image1: base64 string (TEXT field)
    - image2: base64 string (TEXT field)
    - image3: base64 string (TEXT field)
    """
    
    content_type = request.headers.get("content-type", "").lower()
    
    if "application/json" in content_type:
        try:
            body = await request.json()
            request_obj = EvaluateRequest(**body)
            
            evaluation1 = await evaluate_single_image(request_obj.image1.image_data, 1)
            evaluation2 = await evaluate_single_image(request_obj.image2.image_data, 2)
            evaluation3 = await evaluate_single_image(request_obj.image3.image_data, 3)
            
            return AdEvaluationResponse(
                evaluations=[evaluation1, evaluation2, evaluation3]
            )
            
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid JSON format: {str(e)}"
            )
    
    elif "multipart/form-data" in content_type or "application/x-www-form-urlencoded" in content_type:
        if not image1 or not image2 or not image3:
            raise HTTPException(
                status_code=400,
                detail="All three images (image1, image2, image3) are required as text fields"
            )
        
        try:
            image1_clean = validate_base64(image1)
            image2_clean = validate_base64(image2)
            image3_clean = validate_base64(image3)
            
            evaluation1 = await evaluate_single_image(image1_clean, 1)
            evaluation2 = await evaluate_single_image(image2_clean, 2)
            evaluation3 = await evaluate_single_image(image3_clean, 3)
            
            return AdEvaluationResponse(
                evaluations=[evaluation1, evaluation2, evaluation3]
            )
            
        except ValueError as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid image data: {str(e)}"
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error evaluating ad: {str(e)}"
            )
    
    else:
        raise HTTPException(
            status_code=400,
            detail="Content-Type must be either 'application/json' or 'multipart/form-data'"
        )