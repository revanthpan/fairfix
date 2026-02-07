"""
Flask API for auto maintenance pipeline.
Serves quote, recommend, and services endpoints.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

from src.estimator import CostEstimator

app = Flask(__name__, static_folder="frontend", static_url_path="")
CORS(app)

estimator = CostEstimator()


def estimate_to_dict(est):
    """Convert CostEstimate to JSON-serializable dict."""
    if est is None:
        return None
    return {
        "shop_type": est.shop_type,
        "total_ci_low": round(est.total_ci_low, 0),
        "total_ci_high": round(est.total_ci_high, 0),
        "labor_cost_ci_low": round(est.labor_cost_ci_low, 0),
        "labor_cost_ci_high": round(est.labor_cost_ci_high, 0),
        "parts_ci_low": round(est.parts_ci_low, 0),
        "parts_ci_high": round(est.parts_ci_high, 0),
    }


@app.route("/")
def index():
    return send_from_directory("frontend", "index.html")


@app.route("/api/services", methods=["GET"])
def get_services():
    """List available services."""
    services = sorted(estimator._labor_standards.keys())
    return jsonify({"services": services})


@app.route("/api/quote", methods=["POST"])
def quote():
    """Get cost quote for year, make, model, service."""
    data = request.get_json() or request.form
    year = int(data.get("year", 0))
    make = data.get("make", "").strip()
    model = data.get("model", "").strip()
    service = data.get("service", "").strip()
    mileage = data.get("mileage")  # optional

    if not (year and make and model and service):
        return jsonify({"error": "year, make, model, service required"}), 400

    # Brakes shorthand
    if service.lower() in ("brakes", "brake pads", "brake pads full"):
        result = estimator.estimate_brakes_full(make, model, year)
    else:
        result = estimator.estimate(make, model, year, service)

    if not result:
        return jsonify({"error": "Unknown service"}), 400

    response = {
        "make": result.make,
        "model": result.model,
        "year": result.year,
        "service": result.service,
        "vehicle_tier": result.vehicle_tier,
        "labor_hours": result.labor_hours,
        "dealer": estimate_to_dict(result.dealer),
        "indy": estimate_to_dict(result.indy),
        "indy_savings_ci_low": round(result.indy_savings_ci_low, 0),
        "indy_savings_ci_high": round(result.indy_savings_ci_high, 0),
    }

    if mileage is not None:
        mileage = int(mileage)
        recs = estimator.recommend_services(make, model, mileage)
        response["recommended_services"] = [
            {"service_name": r.service_name, "mileage_interval": r.mileage_interval, "due_now": r.due_now}
            for r in recs
        ]

    return jsonify(response)


@app.route("/api/recommend", methods=["POST"])
def recommend():
    """Recommend services based on year, make, model, mileage."""
    data = request.get_json() or request.form
    year = int(data.get("year", 0))
    make = data.get("make", "").strip()
    model = data.get("model", "").strip()
    mileage = int(data.get("mileage", 0))

    if not (year and make and model and mileage):
        return jsonify({"error": "year, make, model, mileage required"}), 400

    recs = estimator.recommend_services(make, model, mileage)
    return jsonify({
        "make": make,
        "model": model,
        "year": year,
        "mileage": mileage,
        "services": [
            {"service_name": r.service_name, "mileage_interval": r.mileage_interval, "due_now": r.due_now}
            for r in recs
        ],
    })


@app.route("/<path:path>")
def serve_frontend(path):
    """Serve frontend static files."""
    return send_from_directory("frontend", path)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
