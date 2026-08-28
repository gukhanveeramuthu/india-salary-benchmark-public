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
from confidence_tiers import INSUFFICIENT, LOW, MODERATE, HIGH
from data_loader import load_dataset
from taxonomy import ROLE_FAMILIES, role_family

# FRED H.10 / AEXINUS annual-average USD/INR rate, most recent period in
# the dataset (see data/README.md for the full cited table by year).
USD_INR_RATE = 87.15

# --- ledger design tokens (kept in sync with the CSS block below) ---
INK = "#1C2536"
PAPER = "#EFF1EC"
CARD = "#FFFFFF"
MARIGOLD = "#E8A33D"
SLATE = "#5B6472"
MOSS = "#5C7A5C"
RUST = "#B0503C"
RULE = "#D9DCD3"

CONFIDENCE_INFO = {
    HIGH: (MOSS, "High", "50+ comparable observations."),
    MODERATE: (MARIGOLD, "Moderate", "20–49 comparable observations."),
    LOW: (RUST, "Low", "10–19 comparable observations — treat with caution."),
    INSUFFICIENT: (INK, "Insufficient", "Fewer than 10 observations — no number is shown."),
}

st.set_page_config(page_title="India Salary Benchmark", page_icon="📏", layout="centered")


@st.cache_data(show_spinner="Loading dataset…")
def load_data():
    return load_dataset()


@st.cache_data(show_spinner=False)
def _deduped_titles(_observations):
    """Case-insensitive-deduped title counts, shared by both the flat and
    category-grouped pickers below. Case variants of the same title (e.g.
    'SDE' vs 'Sde') are merged so they don't fragment one role's real
    frequency or show up as visual duplicates."""
    variants: dict[str, Counter] = {}
    for o in _observations:
        raw = o.job_title_raw.strip()
        if not raw:
            continue
        variants.setdefault(raw.lower(), Counter())[raw] += 1

    merged_counts = {key: sum(c.values()) for key, c in variants.items()}
    display_form = {
        key: max(c.items(), key=lambda kv: (kv[1], kv[0]))[0]
        for key, c in variants.items()
    }
    ranked = sorted(merged_counts, key=lambda k: -merged_counts[k])
    return merged_counts, display_form, ranked


@st.cache_data(show_spinner=False)
def title_options(_observations):
    """Flat, frequency-ranked title list ('Search all titles' mode) - the
    top 300 by frequency, plus every taxonomy-recognized title regardless
    of frequency (being rare is exactly when someone most needs to find a
    role here rather than type it manually)."""
    merged_counts, display_form, ranked = _deduped_titles(_observations)
    top_keys = ranked[:300]

    known_titles = {t for titles in ROLE_FAMILIES.values() for t in titles}
    extra_known = [k for k in ranked if k in known_titles and k not in top_keys]

    return [display_form[k] for k in top_keys + extra_known]


@st.cache_data(show_spinner=False)
def family_options(_observations):
    """Groups every observed title the taxonomy recognizes by its role
    family, e.g. all 20 'Software Engineering' variants (SDE, SDE 1/2,
    Software Development Engineer, Backend Developer, ...) together,
    instead of scattered across one 325-entry flat list. Returns
    (family_names_sorted_by_size, {family_name: [titles sorted by freq]})."""
    merged_counts, display_form, ranked = _deduped_titles(_observations)

    grouped: dict[str, list[str]] = {}
    for key in ranked:
        fam = role_family(display_form[key])
        if fam:
            grouped.setdefault(fam, []).append(display_form[key])

    family_totals = {
        fam: sum(merged_counts[t.lower()] for t in titles)
        for fam, titles in grouped.items()
    }
    family_names = sorted(grouped, key=lambda f: -family_totals[f])
    return family_names, grouped, family_totals


@st.cache_data(show_spinner=False)
def city_options(_observations):
    return sorted({o.city for o in _observations if o.city})


@st.cache_data(show_spinner=False)
def experience_breakdown(_observations, job_title):
    """How many IN-based observations exist per experience level for this
    title (or its role family, if recognized) — the same pool the cohort
    engine draws from before applying currency/city. Shown next to the
    Experience picker so a thin cohort at your specific level is visible
    *before* you submit, not just as an "Insufficient" result after."""
    title_norm = job_title.strip().lower()
    family = role_family(job_title)
    if family is not None:
        pool = [o for o in _observations if role_family(o.job_title_raw) == family and o.employee_residence == "IN"]
    else:
        pool = [o for o in _observations if o.job_title_raw.strip().lower() == title_norm and o.employee_residence == "IN"]
    counts = Counter(o.experience_level for o in pool)
    return counts, len(pool), family


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


