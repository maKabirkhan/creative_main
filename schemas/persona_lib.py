from typing import List, Optional
from pydantic import BaseModel, Field

class PersonaLibraryResponse(BaseModel):
    id: int
    audience_name: str
    audience_type: Optional[str]
    geography: Optional[str]
    age_min: Optional[int]
    age_max: Optional[int]
    income_min: Optional[float]
    income_max: Optional[float]
    gender: Optional[List[str]] = Field(default_factory=list)
    interests: Optional[List[str]]
    life_stage: Optional[str]
    category_involvement: Optional[str]
    decision_making_style: Optional[str]
    purchase_frequency: Optional[str]