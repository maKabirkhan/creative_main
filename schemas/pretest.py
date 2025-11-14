from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from enum import Enum

class CreativeType(str, Enum):
    COPY = "copy"
    IMAGE = "image"
    VIDEO = "video"
    TEXT = "text"
    MULTI_ASSET = "multi-asset"

class PretestRequest(BaseModel):
    persona_id: str = Field(..., description="Unique identifier of the persona")
    channels: List[str] = Field(..., description="List of channels where the creative will run")
    creative_ids: List[int] = Field(..., description="List of creative asset IDs to be tested")
    
    headline: str = Field(..., description="Creative headline")
    title: str = Field(..., description="Creative title")
    description: str = Field(..., description="Creative description")