def render_ruler(p10, p25, p50, p75, p90, user_pct, fmt_short):
    """A literal measuring ruler: percentile 0-100 on the x-axis, minor
    ticks every 5%, major ticks at the five reported bands (each labelled
    with its rupee value), and the user's own position pinned with a
    flag. This replaces a generic progress bar with something that
    actually shows where the peer group's money sits, not just where the
    user is relative to an abstract 0-100 bar."""
    x0, x1, axis_y = 50, 950, 118
    span = x1 - x0

    def xpos(p):
        return x0 + (p / 100.0) * span

    minor_ticks = "".join(
        f'<line x1="{xpos(p):.1f}" y1="{axis_y - 5}" x2="{xpos(p):.1f}" y2="{axis_y + 5}" '
        f'stroke="{SLATE}" stroke-width="1" opacity="0.35"/>'
        for p in range(0, 101, 5)
    )

    majors = [(10, "P10", p10), (25, "P25", p25), (50, "MEDIAN", p50), (75, "P75", p75), (90, "P90", p90)]
    major_ticks = ""
    for p, name, val in majors:
        x = xpos(p)
        major_ticks += (
            f'<line x1="{x:.1f}" y1="{axis_y - 16}" x2="{x:.1f}" y2="{axis_y + 16}" '
            f'stroke="{INK}" stroke-width="2"/>'
            f'<text x="{x:.1f}" y="{axis_y - 26}" text-anchor="middle" '
            f'font-family="IBM Plex Mono, monospace" font-size="13" font-weight="600" '
            f'fill="{SLATE}" letter-spacing="0.04em">{name}</text>'
            f'<text x="{x:.1f}" y="{axis_y + 40}" text-anchor="middle" '
            f'font-family="IBM Plex Mono, monospace" font-size="15" font-weight="700" '
            f'fill="{INK}">{fmt_short(val)}</text>'
        )

    clamped_pct = min(max(user_pct, 0.0), 100.0)
    ux = xpos(clamped_pct)
    badge_x = min(max(ux, x0 + 55), x1 - 55)
    badge_label = f"{user_pct:.0f}th"

    svg = f"""
    <svg viewBox="0 0 1000 190" xmlns="http://www.w3.org/2000/svg" style="width:100%;height:auto;overflow:visible;">
        <line x1="{x0}" y1="{axis_y}" x2="{x1}" y2="{axis_y}" stroke="{INK}" stroke-width="2.5"/>
        {minor_ticks}
        {major_ticks}
        <line x1="{ux:.1f}" y1="{axis_y - 55}" x2="{ux:.1f}" y2="{axis_y}" stroke="{MARIGOLD}" stroke-width="2.5"/>
        <circle cx="{ux:.1f}" cy="{axis_y}" r="7" fill="{MARIGOLD}" stroke="{INK}" stroke-width="2"/>
        <rect x="{badge_x - 42:.1f}" y="{axis_y - 84}" width="84" height="30" rx="2"
              fill="{MARIGOLD}" stroke="{INK}" stroke-width="1.5"/>
        <text x="{badge_x:.1f}" y="{axis_y - 63}" text-anchor="middle"
              font-family="IBM Plex Mono, monospace" font-size="15" font-weight="700"
              fill="{INK}">{badge_label} pctl</text>
    </svg>
    """
    return svg


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

