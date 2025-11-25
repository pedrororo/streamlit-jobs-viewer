import streamlit as st
import pandas as pd
from pathlib import Path

# --------- Config ---------
DATA_PATH = Path("data/jobs_latest.csv")  # rename your file to this or adjust path
MAX_ROWS = 6000  # hard cap for displayed jobs

st.set_page_config(
    page_title="Remote/Hybrid Jobs Viewer",
    layout="wide",
)

# --- Hide only the footer (keep header so sidebar toggle works) ---
st.markdown(
    """
    <style>
    footer {visibility: hidden !important;}

    /* Hide the entire toolbar (eye, download, search, fullscreen) */
    [data-testid="stElementToolbar"] {
        display: none !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# --------- Timezone info (expanded/human-friendly) ---------
TIMEZONE_DETAILS = {
    "PST": "Pacific Standard Time (UTC-8) — e.g., California, Washington",
    "PDT": "Pacific Daylight Time (UTC-7, summer)",
    "PT":  "Pacific Time (PST/PDT)",
    "MST": "Mountain Standard Time (UTC-7) — e.g., Colorado, Arizona (winter)",
    "MDT": "Mountain Daylight Time (UTC-6, summer)",
    "MT":  "Mountain Time (MST/MDT)",
    "CST": "Central Standard Time (UTC-6) — e.g., Texas, Illinois",
    "CDT": "Central Daylight Time (UTC-5, summer)",
    "CT":  "Central Time (CST/CDT)",
    "EST": "Eastern Standard Time (UTC-5) — e.g., New York, Boston, Miami",
    "EDT": "Eastern Daylight Time (UTC-4, summer)",
    "ET":  "Eastern Time (EST/EDT)",

    "GMT": "Greenwich Mean Time (UTC+0)",
    "BST": "British Summer Time (UTC+1) — UK summer",

    "CET": "Central European Time (UTC+1) — e.g., Germany, France",
    "CEST": "Central European Summer Time (UTC+2)",

    "EET": "Eastern European Time (UTC+2)",
    "EEST": "Eastern European Summer Time (UTC+3)",

    "IST": "India Standard Time (UTC+5:30)",
    "WAT": "West Africa Time (UTC+1)",
    "EAT": "East Africa Time (UTC+3)",

    "JST": "Japan Standard Time (UTC+9)",
    "AEST": "Australian Eastern Standard Time (UTC+10)",
    "AEDT": "Australian Eastern Daylight Time (UTC+11)",
}

REMOTE_LABELS = {
    "hybrid": "Hybrid",
    "on_site": "On-site",
    "remote_first": "Remote-first",
    "remote_only": "Remote-only",
    "unspecified": "Unspecified",
}

SENIORITY_LABELS = {
    "intern": "Intern",
    "junior": "Junior",
    "mid": "Mid-level",
    "senior": "Senior",
    "staff": "Staff",
    "principal": "Principal",
    "lead": "Lead",
    "manager": "Manager",
    "director": "Director",
    "vp": "VP",
    "c_level": "C-level",
}

# --------- Data loader ---------
@st.cache_data
def load_jobs(path: Path, file_mtime: float) -> pd.DataFrame:
    # Your CSV uses ';' as delimiter
    df = pd.read_csv(path, sep=";")

    # Coerce salary columns to numeric (still useful for later, but not shown)
    for col in ["salary_min", "salary_max", "salary_annual_min", "salary_annual_max"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Try to parse posted_at as datetime for sorting + create nice date string
    if "posted_at" in df.columns:
        df["posted_at_dt"] = pd.to_datetime(df["posted_at"], errors="coerce", utc=True)
        df = df.sort_values("posted_at_dt", ascending=False)
        df["posted_date"] = df["posted_at_dt"].dt.strftime("%Y-%m-%d")
    else:
        df["posted_date"] = ""

    # Ensure some optional columns exist so filters don't crash
    for col in [
        "seniority_norm",
        "location",
        "remote_policy",
        "timezone_overlap",
        "job_type",
        "tech_stack.languages",
        "tech_stack.frameworks",
        "tech_stack.data",
        "tech_stack.cloud",
        "tech_stack.ml",
    ]:
        if col not in df.columns:
            df[col] = ""

    return df

# --------- Load data ---------
if not DATA_PATH.exists():
    st.error(
        f"CSV not found at: {DATA_PATH}\n\n"
        "Put a file like jobs_refined_YYYY-MM-DD_HH-MM-SS.csv "
        "there and/or rename it to jobs_latest.csv."
    )
    st.stop()

file_mtime = DATA_PATH.stat().st_mtime  # changes whenever the CSV is updated
df = load_jobs(DATA_PATH, file_mtime)

# --------- Header ---------
st.title("🌐 Remote/Hybrid Jobs Viewer")
st.caption(
    "Daily curated remote jobs by "
    "[Pedro Arroyo](https://www.linkedin.com/in/pedro-andre-arroyo-silva/)"
)
st.caption("📅 Dates shown as **YYYY-MM-DD**.")

# st.write(
#     f"Total jobs in this snapshot: **{MAX_ROWS}** "
# )

# --------- Prepare filter option lists (shared) ---------
seniority_options = sorted(
    s
    for s in df["seniority_norm"].dropna().unique()
    if str(s).strip() and str(s).lower() != "unspecified"
)

job_type_options = sorted(
    s for s in df["job_type"].dropna().unique() if str(s).strip()
)

remote_options = sorted(
    s for s in df["remote_policy"].dropna().unique() if str(s).strip()
)

company_options = sorted(
    s for s in df["company"].dropna().unique() if str(s).strip()
)

tz_options = sorted(
    s for s in df["timezone_overlap"].dropna().unique() if str(s).strip()
)
tz_options_human = [
    f"{tz} — {TIMEZONE_DETAILS.get(tz, 'Unknown timezone')}"
    for tz in tz_options
]

# --------- Layout selector (PC vs Mobile) ---------
layout_mode = st.radio(
    "Layout mode",
    ("🖥️ Desktop (sidebar filters)", "📱 Mobile (top filters)"),
    horizontal=True,
)

# Initialize filter variables
q = ""
location_q = ""
tech_q = ""
selected_seniority = []
selected_job_types = []
selected_remote = []
selected_tz = []
selected_companies = []

# --------- Filters (two UIs, same variables) ---------
if layout_mode.startswith("🖥️"):
    # DESKTOP: sidebar filters
    st.sidebar.header("Filters")

    q = st.sidebar.text_input("Search in Job title", "")

    selected_companies = st.sidebar.multiselect(
        "Choose by Company",
        options=company_options,
        default=[],
        help="Select specific companies to filter by. Leave empty to see all companies.",
    )

    selected_seniority = st.sidebar.multiselect(
        "Seniority",
        options=seniority_options,
        default=[],
        format_func=lambda v: SENIORITY_LABELS.get(v, v.title()),
    )

    selected_job_types = st.sidebar.multiselect(
        "Job type",
        options=job_type_options,
        default=[],
    )

    selected_remote = st.sidebar.multiselect(
        "Remote policy",
        options=remote_options,
        default=[],
        format_func=lambda v: REMOTE_LABELS.get(v, v.replace("_", " ").title()),
    )

    location_q = st.sidebar.text_input("Location contains", "")

    selected_tz_human = st.sidebar.multiselect(
        "Timezone overlap",
        options=tz_options_human,
        default=[],
        help="Choose the timezones companies expect you to overlap with.",
    )
    selected_tz = [tz.split(" — ")[0] for tz in selected_tz_human]

    tech_q = st.sidebar.text_input("Tech stack contains", "")

else:
    # MOBILE: filters in an expander on the main page
    with st.expander("Filters", expanded=True):
        st.subheader("Filters")

        q = st.text_input("Search in Job title", "")

        selected_companies = st.multiselect(
            "Choose by Company",
            options=company_options,
            default=[],
            help="Select specific companies to filter by. Leave empty to see all companies.",
        )

        selected_seniority = st.multiselect(
            "Seniority",
            options=seniority_options,
            default=[],
            format_func=lambda v: SENIORITY_LABELS.get(v, v.title()),
        )

        selected_job_types = st.multiselect(
            "Job type",
            options=job_type_options,
            default=[],
        )

        selected_remote = st.multiselect(
            "Remote policy",
            options=remote_options,
            default=[],
            format_func=lambda v: REMOTE_LABELS.get(v, v.replace("_", " ").title()),
        )

        location_q = st.text_input("Location contains", "")

        selected_tz_human = st.multiselect(
            "Timezone overlap",
            options=tz_options_human,
            default=[],
            help="Choose the timezones companies expect you to overlap with.",
        )
        selected_tz = [tz.split(" — ")[0] for tz in selected_tz_human]

        tech_q = st.text_input("Tech stack contains", "")

# --------- Apply filters ---------
filtered = df.copy()

if q:
    q_low = q.lower()
    filtered = filtered[
        filtered["title"].fillna("").str.lower().str.contains(q_low)
    ]

if selected_companies:
    filtered = filtered[filtered["company"].isin(selected_companies)]

if selected_seniority:
    filtered = filtered[filtered["seniority_norm"].isin(selected_seniority)]

if selected_job_types:
    filtered = filtered[filtered["job_type"].isin(selected_job_types)]

if selected_remote:
    filtered = filtered[filtered["remote_policy"].isin(selected_remote)]

if location_q:
    loc_low = location_q.lower()
    filtered = filtered[
        filtered["location"].fillna("").str.lower().str.contains(loc_low)
    ]

if selected_tz:
    filtered = filtered[filtered["timezone_overlap"].isin(selected_tz)]

if tech_q:
    t = tech_q.lower()
    tech_cols = [
        "tech_stack.languages",
        "tech_stack.frameworks",
        "tech_stack.data",
        "tech_stack.cloud",
        "tech_stack.ml",
    ]
    mask = False
    for col in tech_cols:
        mask = mask | filtered[col].fillna("").str.lower().str.contains(t)
    filtered = filtered[mask]

# ---- Limit to MAX_ROWS for display ----
total_after_filters = len(filtered)
# if total_after_filters > MAX_ROWS:
#     st.warning(
#         f"Filters matched **{total_after_filters}** jobs. "
#         f"Showing only the first **{MAX_ROWS}**."
#     )
shown = filtered.head(MAX_ROWS).copy()

# st.write(
#     f"Showing **{len(shown)}** jobs "
#     f"(out of **{total_after_filters}** after filters)."
# )

# --------- Table display ---------
shown["remote_policy"] = shown["remote_policy"].astype("string")
shown["seniority_norm"] = shown["seniority_norm"].astype("string")

shown["remote_policy_pretty"] = (
    shown["remote_policy"]
    .map(REMOTE_LABELS)
    .fillna(shown["remote_policy"])
    .fillna("")
    .astype("string")
)

shown["seniority_pretty"] = (
    shown["seniority_norm"]
    .map(SENIORITY_LABELS)
    .fillna(shown["seniority_norm"])
    .fillna("")
    .astype("string")
)

display_cols = [
    "title",
    "company",
    "location",
    "seniority_pretty",
    "job_type",
    "remote_policy_pretty",
    "timezone_overlap",
    "posted_date",
    "source",
    "link",
]

existing_cols = [c for c in display_cols if c in shown.columns]

# Coerce all display columns (except link/posted_date) to string
for col in existing_cols:
    if col not in ("link", "posted_date"):
        shown[col] = shown[col].astype("string")

col_labels = {
    "title": "Job title",
    "company": "Company",
    "location": "Location",
    "seniority_pretty": "Seniority",
    "job_type": "Job type",
    "remote_policy_pretty": "Remote policy",
    "timezone_overlap": "Timezone overlap",
    "posted_date": "Posted",
    "source": "Source",
    "link": "Apply / Job link",
}

column_config = {
    "link": st.column_config.LinkColumn(col_labels["link"]),
    "posted_date": st.column_config.TextColumn(col_labels["posted_date"]),
}

for col in existing_cols:
    if col not in column_config:
        label = col_labels.get(col, col)
        column_config[col] = st.column_config.TextColumn(label)

st.data_editor(
    shown[existing_cols],
    column_config=column_config,
    hide_index=True,
    width="stretch",
)
