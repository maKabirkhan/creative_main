from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class CreateAudienceRequest(BaseModel):
    name: str
    audience_type: str
    geography: str
    age_min: Optional[int] = None
    age_max: Optional[int] = None
    income_min: Optional[float] = None
    income_max: Optional[float] = None
    gender: Optional[List[str]] = Field(default_factory=list)
    purchase_frequency: Optional[str] = None
    interests: Optional[List[str]] = None
    life_stage: Optional[str] = None
    category_involvement: Optional[str] = None
    decision_making_style: Optional[str] = None


class AudienceResponse(BaseModel):
    id: int
    project_id: int

    audience_type: str
    geography: str

    age_min: Optional[int]
    age_max: Optional[int]

    income_min: Optional[float]
    income_max: Optional[float]

    gender: Optional[List[str]] = Field(default_factory=list)
    purchase_frequency: Optional[str]

    interests: Optional[List[str]]

    life_stage: Optional[str]
    category_involvement: Optional[str]
    decision_making_style: Optional[str]

    created_at: datetime
    updated_at: datetime
