from typing import List

from pydantic import BaseModel, Field


class ReceiptData(BaseModel):
    shop_name: str = Field(..., description="Name of the repair shop")
    service_date: str = Field(..., description="YYYY-MM-DD")
    mileage_in: int = Field(..., ge=0)
    services_performed: List[str] = Field(..., min_length=1)
    total_cost: float = Field(..., ge=0)
