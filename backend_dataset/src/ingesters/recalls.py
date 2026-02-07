"""
Recalls + Known Issues Ingestion

Sources:
- NHTSA API (free, no key required)
- Manufacturer recall databases
- Technical Service Bulletins (TSBs)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import requests
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from ..models import Recall, TSB
from config.settings import load_sources_config, NHTSA_BASE_URL


class RecallsIngester:
    """Ingest recalls and TSBs - NHTSA API is fully implemented."""

    def __init__(self):
        self.config = load_sources_config()["recalls_and_issues"]
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json"})
        self.base_url = NHTSA_BASE_URL
        self.recalls: list[Recall] = []
        self.tsbs: list[TSB] = []

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def _fetch_nhtsa(self, path: str, params: dict | None = None) -> dict:
        """Fetch NHTSA API endpoint."""
        url = f"{self.base_url}{path}"
        resp = self.session.get(url, params=params or {}, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def get_recalls_by_vin(self, vin: str) -> list[Recall]:
        """Get recalls for a specific VIN. NHTSA API - works out of the box."""
        try:
            data = self._fetch_nhtsa("/recalls/recallsByVIN", {"vin": vin})
            items = []
            for r in data.get("results", []):
                items.append(Recall(
                    nhtsa_id=r.get("NHTSACampaignNumber"),
                    campaign_number=r.get("NHTSACampaignNumber"),
                    component=r.get("Component", ""),
                    summary=r.get("Summary", ""),
                    consequence=r.get("Conequence"),
                    remedy=r.get("Remedy"),
                    manufacturer=r.get("Manufacturer", ""),
                    make=r.get("Make", ""),
                    model=r.get("Model", ""),
                    year=int(r["ModelYear"]) if r.get("ModelYear") else None,
                    source="NHTSA",
                ))
            logger.info(f"NHTSA: {len(items)} recalls for VIN {vin[:8]}...")
            return items
        except Exception as e:
            logger.warning(f"NHTSA recall fetch failed for VIN {vin}: {e}")
            return []

    def get_recalls_by_campaign(self, campaign_number: str) -> list[Recall]:
        """Get recalls by NHTSA campaign number."""
        try:
            data = self._fetch_nhtsa("/recalls/recallsByCampaignNumber", {"campaignNumber": campaign_number})
            items = []
            for r in data.get("results", []):
                items.append(Recall(
                    nhtsa_id=r.get("NHTSACampaignNumber"),
                    campaign_number=r.get("NHTSACampaignNumber"),
                    component=r.get("Component", ""),
                    summary=r.get("Summary", ""),
                    consequence=r.get("Conequence"),
                    remedy=r.get("Remedy"),
                    manufacturer=r.get("Manufacturer", ""),
                    make=r.get("Make", ""),
                    model=r.get("Model", ""),
                    year=int(r["ModelYear"]) if r.get("ModelYear") else None,
                    source="NHTSA",
                ))
            return items
        except Exception as e:
            logger.warning(f"NHTSA campaign fetch failed: {e}")
            return []

    def get_recalls_by_vehicle(self, make: str, model: str, year: int) -> list[Recall]:
        """Get recalls for make/model/year. Uses NHTSA Recalls by Vehicle endpoint."""
        try:
            # NHTSA: /recalls/recallsByVehicle?make=...&model=...&modelYear=...
            path = "/recalls/recallsByVehicle"
            params = {"make": make, "model": model, "modelYear": year}
            data = self._fetch_nhtsa(path, params)
            items = []
            for r in data.get("results", []):
                items.append(Recall(
                    nhtsa_id=r.get("NHTSACampaignNumber"),
                    campaign_number=r.get("NHTSACampaignNumber"),
                    component=r.get("Component", ""),
                    summary=r.get("Summary", ""),
                    consequence=r.get("Conequence"),
                    remedy=r.get("Remedy"),
                    manufacturer=r.get("Manufacturer", ""),
                    make=r.get("Make", ""),
                    model=r.get("Model", ""),
                    year=int(r["ModelYear"]) if r.get("ModelYear") else None,
                    source="NHTSA",
                ))
            logger.info(f"NHTSA: {len(items)} recalls for {year} {make} {model}")
            return items
        except Exception as e:
            logger.warning(f"NHTSA vehicle recall fetch failed: {e}")
            return []

    def get_complaints_by_vehicle(self, make: str, model: str, year: int) -> list[dict]:
        """Get complaints for make/model/year."""
        try:
            path = "/complaints/complaintsByVehicle"
            params = {"make": make, "model": model, "modelYear": year}
            data = self._fetch_nhtsa(path, params)
            return data.get("results", [])
        except Exception as e:
            logger.warning(f"NHTSA complaints fetch failed: {e}")
            return []

    def run(self, vins: list[str] | None = None, vehicles: list[tuple[str, str, int]] | None = None) -> tuple[list[Recall], list[TSB]]:
        """
        Run full recalls + TSB ingestion.
        vins: optional list of VINs to check
        vehicles: optional list of (make, model, year) tuples
        """
        logger.info("Starting recalls + TSB ingestion")

        for source in self.config["sources"]:
            if not source.get("enabled", True):
                continue
            if source.get("name") != "nhtsa":
                continue

            if vins:
                for vin in vins[:20]:  # Limit
                    self.recalls.extend(self.get_recalls_by_vin(vin))

            if vehicles:
                for make, model, year in vehicles[:50]:
                    self.recalls.extend(self.get_recalls_by_vehicle(make, model, year))

            # Fallback: fetch some recent recalls if no input
            if not vins and not vehicles:
                try:
                    # NHTSA Recalls by Component - can get recent recalls
                    data = self._fetch_nhtsa("/recalls/recallsByComponent", {"component": "air bags"})
                    for r in data.get("results", [])[:20]:
                        self.recalls.append(Recall(
                            nhtsa_id=r.get("NHTSACampaignNumber"),
                            campaign_number=r.get("NHTSACampaignNumber"),
                            component=r.get("Component", ""),
                            summary=r.get("Summary", ""),
                            consequence=r.get("Conequence"),
                            remedy=r.get("Remedy"),
                            manufacturer=r.get("Manufacturer", ""),
                            make=r.get("Make", ""),
                            model=r.get("Model", ""),
                            year=int(r["ModelYear"]) if r.get("ModelYear") else None,
                            source="NHTSA",
                        ))
                except Exception as e:
                    logger.warning(f"NHTSA component recall fetch failed: {e}")

        logger.info(f"Recalls: ingested {len(self.recalls)} items")
        return self.recalls, self.tsbs
