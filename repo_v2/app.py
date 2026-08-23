"""
Streamlit front end for the India Professional Salary Benchmark engine.

This is the "minimal API + form" step the engine's own README listed as
the next open item — it does not touch any of the engine modules
(schema.py, cohort_engine.py, confidence.py, percentile_engine.py,
taxonomy.py, benchmark.py). It only calls run_benchmark() and renders
the result.
"""

import os
from collections import Counter

import streamlit as st

from schema import EXPERIENCE_LABELS
from benchmark import run_benchmark
from confidence import INSUFFICIENT, LOW, MODERATE, HIGH
from data_loader import load_dataset

# FRED H.10 / AEXINUS annual-average USD/INR rate, most recent period in
# the dataset (see data/README.md for the full cited table by year).
USD_INR_RATE = 87.15

CONFIDENCE_INFO = {
    HIGH: ("🟢", "High", "50+ comparable observations."),
    MODERATE: ("🟡", "Moderate", "20–49 comparable observations."),
    LOW: ("🟠", "Low", "10–19 comparable observations — treat with caution."),
    INSUFFICIENT: ("🔴", "Insufficient", "Fewer than 10 observations — no number is shown."),
}

st.set_page_config(page_title="India Salary Benchmark", page_icon="📊", layout="centered")


@st.cache_data(show_spinner="Loading dataset…")
def load_data():
    return load_dataset()


@st.cache_data(show_spinner=False)
def title_options(_observations):
    counts = Counter(o.job_title_raw.strip() for o in _observations if o.job_title_raw.strip())
    # Most common titles first, so the dropdown surfaces titles that are
    # actually likely to produce a real cohort.
    return [t for t, _ in counts.most_common(300)]


@st.cache_data(show_spinner=False)
def city_options(_observations):
    return sorted({o.city for o in _observations if o.city})


def format_inr(usd_value: float) -> str:
    """Convert a USD figure back to INR and format with Indian digit
    grouping (e.g. 12,50,000), for display to an India-based audience."""
    rupees = round(usd_value * USD_INR_RATE)
    s = str(rupees)
    if len(s) <= 3:
        grouped = s
    else:
        last3 = s[-3:]
        rest = s[:-3]
        parts = []
        while len(rest) > 2:
            parts.insert(0, rest[-2:])
            rest = rest[:-2]
        if rest:
            parts.insert(0, rest)
        grouped = ",".join(parts) + "," + last3
    return f"₹{grouped}"


def format_inr_short(usd_value: float) -> str:
    """Compact ₹ lakh/crore format for tight metric cards, e.g. ₹7.88L or ₹1.25Cr."""
    rupees = usd_value * USD_INR_RATE
    if rupees >= 1_00_00_000:
        return f"₹{rupees / 1_00_00_000:.2f}Cr"
    if rupees >= 1_00_000:
        return f"₹{rupees / 1_00_000:.2f}L"
    return f"₹{rupees:,.0f}"


try:
    observations, load_report = load_data()
except Exception as e:
    st.error(
        "Couldn't load the dataset. If you're setting this app up for the "
        "first time, check that the `github_token`, `data_repo`, and "
        "`data_path` secrets are configured — see README.md 'Keeping the "
        "source data private'."
    )
    st.exception(e)
    st.stop()

