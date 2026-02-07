#!/usr/bin/env python3
"""
Quick demo: NHTSA Recalls API (free, no key required).

Usage:
  python run_recalls.py                    # Demo with sample VIN/vehicle
  python run_recalls.py 1HGBH41JXMN109186  # Check specific VIN
  python run_recalls.py Toyota Camry 2020  # Check make/model/year
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.ingesters.recalls import RecallsIngester


def main():
    ingester = RecallsIngester()

    if len(sys.argv) == 1:
        # Demo mode
        print("NHTSA Recalls Demo (no key required)\n")
        print("Checking 2020 Toyota Camry...")
        recalls = ingester.get_recalls_by_vehicle("Toyota", "Camry", 2020)
        for r in recalls[:5]:
            print(f"  - {r.component}: {r.summary[:80]}...")
        print(f"\nTotal: {len(recalls)} recalls")
        return

    if len(sys.argv) == 2:
        vin = sys.argv[1]
        print(f"Recalls for VIN {vin[:8]}...")
        recalls = ingester.get_recalls_by_vin(vin)
        for r in recalls:
            print(f"  - {r.component}: {r.summary[:80]}...")
        print(f"\nTotal: {len(recalls)} recalls")
        return

    if len(sys.argv) >= 4:
        make, model, year = sys.argv[1], sys.argv[2], int(sys.argv[3])
        print(f"Recalls for {year} {make} {model}...")
        recalls = ingester.get_recalls_by_vehicle(make, model, year)
        for r in recalls:
            print(f"  - {r.component}: {r.summary[:80]}...")
        print(f"\nTotal: {len(recalls)} recalls")
        return

    print(__doc__)


if __name__ == "__main__":
    main()
