"""Data access layer: loads Data/Master.csv once and answers the app's queries."""

from pathlib import Path

import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent
MASTER_PATH = PROJECT_ROOT / "Data" / "Master.csv"

REG_MIN = pd.Timestamp("2026-01-01")
REG_MAX = pd.Timestamp("2026-09-30")
STATUS_VALUES = ["Y", "N"]
RELATIONSHIP_VALUES = ["EE", "SP"]


@st.cache_data(show_spinner="Loading Master.csv (1,000,000 rows)...")
def load_master() -> pd.DataFrame:
    return pd.read_csv(
        MASTER_PATH,
        dtype={
            "first_name": str,
            "last_name": str,
            "Date_of_Birth": str,
            "SSN": str,
            "member_id": str,
            "email_id": str,
            "relationship_code": "category",
            "registration_status": "category",
        },
        parse_dates=["registration_date"],
    )


@st.cache_data(show_spinner=False)
def daily_table() -> pd.DataFrame:
    """Registration counts per calendar day, split by Y and N, plus Total."""
    df = load_master()
    table = (
        df.groupby(["registration_date", "registration_status"], observed=True)
        .size()
        .unstack(fill_value=0)
        .reindex(columns=STATUS_VALUES, fill_value=0)
    )
    table["Total"] = table["Y"] + table["N"]
    return table


@st.cache_data(show_spinner=False)
def monthly_table() -> pd.DataFrame:
    """Registration counts per calendar month, split by Y and N, plus Total."""
    table = daily_table().copy()
    table["Month"] = table.index.to_period("M").astype(str)
    return table.groupby("Month")[STATUS_VALUES + ["Total"]].sum()


def month_bounds(year: int, month: int) -> tuple[pd.Timestamp, pd.Timestamp]:
    start = pd.Timestamp(year=year, month=month, day=1)
    return start, start + pd.offsets.MonthEnd(0)


def month_daily(year: int, month: int) -> pd.DataFrame:
    """Every day of the month (zero-filled) with Y, N and Total counts."""
    start, end = month_bounds(year, month)
    days = pd.date_range(start, end, freq="D")
    out = daily_table().reindex(days, fill_value=0)
    out.index.name = "date"
    return out


def in_month(df: pd.DataFrame, year: int, month: int) -> pd.Series:
    start, end = month_bounds(year, month)
    return (df["registration_date"] >= start) & (df["registration_date"] <= end)


def search_members(field: str, query: str, limit: int = 50) -> tuple[pd.DataFrame, int]:
    """Partial, case-insensitive search on member_id or SSN. Returns (rows, total matches)."""
    df = load_master()
    column = "SSN" if field == "SSN" else "member_id"
    mask = df[column].str.contains(query, case=False, regex=False, na=False)
    matches = df.loc[mask]
    return matches.head(limit), len(matches)


def members_not_registered(year: int, month: int) -> pd.DataFrame:
    df = load_master()
    return df.loc[in_month(df, year, month) & (df["registration_status"] == "N")]


def stats_for_day(day: pd.Timestamp) -> pd.DataFrame:
    """Breakdown of one day's registrations by status and relationship code."""
    df = load_master()
    day_rows = df.loc[df["registration_date"] == day]
    breakdown = (
        day_rows.groupby(["relationship_code", "registration_status"], observed=True)
        .size()
        .unstack(fill_value=0)
        .reindex(index=RELATIONSHIP_VALUES, columns=STATUS_VALUES, fill_value=0)
    )
    breakdown["Total"] = breakdown["Y"] + breakdown["N"]
    breakdown.loc["All"] = breakdown.sum()
    breakdown.columns.name = None
    return breakdown.reset_index().rename(columns={"relationship_code": "Relationship"})


def status_by_month(status: str, year: int, month: int) -> pd.DataFrame:
    df = load_master()
    return df.loc[in_month(df, year, month) & (df["registration_status"] == status)]


def by_relationship(code: str) -> pd.DataFrame:
    df = load_master()
    return df.loc[df["relationship_code"] == code]
