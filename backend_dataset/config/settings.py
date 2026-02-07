"""Pipeline configuration and settings."""

import os
from pathlib import Path
import yaml
from dotenv import load_dotenv

load_dotenv()

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
REFERENCE_DIR = DATA_DIR / "reference"
PROCESSED_DIR = DATA_DIR / "processed"
OUTPUT_DIR = DATA_DIR / "output"
LOG_DIR = PROJECT_ROOT / "logs"

# Ensure dirs exist
for d in [DATA_DIR, RAW_DIR, PROCESSED_DIR, OUTPUT_DIR, LOG_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# NHTSA API (free, no key required)
NHTSA_BASE_URL = os.getenv("NHTSA_BASE_URL", "https://api.nhtsa.gov")

# Rate limits
DEFAULT_RATE_LIMIT = 60
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DATA_DIR}/pipeline.db")


def load_sources_config() -> dict:
    """Load source configuration from YAML."""
    config_path = Path(__file__).parent / "sources.yaml"
    with open(config_path) as f:
        return yaml.safe_load(f)
