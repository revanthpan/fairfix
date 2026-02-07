"""
Cost Estimator - Produces dollar estimates from code data only.

Uses:
- Labor hours (from labor_standards)
- Labor rates (from data/reference/labor_rates.csv) - rate_mean, rate_std
- Parts estimates (from data/reference/parts_estimates.csv) - parts_mean, parts_std
- Vehicle tier (from data/reference/vehicle_tiers.csv)

All pricing comes from reference data in the codebase.
Price ranges are 95% confidence intervals (mean ± 1.96 * std).
"""

import csv
import math
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

# 95% confidence interval multiplier (z-score for normal distribution)
Z_95 = 1.96

# Project root for imports
PROJECT_ROOT = Path(__file__).parent.parent


@dataclass
class CostEstimate:
    """Single cost estimate (dealer or indy) with 95% CI."""
    shop_type: str
    vehicle_tier: str
    service: str
    labor_hours: float
    labor_rate_mean: float
    labor_rate_std: float
    labor_rate_ci_low: float
    labor_rate_ci_high: float
    labor_cost_mean: float
    labor_cost_std: float
    labor_cost_ci_low: float
    labor_cost_ci_high: float
    parts_mean: float
    parts_std: float
    parts_ci_low: float
    parts_ci_high: float
    total_mean: float
    total_std: float
    total_ci_low: float
    total_ci_high: float


@dataclass
class RecommendedService:
    """Service recommended based on mileage interval."""
    service_name: str
    mileage_interval: int
    due_now: bool  # True if current mileage >= interval


@dataclass
class EstimateResult:
    """Full estimate result with dealer and indy (95% CI)."""
    make: str
    model: str
    year: int
    service: str
    vehicle_tier: str
    labor_hours: float
    dealer: CostEstimate
    indy: CostEstimate
    indy_savings_ci_low: float
    indy_savings_ci_high: float


