"""
Labor Time Standards Ingestion

Sources:
- ASE (Automotive Service Excellence) data - may require licensing
- Public mechanic forums (iATN, JustAnswer)
- Open shop databases
- Fleet maintenance docs
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from loguru import logger

from ..models import LaborStandard
from config.settings import load_sources_config, RAW_DIR


class LaborStandardsIngester:
    """Ingest labor time standards from configured sources."""

    def __init__(self):
        self.config = load_sources_config()["labor_time_standards"]
        self.results: list[LaborStandard] = []

    def _load_fleet_docs(self) -> list[LaborStandard]:
        """Load labor standards from fleet maintenance docs (CSV/JSON)."""
        items = []
        fleet_dir = RAW_DIR / "fleet_standards"
        if not fleet_dir.exists():
            logger.info(f"No fleet docs at {fleet_dir}")
            return items

        import csv
        for path in fleet_dir.glob("*.csv"):
            try:
                with open(path) as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        op = row.get("operation") or row.get("service") or row.get("task", "")
                        hours = row.get("hours") or row.get("labor_hours") or row.get("time", "0")
                        try:
                            h = float(str(hours).replace(",", "."))
                            if op and h > 0:
                                items.append(LaborStandard(
                                    operation=op,
                                    labor_hours=h,
                                    source="fleet_maintenance_docs",
                                    source_url=str(path),
                                    vehicle_scope=row.get("vehicle_scope"),
                                ))
                        except ValueError:
                            pass
            except Exception as e:
                logger.warning(f"Failed to parse {path}: {e}")

        return items

    def _load_manual_standards(self) -> list[LaborStandard]:
        """Load curated labor standards (Mitchell/Chilton-style reference)."""
        # Common labor times - can be expanded from public references
        defaults = [
            ("Oil Change", 0.5),
            ("Transmission Fluid Change", 0.75),
            ("Brake Fluid Change", 0.5),
            ("Air Filter", 0.25),
            ("Cabin Air Filter", 0.25),
            ("TPMS Sensor", 0.5),
            ("Brake Pad Replacement (Front)", 1.5),
            ("Brake Pad Replacement (Rear)", 1.0),
            ("Brake Rotor Replacement (Front)", 1.0),
            ("Brake Rotor Replacement (Rear)", 1.0),
            ("Alternator Replacement", 1.5),
            ("Starter Replacement", 1.0),
            ("Battery Replacement", 0.25),
            ("Spark Plug Replacement (4-cyl)", 1.0),
            ("Spark Plug Replacement (6-cyl)", 1.5),
            ("Spark Plug Replacement (8-cyl)", 2.0),
            ("Timing Belt Replacement", 4.0),
            ("Water Pump Replacement", 2.5),
            ("Thermostat Replacement", 1.0),
            ("Radiator Replacement", 3.0),
            ("AC Recharge", 0.5),
            ("Compressor Replacement", 3.0),
            ("Tire Rotation", 0.25),
            ("Wheel Alignment", 1.0),
            ("Strut Replacement (Front)", 2.0),
            ("Strut Replacement (Rear)", 1.5),
        ]
        return [
            LaborStandard(operation=op, labor_hours=h, source="curated_manual", confidence=0.9)
            for op, h in defaults
        ]

    def run(self) -> list[LaborStandard]:
        """Run labor standards ingestion."""
        logger.info("Starting labor standards ingestion")

        self.results = self._load_manual_standards()

        for source in self.config["sources"]:
            if not source.get("enabled", True):
                continue
            if source.get("name") == "fleet_maintenance_docs":
                self.results.extend(self._load_fleet_docs())

        logger.info(f"Labor standards: ingested {len(self.results)} items")
        return self.results
