"""Data ingestion modules."""

def __getattr__(name):
    """Lazy imports so run_recalls can work with minimal deps."""
    if name == "OEMMaintenanceIngester":
        from .oem_maintenance import OEMMaintenanceIngester
        return OEMMaintenanceIngester
    if name == "DealerPricingIngester":
        from .dealer_pricing import DealerPricingIngester
        return DealerPricingIngester
    if name == "LaborStandardsIngester":
        from .labor_standards import LaborStandardsIngester
        return LaborStandardsIngester
    if name == "PartsPricingIngester":
        from .parts_pricing import PartsPricingIngester
        return PartsPricingIngester
    if name == "RecallsIngester":
        from .recalls import RecallsIngester
        return RecallsIngester
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    "OEMMaintenanceIngester",
    "DealerPricingIngester",
    "LaborStandardsIngester",
    "PartsPricingIngester",
    "RecallsIngester",
]