class CostEstimator:
    """
    Estimates repair costs from code reference data only.
    Price ranges are 95% confidence intervals.
    """

    def __init__(self):
        self.ref_dir = PROJECT_ROOT / "data" / "reference"
        self._labor_standards: dict[str, float] = {}
        self._labor_rates: dict[tuple[str, str], tuple[float, float]] = {}  # (shop, tier) -> (mean, std)
        self._parts_estimates: dict[tuple[str, str], tuple[float, float]] = {}  # (service, tier) -> (mean, std)
        self._vehicle_tiers: dict[tuple[str, str], str] = {}
        self._make_tiers: dict[str, str] = {}
        self._maintenance_intervals: dict[tuple[str, str], dict[str, int]] = {}  # (make, model) -> {service: miles}
        self._maintenance_intervals_tier: dict[str, dict[str, int]] = {}  # tier -> {service: miles}
        self._load_reference_data()

    def _load_reference_data(self):
        """Load all reference data from CSV files."""
        # Labor standards
        labor_ops = [
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
        self._labor_standards = dict(labor_ops)

        # Labor rates (mean, std)
        with open(self.ref_dir / "labor_rates.csv") as f:
            for row in csv.DictReader(f):
                key = (row["shop_type"], row["vehicle_tier"])
                self._labor_rates[key] = (float(row["rate_mean"]), float(row["rate_std"]))

        # Parts estimates (mean, std)
        with open(self.ref_dir / "parts_estimates.csv") as f:
            for row in csv.DictReader(f):
                key = (row["service_name"], row["vehicle_tier"])
                self._parts_estimates[key] = (float(row["parts_mean"]), float(row["parts_std"]))

        # Maintenance intervals (make/model specific)
        with open(self.ref_dir / "maintenance_intervals.csv") as f:
            for row in csv.DictReader(f):
                make, model = row["make"].strip().lower(), row["model"].strip().lower()
                svc, miles = row["service_name"].strip(), int(row["mileage_interval"])
                key = (make, model)
                if key not in self._maintenance_intervals:
                    self._maintenance_intervals[key] = {}
                self._maintenance_intervals[key][svc] = miles

        # Maintenance intervals (tier fallback)
        with open(self.ref_dir / "maintenance_intervals_tier.csv") as f:
            for row in csv.DictReader(f):
                tier, svc, miles = row["vehicle_tier"].strip(), row["service_name"].strip(), int(row["mileage_interval"])
                if tier not in self._maintenance_intervals_tier:
                    self._maintenance_intervals_tier[tier] = {}
                self._maintenance_intervals_tier[tier][svc] = miles

        # Vehicle tiers
        with open(self.ref_dir / "vehicle_tiers.csv") as f:
            for row in csv.DictReader(f):
                make, model = row["make"].strip(), row["model"].strip()
                tier = row["tier"].strip()
                self._vehicle_tiers[(make.lower(), model.lower())] = tier
                if make.lower() not in self._make_tiers:
                    self._make_tiers[make.lower()] = tier

    def get_vehicle_tier(self, make: str, model: str) -> str:
        """Resolve vehicle tier from make/model. Fallback: make only, then 'mid'."""
        mk, md = make.strip().lower(), model.strip().lower()
        if (mk, md) in self._vehicle_tiers:
            return self._vehicle_tiers[(mk, md)]
        if mk in self._make_tiers:
            return self._make_tiers[mk]
        return "mid"

    def get_labor_hours(self, service: str) -> Optional[float]:
        """Get labor hours for service. Returns None if unknown."""
        return self._labor_standards.get(service)

    def get_labor_rates(self, tier: str, shop_type: str) -> tuple[float, float]:
        """Get labor rate (mean, std) for tier and shop type."""
        return self._labor_rates.get((shop_type, tier), (100.0, 10.0))

    def get_parts_estimate(self, service: str, tier: str) -> tuple[float, float]:
        """Get parts cost (mean, std) for service and tier."""
        return self._parts_estimates.get((service, tier), (0.0, 0.0))

    def recommend_services(
        self, make: str, model: str, mileage: int
    ) -> list[RecommendedService]:
        """
        Recommend services likely due based on mileage intervals.
        Uses make/model-specific intervals when available, else tier fallback.
        Returns services where mileage >= interval (due_now=True) or coming up.
        """
        mk, md = make.strip().lower(), model.strip().lower()
        tier = self.get_vehicle_tier(make, model)

        # Get interval map: make/model specific first, then tier fallback
        intervals: dict[str, int] = {}
        if (mk, md) in self._maintenance_intervals:
            intervals = self._maintenance_intervals[(mk, md)].copy()
        if tier in self._maintenance_intervals_tier:
            for svc, miles in self._maintenance_intervals_tier[tier].items():
                if svc not in intervals:
                    intervals[svc] = miles

        results: list[RecommendedService] = []
        for svc, interval in sorted(intervals.items()):
            due_now = mileage >= interval
            results.append(RecommendedService(
                service_name=svc,
                mileage_interval=interval,
                due_now=due_now,
            ))
        return results

    def _apply_year_discount(self, rate_mean: float, rate_std: float, year: int, shop_type: str) -> tuple[float, float]:
        """Apply year-based discount for older vehicles at indy shops."""
        from datetime import datetime
        current_year = datetime.now().year
        age = current_year - year
        if shop_type == "indy" and age >= 10:
            discount = 0.9
            return (rate_mean * discount, rate_std * discount)
        return (rate_mean, rate_std)

    def _ci_bounds(self, mean: float, std: float) -> tuple[float, float]:
        """Compute 95% CI bounds."""
        ci_low = max(0, mean - Z_95 * std)
        ci_high = mean + Z_95 * std
        return (ci_low, ci_high)

    def estimate(
        self,
        make: str,
        model: str,
        year: int,
        service: str,
    ) -> Optional[EstimateResult]:
        """
        Produce cost estimate from code data only.
        Returns EstimateResult with dealer and indy estimates (95% CI), or None if service unknown.
        """
        labor_hours = self.get_labor_hours(service)
        if labor_hours is None:
            return None

        tier = self.get_vehicle_tier(make, model)

        # Labor rates (mean, std)
        dealer_mean, dealer_std = self.get_labor_rates(tier, "dealer")
        indy_mean, indy_std = self.get_labor_rates(tier, "indy")
        indy_mean, indy_std = self._apply_year_discount(indy_mean, indy_std, year, "indy")

        # Parts (mean, std)
        parts_mean, parts_std = self.get_parts_estimate(service, tier)

        # Dealer estimate
        dealer_labor_mean = labor_hours * dealer_mean
        dealer_labor_std = labor_hours * dealer_std
        dealer_total_mean = dealer_labor_mean + parts_mean
        dealer_total_std = math.sqrt(dealer_labor_std ** 2 + parts_std ** 2)

        dealer_est = CostEstimate(
            shop_type="dealer",
            vehicle_tier=tier,
            service=service,
            labor_hours=labor_hours,
            labor_rate_mean=dealer_mean,
            labor_rate_std=dealer_std,
            labor_rate_ci_low=self._ci_bounds(dealer_mean, dealer_std)[0],
            labor_rate_ci_high=self._ci_bounds(dealer_mean, dealer_std)[1],
            labor_cost_mean=dealer_labor_mean,
            labor_cost_std=dealer_labor_std,
            labor_cost_ci_low=self._ci_bounds(dealer_labor_mean, dealer_labor_std)[0],
            labor_cost_ci_high=self._ci_bounds(dealer_labor_mean, dealer_labor_std)[1],
            parts_mean=parts_mean,
            parts_std=parts_std,
            parts_ci_low=self._ci_bounds(parts_mean, parts_std)[0],
            parts_ci_high=self._ci_bounds(parts_mean, parts_std)[1],
            total_mean=dealer_total_mean,
            total_std=dealer_total_std,
            total_ci_low=self._ci_bounds(dealer_total_mean, dealer_total_std)[0],
            total_ci_high=self._ci_bounds(dealer_total_mean, dealer_total_std)[1],
        )

        # Indy estimate
        indy_labor_mean = labor_hours * indy_mean
        indy_labor_std = labor_hours * indy_std
        indy_total_mean = indy_labor_mean + parts_mean
        indy_total_std = math.sqrt(indy_labor_std ** 2 + parts_std ** 2)

        indy_est = CostEstimate(
            shop_type="indy",
            vehicle_tier=tier,
            service=service,
            labor_hours=labor_hours,
            labor_rate_mean=indy_mean,
            labor_rate_std=indy_std,
            labor_rate_ci_low=self._ci_bounds(indy_mean, indy_std)[0],
            labor_rate_ci_high=self._ci_bounds(indy_mean, indy_std)[1],
            labor_cost_mean=indy_labor_mean,
            labor_cost_std=indy_labor_std,
            labor_cost_ci_low=self._ci_bounds(indy_labor_mean, indy_labor_std)[0],
            labor_cost_ci_high=self._ci_bounds(indy_labor_mean, indy_labor_std)[1],
            parts_mean=parts_mean,
            parts_std=parts_std,
            parts_ci_low=self._ci_bounds(parts_mean, parts_std)[0],
            parts_ci_high=self._ci_bounds(parts_mean, parts_std)[1],
            total_mean=indy_total_mean,
            total_std=indy_total_std,
            total_ci_low=self._ci_bounds(indy_total_mean, indy_total_std)[0],
            total_ci_high=self._ci_bounds(indy_total_mean, indy_total_std)[1],
        )

        savings_ci_low = dealer_est.total_ci_low - indy_est.total_ci_high
        savings_ci_high = dealer_est.total_ci_high - indy_est.total_ci_low

        return EstimateResult(
            make=make,
            model=model,
            year=year,
            service=service,
            vehicle_tier=tier,
            labor_hours=labor_hours,
            dealer=dealer_est,
            indy=indy_est,
            indy_savings_ci_low=max(0, savings_ci_low),
            indy_savings_ci_high=max(0, savings_ci_high),
        )

    def estimate_brakes_full(self, make: str, model: str, year: int) -> Optional[EstimateResult]:
        """Estimate front + rear brake pad replacement (combined)."""
        front = self.estimate(make, model, year, "Brake Pad Replacement (Front)")
        rear = self.estimate(make, model, year, "Brake Pad Replacement (Rear)")
        if not front or not rear:
            return None

        tier = front.vehicle_tier
        labor_hours = front.labor_hours + rear.labor_hours

        # Combine means and variances (independent)
        dealer_total_mean = front.dealer.total_mean + rear.dealer.total_mean
        dealer_total_std = math.sqrt(front.dealer.total_std ** 2 + rear.dealer.total_std ** 2)
        indy_total_mean = front.indy.total_mean + rear.indy.total_mean
        indy_total_std = math.sqrt(front.indy.total_std ** 2 + rear.indy.total_std ** 2)

        dealer = CostEstimate(
            shop_type="dealer",
            vehicle_tier=tier,
            service="Brake Pads (Front + Rear)",
            labor_hours=labor_hours,
            labor_rate_mean=front.dealer.labor_rate_mean,
            labor_rate_std=front.dealer.labor_rate_std,
            labor_rate_ci_low=front.dealer.labor_rate_ci_low,
            labor_rate_ci_high=front.dealer.labor_rate_ci_high,
            labor_cost_mean=front.dealer.labor_cost_mean + rear.dealer.labor_cost_mean,
            labor_cost_std=math.sqrt(front.dealer.labor_cost_std**2 + rear.dealer.labor_cost_std**2),
            labor_cost_ci_low=front.dealer.labor_cost_ci_low + rear.dealer.labor_cost_ci_low,
            labor_cost_ci_high=front.dealer.labor_cost_ci_high + rear.dealer.labor_cost_ci_high,
            parts_mean=front.dealer.parts_mean + rear.dealer.parts_mean,
            parts_std=math.sqrt(front.dealer.parts_std**2 + rear.dealer.parts_std**2),
            parts_ci_low=front.dealer.parts_ci_low + rear.dealer.parts_ci_low,
            parts_ci_high=front.dealer.parts_ci_high + rear.dealer.parts_ci_high,
            total_mean=dealer_total_mean,
            total_std=dealer_total_std,
            total_ci_low=self._ci_bounds(dealer_total_mean, dealer_total_std)[0],
            total_ci_high=self._ci_bounds(dealer_total_mean, dealer_total_std)[1],
        )
        indy = CostEstimate(
            shop_type="indy",
            vehicle_tier=tier,
            service="Brake Pads (Front + Rear)",
            labor_hours=labor_hours,
            labor_rate_mean=front.indy.labor_rate_mean,
            labor_rate_std=front.indy.labor_rate_std,
            labor_rate_ci_low=front.indy.labor_rate_ci_low,
            labor_rate_ci_high=front.indy.labor_rate_ci_high,
            labor_cost_mean=front.indy.labor_cost_mean + rear.indy.labor_cost_mean,
            labor_cost_std=math.sqrt(front.indy.labor_cost_std**2 + rear.indy.labor_cost_std**2),
            labor_cost_ci_low=front.indy.labor_cost_ci_low + rear.indy.labor_cost_ci_low,
            labor_cost_ci_high=front.indy.labor_cost_ci_high + rear.indy.labor_cost_ci_high,
            parts_mean=front.indy.parts_mean + rear.indy.parts_mean,
            parts_std=math.sqrt(front.indy.parts_std**2 + rear.indy.parts_std**2),
            parts_ci_low=front.indy.parts_ci_low + rear.indy.parts_ci_low,
            parts_ci_high=front.indy.parts_ci_high + rear.indy.parts_ci_high,
            total_mean=indy_total_mean,
            total_std=indy_total_std,
            total_ci_low=self._ci_bounds(indy_total_mean, indy_total_std)[0],
            total_ci_high=self._ci_bounds(indy_total_mean, indy_total_std)[1],
        )
        savings_ci_low = dealer.total_ci_low - indy.total_ci_high
        savings_ci_high = dealer.total_ci_high - indy.total_ci_low

        return EstimateResult(
            make=make,
            model=model,
            year=year,
            service="Brake Pads (Front + Rear)",
            vehicle_tier=tier,
            labor_hours=labor_hours,
            dealer=dealer,
            indy=indy,
            indy_savings_ci_low=max(0, savings_ci_low),
            indy_savings_ci_high=max(0, savings_ci_high),
        )
