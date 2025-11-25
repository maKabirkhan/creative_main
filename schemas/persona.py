from pydantic import BaseModel, field_validator
import base64
import re
from typing import List

class ImageInput(BaseModel):
    image_data: str
    
    @field_validator('image_data')
    @classmethod
   
    def validate_base64(cls, v: str) -> str:
        """Validate and clean base64 string"""
        if not v or not v.strip():
            raise ValueError("Image data cannot be empty")
        
        if ',' in v:
            v = v.split(',', 1)[1]
        
        v = re.sub(r'\s+', '', v)
        
        try:
            base64.b64decode(v)
        except Exception:
            raise ValueError("Invalid base64 encoded image data")
        
        return v


class EvaluateRequest(BaseModel):
    image1: ImageInput
    image2: ImageInput
    image3: ImageInput

class ImageEvaluationResult(BaseModel):
    image_number: int
    confidence_score: int

class AdEvaluationResponse(BaseModel):
    evaluations: List[ImageEvaluationResult]