# --- ledger design system: fonts, palette, widget reskin ---
st.markdown(
    f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Zilla+Slab:wght@500;600;700&family=IBM+Plex+Mono:wght@400;500;600;700&family=Inter:wght@400;500;600&display=swap');

    html, body, [class*="css"] {{
        font-family: 'Inter', sans-serif;
    }}

    [data-testid="stAppViewContainer"], [data-testid="stApp"] {{
        background-color: {PAPER};
        background-image:
            linear-gradient(90deg, rgba(28,37,54,0.035) 1px, transparent 1px),
            linear-gradient(rgba(28,37,54,0.035) 1px, transparent 1px);
        background-size: 28px 28px;
    }}

    [data-testid="stHeader"] {{ background-color: transparent; }}

    [data-testid="stMainBlockContainer"] {{
        padding-top: 2.6rem;
        max-width: 760px;
    }}

    h1, h2, h3 {{
        font-family: 'Zilla Slab', serif !important;
        color: {INK} !important;
    }}

    /* -- hero -- */
    .ledger-eyebrow {{
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
        font-family: 'IBM Plex Mono', monospace !important;
        font-size: 0.74rem !important;
        font-weight: 600 !important;
        letter-spacing: 0.14em !important;
        text-transform: uppercase !important;
        color: {SLATE} !important;
        margin-bottom: 0.6rem !important;
    }}
    .ledger-eyebrow::before {{
        content: "";
        display: inline-block;
        width: 9px;
        height: 9px;
        background: {MARIGOLD};
        border: 1.5px solid {INK};
    }}
    .hero-title {{
        font-family: 'Zilla Slab', serif !important;
        font-size: clamp(2.1rem, 5vw, 2.85rem) !important;
        font-weight: 700 !important;
        line-height: 1.08 !important;
        color: {INK} !important;
        margin: 0 0 0.6rem 0 !important;
    }}
    .hero-sub {{
        font-size: 1.02rem !important;
        color: {SLATE} !important;
        max-width: 46ch;
        line-height: 1.5 !important;
        margin-bottom: 0.55rem !important;
    }}
    .stat-strip {{
        font-family: 'IBM Plex Mono', monospace !important;
        font-size: 0.82rem !important;
        color: {INK} !important;
        border-top: 1px solid {RULE};
        border-bottom: 1px solid {RULE};
        padding: 0.5rem 0 !important;
        margin: 0.9rem 0 1.6rem 0 !important;
    }}
    .stat-strip b {{ color: {MARIGOLD}; }}

    /* -- ledger section tabs -- */
    .ledger-tab {{
        display: flex;
        align-items: baseline;
        gap: 0.6rem;
        margin: 1.7rem 0 0.7rem 0 !important;
    }}
    .ledger-tab .idx {{
        font-family: 'IBM Plex Mono', monospace !important;
        font-size: 0.72rem !important;
        font-weight: 700 !important;
        color: {PAPER} !important;
        background: {INK};
        padding: 0.12rem 0.4rem;
    }}
    .ledger-tab .label {{
        font-family: 'IBM Plex Mono', monospace !important;
        font-size: 0.78rem !important;
        font-weight: 600 !important;
        letter-spacing: 0.08em !important;
        text-transform: uppercase !important;
        color: {INK} !important;
    }}
    .ledger-tab .rule {{
        flex: 1;
        height: 1px;
        background: {RULE};
        margin-top: 0.15rem;
    }}

    /* -- intake card -- */
    [data-testid="stForm"] {{
        background: {CARD};
        border: 1.5px solid {INK};
        border-radius: 3px;
        padding: 1.6rem 1.6rem 1.3rem 1.6rem !important;
        box-shadow: 4px 4px 0px 0px rgba(28,37,54,0.08);
    }}

    /* -- inputs -- */
    div[data-baseweb="select"] > div,
    [data-testid="stTextInputRootElement"],
    [data-testid="stNumberInputContainer"] {{
        background-color: {CARD} !important;
        border: 1.5px solid {INK} !important;
        border-radius: 2px !important;
        box-shadow: none !important;
    }}
    [data-testid="stWidgetLabel"] p {{
        font-family: 'IBM Plex Mono', monospace !important;
        font-size: 0.78rem !important;
        color: {SLATE} !important;
        font-weight: 500 !important;
    }}
    [data-testid="stTextInputField"], [data-testid="stNumberInputField"] {{
        font-family: 'IBM Plex Mono', monospace !important;
        color: {INK} !important;
    }}

    /* -- CTA button -- */
    [data-testid="stFormSubmitButton"] button, [data-testid="stBaseButton-primary"] {{
        background-color: {INK} !important;
        color: {PAPER} !important;
        border: 1.5px solid {INK} !important;
        border-radius: 2px !important;
        font-family: 'IBM Plex Mono', monospace !important;
        font-weight: 600 !important;
        letter-spacing: 0.08em !important;
        text-transform: uppercase !important;
        font-size: 0.85rem !important;
        padding: 0.65rem 1rem !important;
        transition: background-color 0.15s ease, color 0.15s ease;
    }}
    [data-testid="stFormSubmitButton"] button:hover {{
        background-color: {MARIGOLD} !important;
        color: {INK} !important;
        border-color: {INK} !important;
    }}

    /* -- expander -- */
    [data-testid="stExpander"] {{
        border: 1.5px solid {INK} !important;
        border-radius: 2px !important;
        background: {CARD} !important;
    }}

    /* -- sidebar -- */
    [data-testid="stSidebar"] {{
        background-color: {CARD} !important;
        border-right: 1.5px solid {INK};
    }}
    [data-testid="stSidebar"] h2 {{
        font-family: 'IBM Plex Mono', monospace !important;
        font-size: 0.8rem !important;
        letter-spacing: 0.1em !important;
        text-transform: uppercase !important;
        color: {SLATE} !important;
        border-bottom: 1px solid {RULE};
        padding-bottom: 0.4rem;
    }}
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown('<div class="ledger-eyebrow">India Career Benchmark</div>', unsafe_allow_html=True)
st.markdown('<div class="hero-title">See where you really stand</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="hero-sub">Enter your role, experience, city and salary. Get a real peer '
    'comparison — with an honest confidence rating, never a fabricated number.</div>',
    unsafe_allow_html=True,
)
n_sources = len({o.source_dataset for o in observations})
st.markdown(
    f'<div class="stat-strip"><b>{load_report.rows_loaded:,}</b> real observations &nbsp;·&nbsp; '
    f'<b>{n_sources}</b> public sources &nbsp;·&nbsp; transparent methodology</div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="ledger-tab"><span class="idx">01</span>'
    '<span class="label">Your role</span><span class="rule"></span></div>',
    unsafe_allow_html=True,
)
family_names, grouped_titles, family_totals = family_options(observations)
category_options = ["Search all titles"] + family_names

def _format_category(c):
    if c == "Search all titles":
        return c
    return f"{c} ({family_totals[c]:,} people)"

role_col1, role_col2 = st.columns(2)
with role_col1:
    category = st.selectbox(
        "Narrow by category (optional)",
        category_options,
        format_func=_format_category,
        help="Many similar titles - e.g. SDE, SDE 1/2, Software Development "
             "Engineer, Backend Developer - are really the same role family. "
             "Pick a category to see just that family's titles instead of "
             "all 300+ at once. The count shown is across ALL experience "
             "levels combined — your specific level will usually have fewer.",
    )
with role_col2:
    if category == "Search all titles":
        title_list = title_options(observations)
    else:
        title_list = grouped_titles[category]
    title_choice = st.selectbox("Your title", ["Type my own…"] + title_list)

if title_choice == "Type my own…":
    job_title = st.text_input("Enter your job title", "")
else:
    job_title = title_choice

EXP_ORDER = ["EN", "MI", "SE"]  # Executive dropped from display — not a band this tool's audience falls into

if job_title.strip():
    exp_counts, total_n, matched_family = experience_breakdown(observations, job_title)
    if total_n > 0:
        chips = "".join(
            f'<span style="margin-right:1.1rem;">'
            f'<b style="color:{INK};">{EXPERIENCE_LABELS[lvl]}</b>'
            f' <span style="color:{MOSS if exp_counts.get(lvl,0) >= 10 else (MARIGOLD if exp_counts.get(lvl,0) >= 3 else RUST)};">'
            f'{exp_counts.get(lvl, 0)}</span></span>'
            for lvl in EXP_ORDER
        )
        chips += (
            f'<span style="margin-right:1.1rem;">'
            f'<b style="color:{INK};">Any (pooled)</b>'
            f' <span style="color:{MOSS if total_n >= 10 else (MARIGOLD if total_n >= 3 else RUST)};">{total_n}</span></span>'
        )
        family_note = f' (grouped under "{matched_family}")' if matched_family else ""
        st.markdown(
            f'''
            <div style="font-family:'IBM Plex Mono',monospace; font-size:0.8rem; color:{SLATE};
                        border-left:2.5px solid {MARIGOLD}; padding:0.4rem 0 0.4rem 0.7rem; margin:0.7rem 0 1.1rem 0;">
                Comparable observations by experience{family_note}: {chips}
                <span style="color:{SLATE};">— pick a level with 10+ for a confident number, or "Any / not sure" to pool every level.</span>
            </div>
            ''',
            unsafe_allow_html=True,
        )

with st.form("benchmark_form"):
    st.markdown(
        '<div class="ledger-tab" style="margin-top:0 !important;"><span class="idx">02</span>'
        '<span class="label">Experience &amp; city</span><span class="rule"></span></div>',
        unsafe_allow_html=True,
    )
    col1, col2 = st.columns(2)

    with col1:
        EXP_UI_OPTIONS = ["EN", "MI", "SE", "ANY"]

        def _format_exp(k):
            return "Any / not sure" if k == "ANY" else EXPERIENCE_LABELS[k]

        experience_choice = st.selectbox(
            "Experience",
            options=EXP_UI_OPTIONS,
            format_func=_format_exp,
            help="Pick 'Any / not sure' to compare against everyone at this "
                 "title regardless of self-reported experience band — useful "
                 "when a specific band is too thin on its own.",
        )
        experience_level = None if experience_choice == "ANY" else experience_choice

    with col2:
        city_list = city_options(observations)
        city_choice = st.selectbox("City (optional)", ["All of India"] + city_list)
        city = None if city_choice == "All of India" else city_choice

    st.markdown(
        '<div class="ledger-tab"><span class="idx">03</span>'
        '<span class="label">Your salary</span><span class="rule"></span></div>',
        unsafe_allow_html=True,
    )
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

        st.markdown(
            '<div class="ledger-tab"><span class="idx">→</span>'
            '<span class="label">Your result</span><span class="rule"></span></div>',
            unsafe_allow_html=True,
        )

        if result.bands is None:
            tier_color, label, _ = CONFIDENCE_INFO[result.confidence]
            st.markdown(
                f'''
                <div style="border:1.5px dashed {INK}; border-radius:3px; padding:1.4rem 1.5rem;
                            background:{CARD};">
                    <div style="font-family:'IBM Plex Mono',monospace; font-size:0.78rem;
                                font-weight:700; letter-spacing:0.08em; text-transform:uppercase;
                                color:{RUST}; margin-bottom:0.5rem;">Not enough data — the honest answer</div>
                    <div style="color:{INK}; line-height:1.55;">
                        There isn't a large enough peer group to show a percentile or salary range
                        here. Showing a number anyway would be misleading, so nothing is shown
                        instead. Try a broader city (or none), double-check the job title, or try
                        a nearby experience level.
                    </div>
                </div>
                ''',
                unsafe_allow_html=True,
            )
        else:
            pct = result.user_percentile
            b = result.bands
            exp_display = EXPERIENCE_LABELS[experience_level] if experience_level else "Any experience level"
            st.markdown(
                f'''
                <div style="border:1.5px solid {INK}; border-radius:3px; padding:1.5rem 1.6rem 1.1rem 1.6rem;
                            background:{CARD}; box-shadow:4px 4px 0px 0px rgba(28,37,54,0.08);">
                    <div style="font-family:'IBM Plex Mono',monospace; font-size:0.82rem; color:{SLATE};">
                        {job_title} · {exp_display}{f' · {city}' if city else ''}
                        &nbsp;at&nbsp;<b style="color:{INK};">{format_inr(salary_in_usd)}</b>/yr
                    </div>
                </div>
                ''',
                unsafe_allow_html=True,
            )
            st.markdown(
                f'<div style="overflow-x:auto; padding-bottom:0.3rem;">'
                f'<div style="min-width:640px;">{render_ruler(b.p10, b.p25, b.p50, b.p75, b.p90, pct, format_inr_short)}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

            for w in result.warnings:
                st.warning(w)

        tier_color, label, blurb = CONFIDENCE_INFO[result.confidence]
        st.markdown(
            '<div class="ledger-tab"><span class="idx">→</span>'
            '<span class="label">Confidence</span><span class="rule"></span></div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'''
            <div style="display:flex; align-items:center; gap:0.55rem; font-size:0.98rem; color:{INK};">
                <span style="width:11px; height:11px; background:{tier_color}; border:1.5px solid {INK};
                             display:inline-block; flex-shrink:0;"></span>
                <span><b>{label}</b> — {blurb}</span>
            </div>
            ''',
            unsafe_allow_html=True,
        )

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
        tier_color, label, blurb = CONFIDENCE_INFO[tier]
        st.markdown(
            f'''
            <div style="display:flex; align-items:flex-start; gap:0.5rem; margin-bottom:0.6rem; font-size:0.92rem; color:{INK};">
                <span style="width:10px; height:10px; margin-top:0.3rem; background:{tier_color};
                             border:1.5px solid {INK}; display:inline-block; flex-shrink:0;"></span>
                <span><b>{label}</b> — {blurb}</span>
            </div>
            ''',
            unsafe_allow_html=True,
        )
    st.divider()
    st.caption(
        f"Dataset: {load_report.rows_loaded:,} rows loaded "
        f"({load_report.summary()})."
    )
    st.caption("Nothing you enter here is stored or sent anywhere — it only lives in this browser session.")
