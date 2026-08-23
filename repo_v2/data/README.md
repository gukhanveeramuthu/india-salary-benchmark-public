# data/india_salaries_deduped.csv

11,348 rows (loaded, deduplicated), real, non-synthetic. Every value is either
taken directly from a source record or derived by a stated, documented rule
(currency conversion, years-of-experience bucketing, city-name normalization)
— nothing was invented to fill a gap. Where a source simply didn't capture a
field, that field is marked `UNK` (or `-1` for `remote_ratio`, or blank for
`city`) rather than guessed.

**Composition matters more than the total row count.** 9,410 of these rows
(83%) are the 2022 Glassdoor snapshot, which never captured years-of-experience
— so a headline "11,000+ salary records" is misleading on its own. See the
per-source breakdown below before treating any cohort as more solid than it is.

## Sources combined

| source_dataset | rows (loaded, post-dedup) | what it is |
|---|---|---|
| `glassdoor_india_2022` | 9,410 | Employee-submitted salary reports for IT/software roles, scraped from Glassdoor India, published as "Software Professional Salaries – 2022" on Kaggle (kaggle.com/datasets/iamsouravbanerjee/software-professional-salaries-2022) |
| `leetcode_compensations_india` | 1,709 | Self-reported compensation posts from LeetCode's "Compensations" forum (overwhelmingly India-based, INR/LPA), parsed by `utkarshdeepak/LeetComp` (through Jan 2023) and `Thesohan/leetcode-compensation` (through Jan 2026) |
| `ai_jobs_net_survey` | 229 | India-resident (`employee_residence == IN`) rows from `foorilla/ai-jobs-net-salaries` — a weekly-updated, CC0-licensed self-report survey at aijobs.net/salaries, filtered to India and added specifically to bring in real experience-level coverage, currency variety, and years 2020–2025 (see "Why this source" below) |

## Why the third source was added

The first two sources have two structural gaps, both confirmed directly
against the loaded data, not assumed:

1. **Experience-level coverage.** All 9,410 Glassdoor rows are
   `experience_level = UNK` — that source's form never captured it. Only the
   1,709 LeetCode rows have a real self-reported experience bucket. So any
   cohort filtered by experience level was, before this pass, drawing only
   from a much smaller effective pool than the total row count suggested.
2. **Role coverage gaps, "Product Manager" being the sharpest example.**
   Neither original source contains a single row with the exact title
   "Product Manager" — the closest match in 11,119 rows was one row titled
   "Senior Mobile Product Manager," which doesn't match the taxonomy's exact
   title strings either, so even the role-family fallback came up empty.
   Both are consequences of the sourcing (Glassdoor-India-2022 skews
   engineering-heavy; LeetCode's "Compensations" forum is an interview-prep
   community, essentially engineering-only by construction) rather than a
   preventable data-cleaning issue.

`foorilla/ai-jobs-net-salaries` was added because it's real (self-reported,
same honesty standard as the other two), CC0-licensed (safe to redistribute),
already uses this project's exact target schema (it's the same ai-jobs.net
schema this engine's `SalaryObservation` fields were originally modeled on),
and — filtered to India residents — contributes:
- **4 real "Product Manager" rows** (after dedup; 2 SE, 2 MI). This does
  **not** solve the PM coverage gap — 4 is still below the `Insufficient`
  threshold (10), so a "Product Manager" query correctly still returns no
  percentile. What it does do is turn a hard "zero rows, taxonomy fallback
  also fails" case into an honest "not enough data yet" case, which is a
  real (if modest) improvement, not a fabricated one.
- **Real experience levels across the board**: of 229 loaded rows, 39 EN /
  74 MI / 114 SE / 2 EX — a meaningfully larger pool of experience-tagged
  India observations than LeetCode alone provided.
- **A real currency mix** (135 INR / 91 USD / 3 EUR among these 229 rows),
  which is the first time the `mixed_currency_warning` path fires on
  genuine data rather than only in the synthetic test suite.
- **Fresher years**: 104 of these 229 rows are from 2025 (full breakdown:
  2020×1, 2021×19, 2022×20, 2023×30, 2024×55, 2025×104), partially offsetting
  how Glassdoor-heavy cohorts still skew toward the 2022 snapshot.
- No `city` field — this source doesn't capture city, so all 229 rows load
  with `city=None`, honestly excluded from the city-specific fallback rung
  rather than guessed.

