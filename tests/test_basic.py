"""Basic smoke tests – run after generation."""

import pytest
from pathlib import Path
import pandas as pd

DATA = Path(__file__).resolve().parents[1] / "data" / "csv"


@pytest.fixture(scope="module")
def tables():
    if not DATA.exists():
        pytest.skip("Data not generated – run python -m src.generate first")
    return {
        name: pd.read_csv(DATA / f"{name}.csv")
        for name in [
            "facilities", "docks", "appointments", "shipments",
            "check_in_events", "ground_truth", "exceptions",
        ]
    }


def test_row_counts_positive(tables):
    for name, df in tables.items():
        assert len(df) > 0, f"{name} is empty"


def test_appointment_pk_unique(tables):
    df = tables["appointments"]
    assert df["appointment_id"].nunique() == len(df)


def test_fk_appointments_dock(tables):
    docks = set(tables["docks"]["dock_id"])
    assert tables["appointments"]["dock_id"].isin(docks).all()


def test_ground_truth_exists(tables):
    assert len(tables["ground_truth"]) > 0


def test_events_have_sequence(tables):
    ev = tables["check_in_events"]
    assert "sequence" in ev.columns
    assert ev["sequence"].min() >= 1
