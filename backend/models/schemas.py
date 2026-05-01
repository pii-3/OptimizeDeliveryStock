from typing import Optional
from pydantic import BaseModel


class UploadResponse(BaseModel):
    session_id: str


class ActionRequest(BaseModel):
    session_id: str


class CostBreakdown(BaseModel):
    delivery_small: float
    delivery_large: float
    holding: float


class SummaryKPIs(BaseModel):
    avg_inventory: float
    turnover_days: float
    total_trucks: int
    total_small_cases: float
    total_large_cases: float


class OptimizeResponse(BaseModel):
    status: str
    total_cost: Optional[float] = None
    cost_breakdown: Optional[CostBreakdown] = None
    summary: Optional[SummaryKPIs] = None
    decision_variables: Optional[list[dict]] = None
    trucks: Optional[list[dict]] = None
    aggregated_by_date: Optional[list[dict]] = None
    pivot_by_date_product: Optional[list[dict]] = None
    chart_c1_base64: Optional[str] = None
    chart_c2_base64: Optional[str] = None
    excel_base64: Optional[str] = None