This is additive only: nothing from the original two sources was removed,
re-labeled, or reinterpreted to make this addition look bigger than it is.

*(Row count is higher than the 7,607 in an earlier pass: adding `city` as
a genuine data field means two otherwise-identical rows in different cities
are no longer incorrectly collapsed into one during dedup — the identity
rule now correctly treats them as distinct observations.)*

## Field-by-field notes


- **work_year**: Glassdoor rows all use 2022 (the dataset's publication year — the source didn't provide a per-row date). LeetCode rows use the actual year of the forum post.
- **experience_level**: `EN`/`MI`/`SE`/`EX`, or `UNK`.
  - Glassdoor's source form never captured years of experience, so all 6,092 of those rows are `UNK`. This is not a guess — it's an honest "not reported."
  - LeetCode posts include a real, self-reported years-of-experience number, bucketed as: `EN` <2y, `MI` 2–5y, `SE` 5–10y, `EX` 10y+.
- **employment_type**: `FT`/`CT`/`IN`(intern)/`TR`(trainee) from Glassdoor's real `Employment Status` field; `UNK` for LeetCode (not captured by that source).
- **salary / salary_currency**: the real reported INR figure, currency always `INR` (both sources are India-specific and report in INR/LPA).
- **salary_in_usd**: derived by dividing the INR figure by the published annual-average USD/INR exchange rate for that row's `work_year`, sourced from the Federal Reserve's H.10/FRED series (AEXINUS): 2021 ₹73.94, 2022 ₹78.58, 2023 ₹82.57, 2024 ₹83.66, 2025–26 ₹87.15. This is the one derived (not directly reported) numeric field in the dataset — flagged here rather than hidden, per the original engine's stated principle of not introducing an *unaudited* exchange-rate assumption. This one is audited/cited.
- **employee_residence / company_location**: `IN` for all rows — both sources are explicitly India-focused surveys.
- **remote_ratio**: `-1` sentinel for "not captured" — neither source records remote/hybrid/onsite status per row. Not used by the cohort-matching logic, only carried as metadata.
- **company_size**: `UNK` for all rows — neither source captures this.
- **city**: normalized city name (e.g. "Bangalore"/"bengaluru" both become
  `Bengaluru`; "Gurgaon" becomes `Gurugram`), derived from each source's raw
  `location` field. Blank/unparseable locations become an empty value
  (loaded as `None`), never guessed. Two Glassdoor rows report a state
  ("Madhya Pradesh", "Kerala") instead of a city in the raw source data —
  kept verbatim rather than mapped to an invented city. This field is now
  wired into `cohort_engine.py`'s fallback ladder as an optional top rung —
  see the main `README.md`.
- **source_dataset**: as in the table above.

## What this dataset does NOT have (yet)
- **Industry / sector.**
- **A "nearby city" grouping** — e.g. Gurugram/Noida are both NCR but are
  currently treated as fully distinct cities with no intermediate fallback
  between "exact city" and "all of India."
- **Enough Product/Program/Design-management coverage to be useful.** The
  third source (below) adds a handful of real rows, but Product Management
  in particular is still thin enough that most queries against it will
  honestly return "Insufficient" rather than a number. This is a data
  gap, not a taxonomy or engine gap — see "Why the third source was added."

## Reproducing this file
Built by combining, cleaning, and deduplicating
`india_it_salaries_glassdoor.csv` and `india_it_salaries_leetcode_yoe.csv`
(the two source files pulled earlier), then applying `schema.py`'s exact
identity rule (all fields except `source_dataset`) to drop duplicates —
which is why this file loads with `duplicates_removed=0` for that pass:
it's already deduplicated at the file level, and the loader's own dedup
pass just confirms it.

The third source (`ai_jobs_net_survey`) was added in a later pass by
pulling `salaries.csv` directly from the `foorilla/ai-jobs-net-salaries`
GitHub repo (CC0-licensed, updated weekly), filtering to
`employee_residence == IN`, adding a blank `city` column (this source
doesn't capture city) and `source_dataset = ai_jobs_net_survey`, and
appending — unchanged otherwise — to the existing file. The loader's
identity-based dedup (all fields except `source_dataset`) then naturally
drops any rows that happen to collide with existing ones; `duplicates_removed`
in a fresh `load_observations()` call reflects this. To refresh this source
with a newer snapshot: re-clone `foorilla/ai-jobs-net-salaries`, re-run the
same filter/transform, and re-append — do not hand-edit rows into this file.
