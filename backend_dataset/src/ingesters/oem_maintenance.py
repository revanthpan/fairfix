"""
OEM Maintenance Schedules Ingestion

Sources:
- Manufacturer service websites
- Owner manual PDFs
- OEM APIs (where available)
- Public service bulletins
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import requests
from bs4 import BeautifulSoup
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from ..models import MaintenanceItem
from config.settings import load_sources_config, RAW_DIR


class OEMMaintenanceIngester:
    """Ingest OEM maintenance schedules from configured sources."""

    def __init__(self):
        self.config = load_sources_config()["oem_maintenance_schedules"]
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (compatible; MaintenancePipeline/1.0; +research)"
        })
        self.results: list[MaintenanceItem] = []

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def _fetch_url(self, url: str) -> str:
        """Fetch URL with retries."""
        resp = self.session.get(url, timeout=30)
        resp.raise_for_status()
        return resp.text

    def _parse_maintenance_website(self, url: str, make: str) -> list[MaintenanceItem]:
        """Parse manufacturer maintenance webpage (structure varies by OEM)."""
        items = []
        try:
            html = self._fetch_url(url)
            soup = BeautifulSoup(html, "lxml")

            # Generic extraction - OEM sites have different structures
            # Common patterns: tables, lists, accordions
            for table in soup.find_all("table"):
                for row in table.find_all("tr")[1:]:
                    cells = row.find_all(["td", "th"])
                    if len(cells) >= 2:
                        service_name = cells[0].get_text(strip=True)
                        interval = cells[1].get_text(strip=True) if len(cells) > 1 else None
                        items.append(MaintenanceItem(
                            make=make,
                            model="*",  # May need model-specific pages
                            year=0,  # Placeholder
                            service_type="scheduled",
                            service_name=service_name,
                            mileage_interval=self._parse_mileage(interval),
                            source="manufacturer_website",
                            source_url=url,
                            confidence=0.7,
                        ))

            logger.info(f"Extracted {len(items)} items from {url}")
        except Exception as e:
            logger.warning(f"Failed to parse {url}: {e}")

        return items

    def _parse_mileage(self, s: str | None) -> int | None:
        """Extract mileage number from string (e.g. '5,000 mi' -> 5000)."""
        if not s:
            return None
        import re
        m = re.search(r"[\d,]+", s.replace(",", ""))
        return int(m.group()) if m else None

    def _load_pdf_manuals(self) -> list[MaintenanceItem]:
        """Load maintenance data from PDF manuals in storage."""
        items = []
        manuals_dir = RAW_DIR / "oem_manuals"
        if not manuals_dir.exists():
            logger.info(f"No PDF manuals at {manuals_dir}")
            return items

        try:
            import pdfplumber
            for pdf_path in manuals_dir.glob("*.pdf"):
                try:
                    with pdfplumber.open(pdf_path) as pdf:
                        for page in pdf.pages:
                            tables = page.extract_tables()
                            for table in tables:
                                if table:
                                    for row in table[1:]:
                                        if row and len(row) >= 2:
                                            items.append(MaintenanceItem(
                                                make=pdf_path.stem.split("_")[0] if "_" in pdf_path.stem else "Unknown",
                                                model="*",
                                                year=0,
                                                service_type="scheduled",
                                                service_name=str(row[0])[:200],
                                                mileage_interval=self._parse_mileage(str(row[1]) if row[1] else None),
                                                source="owner_manual_pdf",
                                                source_url=str(pdf_path),
                                                confidence=0.8,
                                            ))
                except Exception as e:
                    logger.warning(f"Failed to parse PDF {pdf_path}: {e}")
        except ImportError:
            logger.warning("pdfplumber not installed; skipping PDF parsing")

        return items

    def run(self) -> list[MaintenanceItem]:
        """Run full OEM maintenance ingestion."""
        logger.info("Starting OEM maintenance ingestion")

        for source in self.config["sources"]:
            if not source.get("enabled", True):
                continue

            if source["type"] == "website" and "base_urls" in source:
                make_map = {"toyota": "Toyota", "honda": "Honda", "ford": "Ford"}
                for url in source["base_urls"]:
                    make = next((m for k, m in make_map.items() if k in url.lower()), "Unknown")
                    self.results.extend(self._parse_maintenance_website(url, make))

            elif source["type"] == "pdf":
                self.results.extend(self._load_pdf_manuals())

        logger.info(f"OEM maintenance: ingested {len(self.results)} items")
        return self.results
