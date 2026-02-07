from pathlib import Path

import pandas as pd
from sqlmodel import SQLModel, create_engine

from backend.models import MaintenanceSchedule


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [col.strip().lower() for col in df.columns]
    return df


def validate_columns(df: pd.DataFrame) -> None:
    required = {
        "make",
        "model",
        "year",
        "interval_miles",
        "service_task",
        "description",
        "severity",
    }
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")


def ensure_required_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if "service_task" not in df.columns and "service_category" in df.columns:
        df["service_task"] = df["service_category"]

    if "severity" not in df.columns:
        def infer_severity(value: str) -> str:
            text = str(value).lower()
            if "critical" in text:
                return "Critical"
            if "major" in text:
                return "Major"
            return "Routine"

        basis = df["service_task"] if "service_task" in df.columns else df["description"]
        df["severity"] = basis.map(infer_severity)

    return df


def apply_rules(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    df["year"] = pd.to_numeric(df["year"], errors="coerce").fillna(0).astype(int)
    df["interval_miles"] = (
        pd.to_numeric(df["interval_miles"], errors="coerce").fillna(0).astype(int)
    )

    ghost_mask = (df["model"] == "TRX") & (df["year"] < 2021)
    df = df.loc[~ghost_mask].reset_index(drop=True)

    oil_mask = (
        df["make"].isin(["Toyota", "Honda", "Ford"])
        & (df["year"] > 2016)
        & (df["service_task"] == "Oil Service")
    )
    df.loc[oil_mask, "interval_miles"] = 10000
    df.loc[oil_mask, "description"] = "Synthetic Oil Change"

    trx_years = sorted(df.loc[df["model"] == "TRX", "year"].unique().tolist())
    if trx_years:
        trx_rows = df.loc[df["model"] == "TRX"]
        trx_make_by_year = (
            trx_rows.groupby("year")["make"].first().to_dict() if not trx_rows.empty else {}
        )
        injected_rows = []
        for year in trx_years:
            injected_rows.append(
                {
                    "make": trx_make_by_year.get(year, "Ram"),
                    "model": "TRX",
                    "year": int(year),
                    "interval_miles": 15000,
                    "service_task": "Diff Fluid Check",
                    "description": "Inspect Front/Rear Axle Fluid & Transfer Case (High Performance)",
                    "severity": "Critical",
                }
            )
        df = pd.concat([df, pd.DataFrame(injected_rows)], ignore_index=True)

    return df


def main() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    csv_path = repo_root / "full_precise_maintenance_schedule.csv"
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV not found at {csv_path}")

    df = pd.read_csv(csv_path)
    df = normalize_columns(df)
    df = ensure_required_columns(df)
    validate_columns(df)
    df = apply_rules(df)

    db_path = Path(__file__).resolve().parent / "maintenance.db"
    engine = create_engine(f"sqlite:///{db_path}")
    SQLModel.metadata.create_all(engine)

    df.to_sql(MaintenanceSchedule.__tablename__, engine, if_exists="replace", index=False)
    print(f"Seeded {len(df)} rows into {db_path}")


if __name__ == "__main__":
    main()
