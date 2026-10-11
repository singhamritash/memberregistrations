"""Member outreach helpers: templates, SSN masking and the simulated-send log.

Sending is simulated for now (PRD answer 12): nothing is emailed. Each send is
appended to outreach_log.csv in the project folder instead.
"""

from datetime import datetime
from pathlib import Path

import pandas as pd

LOG_PATH = Path(__file__).resolve().parent / "outreach_log.csv"
LOG_COLUMNS = ["timestamp", "member_id", "email_id", "subject", "message", "delivery"]

# Placeholder drafts for the marketing team to edit ({first_name} is filled in automatically).
TEMPLATES = {
    "Template 1: Welcome, finish registration": {
        "subject": "Welcome! Finish your registration",
        "body": (
            "Hi {first_name},\n\n"
            "Welcome to our health app. Please finish your registration so you can start "
            "tracking your care.\n\n"
            "Thank you,\nMember Engagement Team"
        ),
    },
    "Template 2: Reminder, registration pending": {
        "subject": "Your registration is still pending",
        "body": (
            "Hi {first_name},\n\n"
            "We noticed your registration is not complete yet. It takes only a few minutes "
            "to finish.\n\n"
            "Thank you,\nMember Engagement Team"
        ),
    },
    "Template 3: Thank you, registration confirmed": {
        "subject": "Thank you for registering",
        "body": (
            "Hi {first_name},\n\n"
            "Thank you for registering. Explore the member portal for tips and resources "
            "for your health.\n\n"
            "Thank you,\nMember Engagement Team"
        ),
    },
}


def render_template(template_name: str, first_name: str) -> tuple[str, str]:
    template = TEMPLATES[template_name]
    return template["subject"], template["body"].format(first_name=first_name)


def mask_ssn(ssn: str) -> str:
    """Show only the last 4 digits of an SSN (PRD answer 14)."""
    return f"***-**-{ssn[-4:]}"


def mask_ssn_column(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy of df with SSN masked, so screens and downloads show only the last 4 digits."""
    if "SSN" not in df.columns:
        return df
    masked = df.copy()
    masked["SSN"] = masked["SSN"].map(mask_ssn)
    return masked


def log_outreach(member_id: str, email_id: str, subject: str, message: str) -> None:
    """Append one simulated send to outreach_log.csv, creating the file with a header if needed."""
    entry = pd.DataFrame(
        [
            {
                "timestamp": datetime.now().isoformat(timespec="seconds"),
                "member_id": member_id,
                "email_id": email_id,
                "subject": subject,
                "message": message,
                "delivery": "SIMULATED (not emailed)",
            }
        ],
        columns=LOG_COLUMNS,
    )
    entry.to_csv(LOG_PATH, mode="a", header=not LOG_PATH.exists(), index=False)
