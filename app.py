import streamlit as st
import pandas as pd
import gspread
import datetime
from google.oauth2.service_account import Credentials


# ---------------- CONFIG ----------------
SERVICE_ACCOUNT_FILE = "student-tracker-service-account.json"
SPREADSHEET_NAME = "Assignment_tracking_sample_data"
WORKSHEET_NAME = "records"


# ---------------- AUTH ----------------
@st.cache_resource
def get_worksheet():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]

    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
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

def load_sheet_as_df():
    ws = get_worksheet()
    data = ws.get_all_records()
    return pd.DataFrame(data)

@st.cache_resource
def get_sheet():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]

    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=scopes
    )

    client = gspread.authorize(creds)
    return client.open(SPREADSHEET_NAME)

@st.cache_data(ttl=60)
def load_students_df():
    sheet = get_sheet()
    df = pd.DataFrame(sheet.worksheet("students").get_all_records())
    return df


@st.cache_data(ttl=60)
def load_allowed_values_df():
    sheet = get_sheet()
    df = pd.DataFrame(sheet.worksheet("allowed_values").get_all_records())
    df["lap"] = df["lap"].astype(int)
    return df


@st.cache_data(ttl=30)
def load_records_df():
    sheet = get_sheet()
    df = pd.DataFrame(sheet.worksheet("records").get_all_records())
    df["lap"] = df["lap"].astype(int)
    df["date"] = df["date"].astype(str)
    return df


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
st.set_page_config(page_title="Academic Monitoring Tool", layout="centered")
st.title("📘 Academic Monitoring Tool")

df = load_sheet_as_df()

if df.empty:
    st.warning("Sheet is empty. First entry will create data.")
    df = pd.DataFrame(columns=["student_name", "date", "assignment", "lap", "value"])

date_obj = st.date_input(
    "Date",
    value=datetime.date.today()
)

date = date_obj.isoformat()

allowed_df = load_allowed_values_df()


students_df = load_students_df()

student = st.selectbox(
    "Student",
    sorted(students_df["student"].unique())
)

records_df = load_records_df()

assignment = st.selectbox(
    "Assignment",
    sorted(allowed_df["assignment"].unique())
)

lap = st.selectbox(
    "Lap",
    sorted(allowed_df["lap"].unique())
)

value_options = allowed_df[
    (allowed_df["assignment"] == assignment) &
    (allowed_df["lap"] == lap)
].sort_values("points", ascending=False)

if value_options.empty:
    st.error("No allowed values defined for this assignment/lap combination.")
    st.stop()


# ---- CURRENT VALUE (IF EXISTS) ----
existing = df[
    (df["student_name"] == student) &
    (df["date"] == date) &
    (df["assignment"] == assignment) &
    (df["lap"] == lap)
]

current_value = existing["value"].iloc[0] if not existing.empty else None

# st.markdown(f"**Current Value:** `{current_value}`")


# ---- VALUE UPDATE ----
value_labels = value_options["value"].tolist()

if current_value in value_labels:
    default_index = value_labels.index(current_value)
else:
    default_index = 0

if current_value:
    st.caption(f"Currently saved value: **{current_value}**")
else:
    st.caption("No value saved yet — selecting one will create a new record.")

new_value = st.radio(
    "Value",
    value_labels,
    index=default_index,
    horizontal=False
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
