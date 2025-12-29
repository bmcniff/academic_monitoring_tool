import streamlit as st
import pandas as pd
import gspread
import datetime
from google.oauth2.service_account import Credentials

# ---------------- CONFIG ----------------
SERVICE_ACCOUNT_FILE = "student-tracker-service-account.json"
SPREADSHEET_NAME = "Assignemnt_tracking_sample_data"
WORKSHEET_NAME = "Sheet1"

ALLOWED_VALUES = [
    "Not Started",
    "In Progress",
    "Complete",
    "Needs Review"
]

# ---------------- AUTH ----------------
@st.cache_resource
def get_worksheet():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]

    creds = Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE,
        scopes=scopes
    )

    client = gspread.authorize(creds)
    sheet = client.open(SPREADSHEET_NAME)
    return sheet.worksheet(WORKSHEET_NAME)


@st.cache_data(ttl=30)
def load_sheet_as_df():
    ws = get_worksheet()
    data = ws.get_all_records()
    return pd.DataFrame(data)


# ---------------- UPSERT ----------------
def upsert_value(student_name, date, assignment, lap, value):
    ws = get_worksheet()
    df = load_sheet_as_df()

    match = df[
        (df["student_name"] == student_name) &
        (df["date"] == date) &
        (df["assignment"] == assignment) &
        (df["lap"] == lap)
    ]

    if not match.empty:
        row_index = int(match.index[0]) + 2
        value_col = df.columns.get_loc("value") + 1
        ws.update_cell(row_index, value_col, str(value))
        return "updated"

    else:
        ws.append_row([
            str(student_name),
            str(date),
            str(assignment),
            int(lap),
            str(value)
        ])
        return "inserted"


# ---------------- UI ----------------
st.set_page_config(page_title="Student Assignment Tracker", layout="centered")
st.title("📘 Student Assignment Tracker")

df = load_sheet_as_df()

if df.empty:
    st.warning("Sheet is empty. First entry will create data.")
    df = pd.DataFrame(columns=["student_name", "date", "assignment", "lap", "value"])

date_obj = st.date_input(
    "Date",
    value=datetime.date.today()
)

date = date_obj.isoformat()

student = st.selectbox(
    "Student Name",
    sorted(df["student_name"].unique())
)

assignment = st.selectbox(
    "Assignment",
    sorted(df["assignment"].unique())
)

lap = st.selectbox(
    "Lap",
    sorted(df["lap"].unique())
)

# ---- CURRENT VALUE (IF EXISTS) ----
existing = df[
    (df["student_name"] == student) &
    (df["date"] == date) &
    (df["assignment"] == assignment) &
    (df["lap"] == lap)
]

current_value = existing["value"].iloc[0] if not existing.empty else None

st.markdown(f"**Current Value:** `{current_value}`")

# ---- VALUE UPDATE ----
new_value = st.radio(
    "New Value",
    ALLOWED_VALUES,
    index=ALLOWED_VALUES.index(current_value)
    if current_value in ALLOWED_VALUES
    else 0
)

# ---- SUBMIT ----
if st.button("💾 Save"):
    result = upsert_value(
        student_name=student,
        date=date,
        assignment=assignment,
        lap=lap,
        value=new_value
    )

    st.success(f"Successfully {result} record.")
    st.cache_data.clear()
    st.rerun()
