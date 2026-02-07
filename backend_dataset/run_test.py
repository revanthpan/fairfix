#!/usr/bin/env python3
"""
Test the pipeline with inputs.

Usage:
  # Recalls by VIN
  python run_test.py recalls --vin 1HGBH41JXMN109186

  # Recalls by make/model/year
  python run_test.py recalls --make Toyota --model Camry --year 2020

  # Recalls for multiple vehicles
  python run_test.py recalls --vehicles "Toyota,Camry,2020" "Honda,Accord,2019"

  # Full pipeline with vehicles
  python run_test.py pipeline --vehicles "Toyota,Camry,2020"

  # Full pipeline with VINs
  python run_test.py pipeline --vins 1HGBH41JXMN109186

  # Parts search
  python run_test.py pipeline --parts "oil filter" "brake pads" --skip-oem --skip-dealer --skip-recalls

  # Labor standards only
  python run_test.py pipeline --skip-oem --skip-dealer --skip-parts --skip-recalls

  # Cost estimate (all data from code reference files)
  python run_test.py estimate --make Toyota --model Camry --year 2020 --service "Oil Change"
  python run_test.py estimate --make BMW --model M3 --year 2023 --service "Oil Change"
  python run_test.py estimate --make Toyota --model Camry --year 2012 --brakes  # front+rear pads
  python run_test.py estimate --list-services

  # Quote: year, make, model, service (+ optional mileage for recommended services)
  python run_test.py quote --year 2020 --make Honda --model Civic --service "Oil Change"
  python run_test.py quote --year 2020 --make Honda --model Civic --mileage 45000 --service "Oil Change"

  # Recommend services based on mileage (year, make, model, mileage)
  python run_test.py recommend --year 2020 --make Honda --model Civic --mileage 55000
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


def run_recalls(args):
    from src.ingesters.recalls import RecallsIngester

    ingester = RecallsIngester()

    if args.vin:
        print(f"Recalls for VIN {args.vin[:8]}...\n")
        recalls = ingester.get_recalls_by_vin(args.vin)
    elif args.vehicles:
        recalls = []
        for v in args.vehicles:
            parts = [p.strip() for p in v.split(",")]
            if len(parts) >= 3:
                make, model, year = parts[0], parts[1], int(parts[2])
                print(f"Recalls for {year} {make} {model}...")
                recalls.extend(ingester.get_recalls_by_vehicle(make, model, year))
    elif args.make and args.model and args.year:
        print(f"Recalls for {args.year} {args.make} {args.model}...\n")
        recalls = ingester.get_recalls_by_vehicle(args.make, args.model, args.year)
    else:
        print("Provide --vin, --make/--model/--year, or --vehicles")
        return

    for r in recalls:
        print(f"  - [{r.component}] {r.summary[:80]}...")
    print(f"\nTotal: {len(recalls)} recalls")


def run_pipeline(args):
    from src.pipeline import run_pipeline as _run_pipeline

    vins = args.vins if args.vins else None
    vehicles = None
    if args.vehicles:
        vehicles = []
        for v in args.vehicles:
            parts = [p.strip() for p in v.split(",")]
            if len(parts) >= 3:
                vehicles.append((parts[0], parts[1], int(parts[2])))

    results = _run_pipeline(
        vins=vins,
        vehicles=vehicles,
        dealer_urls=[(u, "Dealer") for u in args.dealer_urls] if args.dealer_urls else None,
        parts_queries=args.parts if args.parts else None,
        skip_oem=args.skip_oem,
        skip_dealer=args.skip_dealer,
        skip_labor=args.skip_labor,
        skip_parts=args.skip_parts,
        skip_recalls=args.skip_recalls,
    )
    print("\nDone. Outputs in data/output/")


def run_estimate(args):
    from src.estimator import CostEstimator

    est = CostEstimator()

    if args.list_services:
        print("Available services (from code reference data):")
        for svc in sorted(est._labor_standards.keys()):
            print(f"  - {svc}")
        return

    if not (args.make and args.model and args.year):
        print("Provide --make --model --year (and --service or --brakes)")
        return

    if args.brakes:
        result = est.estimate_brakes_full(args.make, args.model, args.year)
    elif args.service:
        result = est.estimate(args.make, args.model, args.year, args.service)
    else:
        print("Provide --service or --brakes")
        return

    if not result:
        print("Unknown service. Use --list-services to see options.")
        return

    print(f"\n{result.year} {result.make} {result.model} — {result.service}")
    print(f"Vehicle tier: {result.vehicle_tier} | Labor: {result.labor_hours} hrs")
    print("-" * 55)
    print(f"DEALER (95% CI):  ${result.dealer.total_ci_low:.0f} - ${result.dealer.total_ci_high:.0f}")
    print(f"                  Labor: ${result.dealer.labor_cost_ci_low:.0f}-{result.dealer.labor_cost_ci_high:.0f} @ ${result.dealer.labor_rate_ci_low:.0f}-{result.dealer.labor_rate_ci_high:.0f}/hr")
    print(f"                  Parts: ${result.dealer.parts_ci_low:.0f}-{result.dealer.parts_ci_high:.0f}")
    print()
    print(f"INDY (95% CI):    ${result.indy.total_ci_low:.0f} - ${result.indy.total_ci_high:.0f}")
    print(f"                  Labor: ${result.indy.labor_cost_ci_low:.0f}-{result.indy.labor_cost_ci_high:.0f} @ ${result.indy.labor_rate_ci_low:.0f}-{result.indy.labor_rate_ci_high:.0f}/hr")
    print(f"                  Parts: ${result.indy.parts_ci_low:.0f}-{result.indy.parts_ci_high:.0f}")
    print()
    print(f"Indy savings vs dealer (95% CI): ${result.indy_savings_ci_low:.0f} - ${result.indy_savings_ci_high:.0f}")
    print("\n(All values from code: data/reference/*.csv, ranges are 95% confidence intervals)")


def run_quote(args):
    """Get a quote: year, make, model, service. With mileage, show recommended services."""
    from src.estimator import CostEstimator

    if not (args.year and args.make and args.model and args.service):
        print("Provide --year --make --model --service (--mileage optional)")
        return

    est = CostEstimator()

    # Show recommended services when mileage provided
    if args.mileage is not None:
        recs = est.recommend_services(args.make, args.model, args.mileage)
        due = [r for r in recs if r.due_now]
        coming = [r for r in recs if not r.due_now]
        print(f"\n{'='*60}")
        print(f"SERVICES FOR {args.year} {args.make} {args.model} @ {args.mileage:,} MILES")
        print(f"{'='*60}")
        if due:
            print("\nLIKELY DUE NOW (mileage >= interval):")
            for r in due:
                print(f"  - {r.service_name} (interval: {r.mileage_interval:,} mi)")
        if coming:
            print("\nCOMING UP (mileage < interval):")
            for r in coming:
                print(f"  - {r.service_name} (interval: {r.mileage_interval:,} mi)")
        print()

    # Brakes shorthand
    if args.service.lower() in ("brakes", "brake pads", "brake pads full"):
        result = est.estimate_brakes_full(args.make, args.model, args.year)
    else:
        result = est.estimate(args.make, args.model, args.year, args.service)

    if not result:
        print("Unknown service. Use: python run_test.py estimate --list-services")
        return

    mileage_str = f" | Mileage: {args.mileage:,}" if args.mileage is not None else ""
    print(f"{'='*60}")
    print(f"QUOTE — {result.year} {result.make} {result.model}{mileage_str}")
    print(f"Service: {result.service}")
    print(f"Vehicle tier: {result.vehicle_tier} | Labor: {result.labor_hours} hrs")
    print(f"{'='*60}")
    print(f"\nDEALER (95% CI):  ${result.dealer.total_ci_low:.0f} - ${result.dealer.total_ci_high:.0f}")
    print(f"INDY (95% CI):    ${result.indy.total_ci_low:.0f} - ${result.indy.total_ci_high:.0f}")
    print(f"\nIndy savings vs dealer: ${result.indy_savings_ci_low:.0f} - ${result.indy_savings_ci_high:.0f}")
    print(f"\n(All values from code: data/reference/*.csv)")


def run_recommend(args):
    """Recommend services based on year, make, model, mileage."""
    from src.estimator import CostEstimator

    if not (args.year and args.make and args.model and args.mileage is not None):
        print("Provide --year --make --model --mileage")
        return

    est = CostEstimator()
    recs = est.recommend_services(args.make, args.model, args.mileage)
    due = [r for r in recs if r.due_now]
    coming = [r for r in recs if not r.due_now]

    print(f"\n{'='*60}")
    print(f"SERVICES FOR {args.year} {args.make} {args.model} @ {args.mileage:,} MILES")
    print(f"{'='*60}")
    if due:
        print("\nLIKELY DUE NOW (mileage >= interval):")
        for r in due:
            print(f"  - {r.service_name} (interval: {r.mileage_interval:,} mi)")
    else:
        print("\nLIKELY DUE NOW: None")
    if coming:
        print("\nCOMING UP (mileage < interval):")
        for r in coming:
            print(f"  - {r.service_name} (interval: {r.mileage_interval:,} mi)")
    print(f"\n(Intervals from data/reference/maintenance_intervals*.csv)")


def main():
    parser = argparse.ArgumentParser(description="Test the auto maintenance pipeline")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # recalls
    rp = subparsers.add_parser("recalls", help="Run recalls lookup only")
    rp.add_argument("--vin", help="VIN to check")
    rp.add_argument("--make", help="Make (with --model --year)")
    rp.add_argument("--model", help="Model (with --make --year)")
    rp.add_argument("--year", type=int, help="Year (with --make --model)")
    rp.add_argument("--vehicles", nargs="+", help='e.g. "Toyota,Camry,2020" "Honda,Accord,2019"')
    rp.set_defaults(func=run_recalls)

    # pipeline
    pp = subparsers.add_parser("pipeline", help="Run full pipeline")
    pp.add_argument("--vins", nargs="+", help="VINs for recalls")
    pp.add_argument("--vehicles", nargs="+", help='e.g. "Toyota,Camry,2020"')
    pp.add_argument("--dealer-urls", nargs="+", help="Dealer service page URLs")
    pp.add_argument("--parts", nargs="+", help="Part names to search")
    pp.add_argument("--skip-oem", action="store_true")
    pp.add_argument("--skip-dealer", action="store_true")
    pp.add_argument("--skip-labor", action="store_true")
    pp.add_argument("--skip-parts", action="store_true")
    pp.add_argument("--skip-recalls", action="store_true")
    pp.set_defaults(func=run_pipeline)

    # estimate
    ep = subparsers.add_parser("estimate", help="Cost estimate (all data from code)")
    ep.add_argument("--make", help="Make (e.g. Toyota, BMW)")
    ep.add_argument("--model", help="Model (e.g. Camry, M3)")
    ep.add_argument("--year", type=int, help="Year (e.g. 2020)")
    ep.add_argument("--service", help="Service name (see --list-services)")
    ep.add_argument("--brakes", action="store_true", help="Brake pads front+rear")
    ep.add_argument("--list-services", action="store_true", help="List available services")
    ep.set_defaults(func=run_estimate)

    # quote
    qp = subparsers.add_parser("quote", help="Get quote: year, make, model, service (+ mileage for recommended services)")
    qp.add_argument("--year", type=int, required=True, help="Year (e.g. 2020)")
    qp.add_argument("--make", required=True, help="Make (e.g. Honda, Toyota)")
    qp.add_argument("--model", required=True, help="Model (e.g. Civic, Camry)")
    qp.add_argument("--mileage", type=int, help="Mileage (optional; when provided, show services likely due)")
    qp.add_argument("--service", required=True, help="Service name (see estimate --list-services)")
    qp.set_defaults(func=run_quote)

    # recommend
    rp = subparsers.add_parser("recommend", help="Recommend services based on mileage")
    rp.add_argument("--year", type=int, required=True, help="Year (e.g. 2020)")
    rp.add_argument("--make", required=True, help="Make (e.g. Honda, Toyota)")
    rp.add_argument("--model", required=True, help="Model (e.g. Civic, Camry)")
    rp.add_argument("--mileage", type=int, required=True, help="Current mileage")
    rp.set_defaults(func=run_recommend)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
