from pydantic import BaseModel
from typing import Optional, Dict
from datetime import datetime
from enum import Enum

class AssetType(str, Enum):
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    TEXT = "text"

class CreativeAssetCreate(BaseModel):
    project_id: int
    type: AssetType
    title: str
    file_url: Optional[str] = None
    ad_copy: Optional[str] = None
    voice_script: Optional[str] = None
    meta_data: Optional[Dict] = None

class CreativeAssetResponse(BaseModel):
    id: int
    project_id: int
    type: AssetType
    title: str
    file_url: Optional[str]
    ad_copy: Optional[str]
    voice_script: Optional[str]
    meta_data: Optional[Dict]
    uploaded_at: datetime

    class Config:
        orm_mode = True
