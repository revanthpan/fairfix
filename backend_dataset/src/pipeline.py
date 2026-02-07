"""
Main Pipeline Orchestrator

Runs all 5 ingestion modules:
1. OEM Maintenance Schedules
2. Dealer Repair Pricing
3. Labor Time Standards
4. Parts Pricing
5. Recalls + Known Issues
"""

from pathlib import Path
import sys

# Ensure project root in path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
from loguru import logger

from config.settings import PROCESSED_DIR, OUTPUT_DIR, load_sources_config
from src.ingesters import (
    OEMMaintenanceIngester,
    DealerPricingIngester,
    LaborStandardsIngester,
    PartsPricingIngester,
    RecallsIngester,
)


def run_pipeline(
    vins: list[str] | None = None,
    vehicles: list[tuple[str, str, int]] | None = None,
    dealer_urls: list[tuple[str, str]] | None = None,
    parts_queries: list[str] | None = None,
    skip_oem: bool = False,
    skip_dealer: bool = False,
    skip_labor: bool = False,
    skip_parts: bool = False,
    skip_recalls: bool = False,
) -> dict:
    """
    Run the full data ingestion pipeline.

    Args:
        vins: Optional VINs for recall lookups
        vehicles: Optional (make, model, year) for recalls
        dealer_urls: Optional [(url, dealer_name)] for dealer pricing
        parts_queries: Optional part names for parts pricing
        skip_*: Skip individual ingestion modules

    Returns:
        Dict with keys: oem, dealer, labor, parts, recalls
    """
    logger.info("Starting Auto Maintenance Data Pipeline")

    results = {
        "oem": [],
        "dealer": [],
        "labor": [],
        "parts": [],
        "recalls": [],
    }

    if not skip_oem:
        oem = OEMMaintenanceIngester()
        results["oem"] = oem.run()

    if not skip_dealer:
        dealer = DealerPricingIngester()
        results["dealer"] = dealer.run(dealer_urls=dealer_urls)

    if not skip_labor:
        labor = LaborStandardsIngester()
        results["labor"] = labor.run()

    if not skip_parts:
        parts = PartsPricingIngester()
        results["parts"] = parts.run(search_queries=parts_queries)

    if not skip_recalls:
        recalls_ing = RecallsIngester()
        recalls_list, _ = recalls_ing.run(vins=vins, vehicles=vehicles)
        results["recalls"] = recalls_list

    # Export to CSV
    for name, items in results.items():
        if items:
            df = pd.DataFrame([i.model_dump() if hasattr(i, "model_dump") else dict(i) for i in items])
            out_path = OUTPUT_DIR / f"{name}_data.csv"
            df.to_csv(out_path, index=False)
            logger.info(f"Exported {len(items)} {name} records to {out_path}")

    return results


if __name__ == "__main__":
    run_pipeline(
        vehicles=[("Toyota", "Camry", 2020), ("Honda", "Accord", 2019)],
        skip_oem=True,  # OEM websites may block scrapers
        skip_dealer=True,  # Needs specific dealer URLs
        skip_parts=True,  # Retail sites may block
    )
