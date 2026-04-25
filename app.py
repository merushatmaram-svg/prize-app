import pandas as pd
import streamlit as st
import gspread
import json
from google.oauth2.service_account import Credentials
# ======================
# GOOGLE AUTH (STREAMLIT CLOUD)
# ======================
scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

# ✅ FIX: load raw JSON string safely
creds_dict = st.secrets["gcp_service_account"]

creds = Credentials.from_service_account_info(
    creds_dict,
    scopes=scope
)

client = gspread.authorize(creds)

SPREADSHEET_ID = "15L-szxjc6o3dUkXuCucYLYb7QFHbStJpWZBWsgjewyI"

prize_sheet = client.open_by_key(SPREADSHEET_ID).sheet1
question_sheet = client.open_by_key(SPREADSHEET_ID).worksheet("Sheet2")

# ======================
# UI
# ======================
st.set_page_config(page_title="Prize Game", page_icon="🎁")

st.title("🎁 Mystery Prize Game")

name = st.text_input("Enter your name")

def clean_name(n):
    return n.strip().title()

# ======================
# LOAD QUESTION (ONCE)
# ======================
if "question" not in st.session_state:
    q_data = question_sheet.get_all_records()
    q_df = pd.DataFrame(q_data)
    st.session_state.question = q_df.sample(1).iloc[0]

q = st.session_state.question

# ======================
# DISPLAY QUESTION
# ======================
if name:
    st.write("### 🧠 Answer this question to improve your chances:")
    st.write(q["Question"])

    answer = st.radio(
        "Choose your answer:",
        ["A", "B", "C"],
        format_func=lambda x: q[x]
    )

# ======================
# SPONSOR CHECK
# ======================
def is_sponsor(sponsor_cell, user_name):
    if pd.isna(sponsor_cell) or sponsor_cell == "":
        return False
    sponsors = [s.strip().title() for s in str(sponsor_cell).split(";")]
    return user_name in sponsors

# ======================
# ASSIGN PRIZE
# ======================
def assign_prize(user_name, correct):
    df = pd.DataFrame(prize_sheet.get_all_records())

    user_name = clean_name(user_name)

    # Prevent duplicate participation
    if user_name in df["Assigned To"].astype(str).values:
        return "already"

    # Filter eligible prizes
    available = df[
        (df["Assigned To"].isna() | (df["Assigned To"] == "")) &
        (~df["Sponsor"].apply(lambda x: is_sponsor(x, user_name)))
    ]

    if available.empty:
        return "none"

    # Weight probabilities
    if correct:
        weights = available["Prize category"].map({
            "Big": 5,
            "Medium": 3,
            "Small": 1
        })
    else:
        weights = available["Prize category"].map({
            "Big": 1,
            "Medium": 2,
            "Small": 5
        })

    chosen = available.sample(1, weights=weights).index[0]

    df.at[chosen, "Assigned To"] = user_name

    # Update Google Sheet
    prize_sheet.update([df.columns.tolist()] + df.values.tolist())

    return "ok"

# ======================
# SUBMIT BUTTON
# ======================
if name:
    submitted = st.button("Submit answer & draw prize")

    if submitted:
        is_correct = (answer == q["Correct"])

        result = assign_prize(name, is_correct)

        if result == "ok":
            if is_correct:
                st.success("🎉 Correct! Your chances were boosted!")
            else:
                st.success("🎁 Prize assigned!")
        elif result == "already":
            st.warning("You already participated.")
        elif result == "none":
            st.error("No eligible prizes left.")
