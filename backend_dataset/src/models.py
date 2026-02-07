"""Unified data models for the maintenance pipeline."""

from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class SourceCategory(str, Enum):
    OEM_MAINTENANCE = "oem_maintenance"
    DEALER_PRICING = "dealer_pricing"
    LABOR_STANDARDS = "labor_standards"
    PARTS_PRICING = "parts_pricing"
    RECALLS = "recalls"
    TSB = "tsb"


# ─── OEM Maintenance Schedules ───

class MaintenanceItem(BaseModel):
    """Single maintenance service item from OEM schedule."""
    vin: Optional[str] = None
    make: str
    model: str
    year: int
    engine: Optional[str] = None
    transmission: Optional[str] = None
    service_type: str
    service_name: str
    mileage_interval: Optional[int] = None  # e.g. 5000, 30000
    time_interval_months: Optional[int] = None
    avg_labor_hours: Optional[float] = None
    avg_parts_cost: Optional[float] = None
    avg_labor_cost: Optional[float] = None
    source: str
    source_url: Optional[str] = None
    confidence: float = 1.0
    ingested_at: datetime = Field(default_factory=datetime.utcnow)


# ─── Dealer Repair Pricing ───

class DealerPrice(BaseModel):
    """Dealer repair quote/pricing."""
    dealer_id: Optional[str] = None
    dealer_name: str
    service_name: str
    labor_cost: float
    parts_cost: Optional[float] = None
    total_cost: float
    labor_hours: Optional[float] = None
    region: Optional[str] = None
    source: str
    source_url: Optional[str] = None
    scraped_at: datetime = Field(default_factory=datetime.utcnow)


# ─── Labor Time Standards ───

class LaborStandard(BaseModel):
    """Labor time standard for a repair operation."""
    operation: str
    labor_hours: float
    source: str
    vehicle_scope: Optional[str] = None  # make/model/year
    source_url: Optional[str] = None
    confidence: float = 1.0


# ─── Parts Pricing ───

class PartsPrice(BaseModel):
    """Parts price from retailer/catalog."""
    part_number: Optional[str] = None
    part_name: str
    price: float
    retailer: str
    source_url: Optional[str] = None
    vehicle_scope: Optional[str] = None
    scraped_at: datetime = Field(default_factory=datetime.utcnow)


# ─── Recalls & TSBs ───

class Recall(BaseModel):
    """NHTSA or manufacturer recall."""
    nhtsa_id: Optional[str] = None
    campaign_number: Optional[str] = None
    component: str
    summary: str
    consequence: Optional[str] = None
    remedy: Optional[str] = None
    manufacturer: str
    make: str
    model: str
    year: Optional[int] = None
    vin_scope: Optional[list[str]] = None
    source: str = "NHTSA"
    report_date: Optional[datetime] = None


class TSB(BaseModel):
    """Technical Service Bulletin."""
    tsb_number: str
    component: str
    summary: str
    manufacturer: str
    make: Optional[str] = None
    model: Optional[str] = None
    year_range: Optional[str] = None
    source: str
    source_url: Optional[str] = None
