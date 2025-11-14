from pydantic import BaseModel
from typing import Optional, List

class CreateProjectRequest(BaseModel):
    name: str
    brand: str
    product: str
    product_service_type: str
    category: str
    market_maturity: str
    campaign_objective: str
    value_propositions: str
    media_channels: List[str]
    kpis: str
    kpi_target: str

class ProjectResponse(BaseModel):
    id: int
    user_id: str
    name: str
    brand: Optional[str]
    product: Optional[str]
    product_service_type: Optional[str]
    category: Optional[str]
    market_maturity: Optional[str]
    campaign_objective: Optional[str]
    value_propositions: Optional[str]
    media_channels: Optional[List[str]]
    kpis: Optional[str]
    kpi_target: Optional[str]
    created_at: str
    updated_at: str

    class Config:
        orm_mode = True
