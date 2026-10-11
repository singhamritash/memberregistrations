"""Generate the synthetic 1,000,000-record members file: Data/Master.csv.

Rules come from "CSV creation Prompt.txt":
  - first_name / last_name: fixed 10 alphabetic characters
  - Date_of_Birth: CCYY-MM-DD, between 1980-01-01 and 2009-12-31
  - SSN: dummy 10-digit number
  - member_id: fixed 10-character alphanumeric
  - email_id: last_name.first_name@gmail.com
  - relationship_code: EE or SP (50/50)
  - registration_status: Y or N (50/50)
  - registration_date: CCYY-MM-DD, 2026-01-01 through 2026-09-30 (PRD answer 8)

All values are randomly generated. No real member data is used.
"""

import string
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

ROWS = 1_000_000
SEED = 2026
OUTPUT = Path(__file__).resolve().parent / "Data" / "Master.csv"

DOB_START = date(1980, 1, 1)
DOB_END = date(2009, 12, 31)
REG_START = date(2026, 1, 1)
REG_END = date(2026, 9, 30)

ALNUM = np.array(list(string.ascii_uppercase + string.digits))
LETTERS = np.array(list(string.ascii_letters[:26].upper()))
LOWER = np.array(list(string.ascii_lowercase))


def join_chars(chars: np.ndarray) -> np.ndarray:
    """Join a (n, width) array of single characters into n strings."""
    chars = np.ascontiguousarray(chars)
    return chars.view(f"U{chars.shape[1]}").ravel()


def random_names(rng: np.random.Generator, n: int, width: int = 10) -> np.ndarray:
    """Return n capitalised alphabetic names of exactly `width` letters."""
    first = rng.choice(LETTERS, size=(n, 1))
    rest = rng.choice(LOWER, size=(n, width - 1))
    return join_chars(np.concatenate([first, rest], axis=1))


def random_ids(rng: np.random.Generator, n: int, width: int = 10) -> np.ndarray:
    """Return n uppercase alphanumeric IDs of exactly `width` characters."""
    return join_chars(rng.choice(ALNUM, size=(n, width)))


def random_ssn(rng: np.random.Generator, n: int) -> np.ndarray:
    """Return n dummy 10-digit SSN-style numbers (first digit never 0)."""
    digits = np.concatenate(
        [rng.integers(1, 10, size=(n, 1)), rng.integers(0, 10, size=(n, 9))], axis=1
    ).astype("U1")
    return join_chars(digits)


def random_dates(rng: np.random.Generator, n: int, start: date, end: date) -> np.ndarray:
    """Return n random dates in [start, end] formatted CCYY-MM-DD."""
    span = (end - start).days
    offsets = rng.integers(0, span + 1, size=n)
    base = np.datetime64(start.isoformat())
    return np.datetime_as_string(base + offsets.astype("timedelta64[D]"), unit="D")


def build_frame(rows: int = ROWS, seed: int = SEED) -> pd.DataFrame:
    rng = np.random.default_rng(seed)

    first_name = random_names(rng, rows)
    last_name = random_names(rng, rows)
    dob = random_dates(rng, rows, DOB_START, DOB_END)
    ssn = random_ssn(rng, rows)
    member_id = random_ids(rng, rows)
    email = np.char.add(
        np.char.add(np.char.lower(last_name), "."),
        np.char.add(np.char.lower(first_name), "@gmail.com"),
    )
    relationship = rng.choice(np.array(["EE", "SP"]), size=rows)
    status = rng.choice(np.array(["Y", "N"]), size=rows)
    reg_date = random_dates(rng, rows, REG_START, REG_END)

    return pd.DataFrame(
        {
            "first_name": first_name,
            "last_name": last_name,
            "Date_of_Birth": dob,
            "SSN": ssn,
            "member_id": member_id,
            "email_id": email,
            "relationship_code": relationship,
            "registration_status": status,
            "registration_date": reg_date,
        }
    )


def main() -> None:
    OUTPUT.parent.mkdir(exist_ok=True)
    df = build_frame()
    dupes = int(df["member_id"].duplicated().sum())
    df.to_csv(OUTPUT, index=False)
    print(f"Wrote {len(df):,} rows to {OUTPUT}")
    print(f"Duplicate member_id values: {dupes}")


if __name__ == "__main__":
    main()
