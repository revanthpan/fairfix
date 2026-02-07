from enum import Enum
from typing import Optional

from sqlmodel import Field, SQLModel


class Severity(str, Enum):
    Routine = "Routine"
    Major = "Major"
    Critical = "Critical"


class MaintenanceSchedule(SQLModel, table=True):
    __tablename__ = "maintenance_schedule"

    id: Optional[int] = Field(default=None, primary_key=True)
    make: str
    model: str
    year: int
    interval_miles: int
    service_task: str
    description: str
    severity: Severity


class ServiceHistory(SQLModel, table=True):
    __tablename__ = "service_history"

    id: Optional[int] = Field(default=None, primary_key=True)
    vehicle_id: str
    date: str
    mileage: int
    shop_name: str
    description: str
    cost: float
