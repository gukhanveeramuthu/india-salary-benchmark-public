"""
Loads the salary dataset without the raw CSV ever being committed to this
(public) repo's git history.

Two sources, tried in order:

1. **Private GitHub repo, via Streamlit secrets** (used in production/
   deployed app). Configure three secrets - github_token, data_repo,
   data_path - and this fetches the CSV straight from GitHub's Contents
   API using a short-lived, read-only, single-repo-scoped token. Nothing
   about the dataset ever touches this repo's git history.
2. **Local file fallback** (used for local development only). If the
   secrets above aren't configured - e.g. running `streamlit run app.py`
   on your own machine before you've set anything up - this looks for
   data/india_salaries_deduped.csv on disk instead. That path is in
   .gitignore, so even locally it's never committed by accident.

See README.md ("Keeping the source data private") for the full setup.
"""

import os
import tempfile
from typing import Optional

import requests
import streamlit as st

from schema import load_observations, LoadReport, SalaryObservation

LOCAL_FALLBACK_PATH = os.path.join(os.path.dirname(__file__), "data", "india_salaries_deduped.csv")

GITHUB_API_VERSION = "2022-11-28"


def _read_secrets() -> Optional[dict]:
    """Returns the private-repo config from Streamlit secrets, or None if
    it isn't configured (so callers can fall back to a local file)."""
    try:
        return {
            "token": st.secrets["github_token"],
            "repo": st.secrets["data_repo"],   # "owner/repo-name"
            "path": st.secrets["data_path"],   # e.g. "india_salaries_deduped.csv"
        }
    except (KeyError, FileNotFoundError):
        return None


def _fetch_private_csv(token: str, repo: str, path: str) -> str:
    """Fetches path from repo's default branch via GitHub's Contents API
    and returns a local temp-file path to the downloaded CSV bytes.
    Raises requests.HTTPError on any failure (bad token, wrong repo/path,
    rate limit, etc.) - callers should let this surface, not swallow it,
    since a silent fallback to stale/wrong data would be worse than a
    visible error."""
    url = f"https://api.github.com/repos/{repo}/contents/{path}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.raw",
        "X-GitHub-Api-Version": GITHUB_API_VERSION,
    }
    resp = requests.get(url, headers=headers, timeout=20)
    resp.raise_for_status()

    tmp = tempfile.NamedTemporaryFile(mode="wb", suffix=".csv", delete=False)
    tmp.write(resp.content)
    tmp.close()
    return tmp.name


def load_dataset() -> tuple[list[SalaryObservation], LoadReport]:
    """Returns (observations, report), exactly like schema.load_observations
    - this is a thin wrapper that only decides *where* the CSV comes from."""
    secrets = _read_secrets()

    if secrets is not None:
        csv_path = _fetch_private_csv(**secrets)
        return load_observations(csv_path)

    if os.path.exists(LOCAL_FALLBACK_PATH):
        return load_observations(LOCAL_FALLBACK_PATH)

    raise FileNotFoundError(
        "No dataset available: Streamlit secrets (github_token / data_repo / "
        "data_path) aren't configured, and there's no local "
        f"{LOCAL_FALLBACK_PATH} either. See README.md 'Keeping the source "
        "data private' for setup."
    )
