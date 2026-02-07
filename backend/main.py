from pathlib import Path
import random
from typing import Tuple

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from geopy.geocoders import Nominatim
from sqlmodel import Session, SQLModel, create_engine, select

from backend.models import MaintenanceSchedule, Severity
from backend_dataset.src.estimator import CostEstimator


app = FastAPI(title="Vehicle Maintenance Intelligence")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_PATH = Path(__file__).resolve().parent / "maintenance.db"
engine = create_engine(f"sqlite:///{DB_PATH}")
SQLModel.metadata.create_all(engine)

estimator = CostEstimator()
geocoder = Nominatim(user_agent="fairfix-quote-engine")


def estimate_cost(severity: Severity) -> int:
    if severity == Severity.Routine:
        return 80
    if severity == Severity.Major:
        return 400
    return 800


@app.get("/maintenance-forecast")
def maintenance_forecast(
    make: str = Query(..., min_length=1),
    model: str = Query(..., min_length=1),
    year: int = Query(..., ge=1900),
    current_mileage: int = Query(..., ge=0),
):
    with Session(engine) as session:
        statement = select(MaintenanceSchedule).where(
            MaintenanceSchedule.make == make,
            MaintenanceSchedule.model == model,
            MaintenanceSchedule.year == year,
        )
        schedules = session.exec(statement).all()

    if not schedules:
        raise HTTPException(status_code=404, detail="No schedule found for that vehicle.")

    upcoming = sorted(
        (item for item in schedules if item.interval_miles > current_mileage),
        key=lambda item: item.interval_miles,
    )
    if not upcoming:
        next_service = max(schedules, key=lambda item: item.interval_miles)
    else:
        next_service = upcoming[0]

    overdue = current_mileage > next_service.interval_miles + 500
    status = "Overdue" if overdue else "Good"

    miles_until = max(next_service.interval_miles - current_mileage, 0)

    return {
        "status": status,
        "next_service_due_at": next_service.interval_miles,
        "miles_until_service": miles_until,
        "estimated_cost": estimate_cost(next_service.severity),
    }

@app.get("/schedule")
def schedule(
    make: str = Query(..., min_length=1),
    model: str = Query(..., min_length=1),
    year: int = Query(..., ge=1900),
    mileage: int = Query(..., ge=0),
):
    recommendations = estimator.recommend_services(make, model, mileage)
    if not recommendations:
        raise HTTPException(status_code=404, detail="No schedule found for that vehicle.")

    upper_bound = mileage + 5000
    due_soon = [
        item
        for item in recommendations
        if mileage <= item.mileage_interval <= upper_bound
    ]

    return [
        {
            "service_task": item.service_name,
            "interval_miles": item.mileage_interval,
            "description": f"Service due around {item.mileage_interval:,} miles.",
            "severity": "Routine",
        }
        for item in due_soon
    ]


@app.get("/quotes")
def quotes(
    service_name: str = Query(..., min_length=1),
    make: str = Query(..., min_length=1),
    model: str = Query(..., min_length=1),
    year: int = Query(..., ge=1900),
    zip_code: str = Query(..., min_length=3),
):
    def geocode_zip(value: str) -> Tuple[float, float]:
        location = geocoder.geocode({"postalcode": value, "country": "US"})
        if not location:
            raise HTTPException(status_code=404, detail="Unable to locate that zip code.")
        return location.latitude, location.longitude

    user_lat, user_lng = geocode_zip(zip_code)
    normalized_service = service_name.strip().lower()
    service_lookup = {
        "oil change": "Oil Change",
        "battery replacement": "Battery Replacement",
        "tire rotation": "Tire Rotation",
        "spark plug service": "Spark Plug Replacement (4-cyl)",
    }

    estimate = None
    if normalized_service in {"brake pad replacement", "brake pads"}:
        estimate = estimator.estimate_brakes_full(make, model, year)
    else:
        mapped_service = service_lookup.get(service_name.strip().lower(), service_name.strip())
        estimate = estimator.estimate(make, model, year, mapped_service)

    dealer_names = [
        f"{make.title()} {model.title()} Authorized Dealer",
        f"{make.title()} Certified Service Center",
    ]
    indy_names = [
        "Main Street Auto",
        "Neighborhood Garage",
        "Precision Auto Care",
    ]

    quotes_list = []
    if estimate:
        dealer_low, dealer_high = estimate.dealer.total_ci_low, estimate.dealer.total_ci_high
        indy_low, indy_high = estimate.indy.total_ci_low, estimate.indy.total_ci_high
        for name in dealer_names:
            price = round(random.uniform(dealer_low, dealer_high))
            shop_lat = user_lat + random.uniform(-0.02, 0.02)
            shop_lng = user_lng + random.uniform(-0.02, 0.02)
            quotes_list.append(
                {
                    "name": name,
                    "price": price,
                    "type": "Dealer",
                    "distance": round(random.uniform(2.0, 15.0), 1),
                    "lat": round(shop_lat, 6),
                    "lng": round(shop_lng, 6),
                }
            )

        for name in indy_names:
            price = round(random.uniform(indy_low, indy_high))
            shop_lat = user_lat + random.uniform(-0.02, 0.02)
            shop_lng = user_lng + random.uniform(-0.02, 0.02)
            quotes_list.append(
                {
                    "name": name,
                    "price": price,
                    "type": "Indy",
                    "distance": round(random.uniform(1.0, 12.0), 1),
                    "lat": round(shop_lat, 6),
                    "lng": round(shop_lng, 6),
                }
            )
    else:
        service_price_bands = {
            "oil change": (60, 140),
            "brake pad replacement": (220, 520),
            "battery replacement": (120, 280),
            "tire rotation": (40, 120),
            "spark plug service": (180, 420),
        }
        low, high = service_price_bands.get(normalized_service, (200, 550))
        base_price = random.randint(low, high)

        for name in dealer_names:
            price = round(base_price * 1.4)
            shop_lat = user_lat + random.uniform(-0.02, 0.02)
            shop_lng = user_lng + random.uniform(-0.02, 0.02)
            quotes_list.append(
                {
                    "name": name,
                    "price": price,
                    "type": "Dealer",
                    "distance": round(random.uniform(2.0, 15.0), 1),
                    "lat": round(shop_lat, 6),
                    "lng": round(shop_lng, 6),
                }
            )

        for name in indy_names:
            price = round(base_price * random.uniform(0.75, 0.95))
            shop_lat = user_lat + random.uniform(-0.02, 0.02)
            shop_lng = user_lng + random.uniform(-0.02, 0.02)
            quotes_list.append(
                {
                    "name": name,
                    "price": price,
                    "type": "Indy",
                    "distance": round(random.uniform(1.0, 12.0), 1),
                    "lat": round(shop_lat, 6),
                    "lng": round(shop_lng, 6),
                }
            )

    return {
        "service": service_name,
        "vehicle": {"make": make, "model": model, "year": year},
        "center": {"lat": round(user_lat, 6), "lng": round(user_lng, 6)},
        "quotes": quotes_list,
    }
