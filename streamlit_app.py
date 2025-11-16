import streamlit as st
import pandas as pd
from pathlib import Path

# --------- Config ---------
DATA_PATH = Path("data/jobs_latest.csv")  # rename your file to this or adjust path

st.set_page_config(
    page_title="Remote Jobs Explorer",
    layout="wide",
)

# --------- Data loader ---------
@st.cache_data
def load_jobs(path: Path) -> pd.DataFrame:
    # Your CSV uses ';' as delimiter
    df = pd.read_csv(path, sep=";")

    # Coerce salary columns to numeric (still useful for later, but not shown)
    for col in ["salary_min", "salary_max", "salary_annual_min", "salary_annual_max"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Try to parse posted_at as datetime for sorting
    if "posted_at" in df.columns:
        df["posted_at_dt"] = pd.to_datetime(df["posted_at"], errors="coerce")
        df = df.sort_values("posted_at_dt", ascending=False)

    # Ensure some optional columns exist so filters don’t crash
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

if not DATA_PATH.exists():
    st.error(
        f"CSV not found at: {DATA_PATH}\n\n"
        "Put a file like jobs_refined_YYYY-MM-DD_HH-MM-SS.csv "
        "there and/or rename it to jobs_latest.csv."
    )
    st.stop()

df = load_jobs(DATA_PATH)

# --------- Header ---------
st.title("🌐 Remote/Hybrid Jobs Explorer")
st.caption("Daily curated remote jobs")

st.write(f"Total jobs in this snapshot: **{len(df)}**")

# --------- Sidebar filters ---------
st.sidebar.header("Filters")

# Text search (title + company)
q = st.sidebar.text_input("Search in title / company", "")

# Seniority (normalized)
seniority_options = sorted(
    s
    for s in df["seniority_norm"].dropna().unique()
    if str(s).strip() and str(s).lower() != "unspecified"
)
selected_seniority = st.sidebar.multiselect(
    "Seniority",
    options=seniority_options,
    default=seniority_options,
)

# Job type
job_type_options = sorted(
    s for s in df["job_type"].dropna().unique() if str(s).strip()
)
selected_job_types = st.sidebar.multiselect(
    "Job type",
    options=job_type_options,
    default=job_type_options,
)

# Remote policy
remote_options = sorted(
    s for s in df["remote_policy"].dropna().unique() if str(s).strip()
)
selected_remote = st.sidebar.multiselect(
    "Remote policy",
    options=remote_options,
    default=remote_options,
)

# Location contains
location_q = st.sidebar.text_input("Location contains", "")

# Timezone overlap
tz_options = sorted(
    s for s in df["timezone_overlap"].dropna().unique() if str(s).strip()
)
selected_tz = st.sidebar.multiselect(
    "Timezone overlap",
    options=tz_options,
    default=tz_options,
)

# Very simple tech search across all tech_stack.* columns
tech_q = st.sidebar.text_input("Tech stack contains", "")

# --------- Apply filters ---------
filtered = df.copy()

if q:
    q_low = q.lower()
    filtered = filtered[
        filtered["title"].fillna("").str.lower().str.contains(q_low)
        | filtered["company"].fillna("").str.lower().str.contains(q_low)
    ]

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

st.write(f"Showing **{len(filtered)}** jobs after filters.")

# --------- Table display ---------
display_cols = [
    "title",
    "company",
    "location",
    "seniority_norm",
    "job_type",
    "remote_policy",
    "timezone_overlap",
    "posted_at",
    "source",
    "link",
]

existing_cols = [c for c in display_cols if c in filtered.columns]

st.data_editor(
    filtered[existing_cols],
    column_config={
        "link": st.column_config.LinkColumn("Job link"),
    },
    hide_index=True,
    use_container_width=True,
)

# Optional: download filtered as CSV
csv_bytes = filtered.to_csv(index=False, sep=";").encode("utf-8")
st.download_button(
    "Download filtered jobs as CSV",
    data=csv_bytes,
    file_name="filtered_jobs.csv",
    mime="text/csv",
)