# --- one-time CSS for the hero percentile number and section labels ---
st.markdown(
    """
    <style>
    .hero-eyebrow {
        font-size: 0.8rem !important;
        font-weight: 600 !important;
        letter-spacing: 0.08em !important;
        text-transform: uppercase !important;
        color: #64748B !important;
        margin-bottom: 0.15rem !important;
    }
    .hero-percentile {
        font-size: 4.2rem !important;
        font-weight: 800 !important;
        line-height: 1.05 !important;
        color: #2563EB !important;
        margin: 0 !important;
    }
    .hero-percentile small {
        font-size: 1.6rem !important;
        font-weight: 600 !important;
        color: #0F172A !important;
    }
    .hero-salary {
        font-size: 1.05rem !important;
        color: #334155 !important;
        margin-top: 0.3rem !important;
    }
    .section-label {
        font-size: 0.78rem !important;
        font-weight: 700 !important;
        letter-spacing: 0.06em !important;
        text-transform: uppercase !important;
        color: #64748B !important;
        margin: 1.4rem 0 0.4rem 0 !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown('<div class="hero-eyebrow">India Career Benchmark</div>', unsafe_allow_html=True)
st.title("See where you really stand")
st.caption(
    "Enter your role, experience, city and salary. Get a real peer comparison — "
    "with an honest confidence rating, never a fabricated number."
)
n_sources = len({o.source_dataset for o in observations})
st.caption(
    f"📊 **{load_report.rows_loaded:,}** real observations · "
    f"**{n_sources}** public sources · transparent methodology"
)

with st.form("benchmark_form"):
    col1, col2 = st.columns(2)

    with col1:
        title_choice = st.selectbox(
            "Your role",
            ["Type my own…"] + title_options(observations),
            help="Pick the closest match, or type your own — an exact match isn't required, "
                 "the engine will broaden the comparison automatically if needed.",
        )
        if title_choice == "Type my own…":
            job_title = st.text_input("Enter your job title", "")
        else:
            job_title = title_choice

        experience_level = st.selectbox(
            "Experience",
            options=list(EXPERIENCE_LABELS.keys()),
            format_func=lambda k: EXPERIENCE_LABELS[k],
        )

    with col2:
        city_list = city_options(observations)
        city_choice = st.selectbox("City (optional)", ["All of India"] + city_list)
        city = None if city_choice == "All of India" else city_choice

        salary = st.number_input(
            "Your annual salary (₹ INR)",
            min_value=0,
            step=50000,
            value=1200000,
            help="Enter your gross annual salary in Indian Rupees.",
        )

    submitted = st.form_submit_button("Benchmark My Salary", use_container_width=True, type="primary")

if submitted:
    if not job_title.strip():
        st.error("Enter a job title to see your benchmark.")
    elif salary <= 0:
        st.error("Enter a salary greater than ₹0 to see your benchmark.")
    else:
        salary_in_usd = salary / USD_INR_RATE
        result = run_benchmark(
            observations,
            job_title=job_title,
            experience_level=experience_level,
            salary_currency="INR",
            user_salary_in_usd=salary_in_usd,
            city=city,
        )

        st.divider()

        if result.bands is None:
            icon, label, _ = CONFIDENCE_INFO[result.confidence]
            st.markdown('<div class="hero-eyebrow">Your result</div>', unsafe_allow_html=True)
            st.subheader(f"{icon} Not enough data yet — that's the honest answer")
            st.write(
                "There isn't a large enough peer group to show a percentile or salary "
                "range here. Showing a number anyway would be misleading, so nothing is "
                "shown instead. Try a broader city (or none), double-check the job title, "
                "or try a nearby experience level."
            )
        else:
            pct = result.user_percentile
            b = result.bands
            st.markdown('<div class="hero-eyebrow">Your result</div>', unsafe_allow_html=True)
            st.markdown(
                f'<p class="hero-percentile">{pct:.0f}<small>th percentile</small></p>',
                unsafe_allow_html=True,
            )
            st.markdown(
                f'<p class="hero-salary">at <strong>{format_inr(salary_in_usd)}</strong> / year, '
                f'{job_title} · {EXPERIENCE_LABELS[experience_level]}'
                + (f' · {city}' if city else '') + '</p>',
                unsafe_allow_html=True,
            )
            st.progress(min(max(pct / 100.0, 0.0), 1.0))

            st.markdown('<div class="section-label">Market range (annual, ₹ INR)</div>', unsafe_allow_html=True)
            band_cols = st.columns(5)
            for col, (name, val) in zip(
                band_cols,
                [("P10", b.p10), ("P25", b.p25), ("Median", b.p50), ("P75", b.p75), ("P90", b.p90)],
            ):
                col.metric(name, format_inr_short(val), help=format_inr(val))

            for w in result.warnings:
                st.warning(w)

        icon, label, blurb = CONFIDENCE_INFO[result.confidence]
        st.markdown('<div class="section-label">Confidence</div>', unsafe_allow_html=True)
        st.write(f"{icon} **{label}** — {blurb}")

        with st.expander("Why this benchmark? (peer group, sample size, sources)", expanded=(result.bands is None)):
            st.write(result.cohort.description or "No comparable observations were found.")
            prov = result.provenance
            st.write(
                f"**{prov['n']}** comparable observation(s), "
                f"from **{prov['year_range']}**, across: "
                + (", ".join(f"{k} ({v})" for k, v in prov['sources'].items()) or "no sources")
                + "."
            )
            st.caption(
                "The engine always starts with the tightest possible peer group — same "
                "title, experience, currency, and city — and only broadens the comparison, "
                "one step at a time, when there isn't enough data. This is exactly which "
                "step it landed on for this query."
            )

with st.sidebar:
    st.header("About")
    st.write(
        "This tool compares an anonymous salary against **11,300+ real, "
        "de-duplicated India tech-industry salary records** from three "
        "sources (Glassdoor India, LeetCode Compensations, and a global "
        "self-report survey filtered to India), using a transparent "
        "fallback ladder: it starts with the tightest possible peer group "
        "(same title, experience, currency, city) and only broadens the "
        "comparison — and says so — when there isn't enough data."
    )
    st.write(
        "**The row count overstates coverage for some roles.** 83% of "
        "rows are a 2022 snapshot with no experience-level data. Product "
        "and program management roles in particular are still thin — "
        "you'll likely see `Insufficient` for those, honestly, rather "
        "than a number. The sample size (`n=`) shown after every query "
        "is the real number backing that specific result, not the size "
        "of the whole dataset."
    )
    st.write(
        "**No career-improvement suggestions.** This tool only reports "
        "where you currently stand, honestly, with a visible confidence "
        "tier — nothing is fabricated to fill a data gap."
    )
    st.header("Confidence tiers")
    for tier in (HIGH, MODERATE, LOW, INSUFFICIENT):
        icon, label, blurb = CONFIDENCE_INFO[tier]
        st.write(f"{icon} **{label}** — {blurb}")
    st.divider()
    st.caption(
        f"Dataset: {load_report.rows_loaded:,} rows loaded "
        f"({load_report.summary()})."
    )
    st.caption("Nothing you enter here is stored or sent anywhere — it only lives in this browser session.")
