import streamlit as st
import gspread
import pandas as pd
import random
import json
from google.oauth2.service_account import Credentials

# ---------------------------
# CONFIG
# ---------------------------
SPREADSHEET_ID = "15L-szxjc6o3dUkXuCucYLYb7QFHbStJpWZBWsgjewyI"

scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

# ---------------------------
# AUTHENTICATION
# ---------------------------
creds_dict = json.loads(st.secrets["gcp_service_account"])

creds = Credentials.from_service_account_info(
    creds_dict,
    scopes=scope
)

client = gspread.authorize(creds)

# ---------------------------
# LOAD SHEETS
# ---------------------------
sheet = client.open_by_key(SPREADSHEET_ID)

prize_sheet = sheet.sheet1
question_sheet = sheet.worksheet("Sheet2")

# Convert to DataFrame
prizes_df = pd.DataFrame(prize_sheet.get_all_records())
questions_df = pd.DataFrame(question_sheet.get_all_records())

# ---------------------------
# UI
# ---------------------------
st.title("🎁 Prize Draw")

name = st.text_input("Enter your name")

if name:

    # ---------------------------
    # PICK RANDOM QUESTION
    # ---------------------------
    question_row = questions_df.sample(1).iloc[0]

    st.subheader("Answer this question:")

    question = question_row["Question"]

    options = [
        question_row["Option A"],
        question_row["Option B"],
        question_row["Option C"]
    ]

    correct_answer = question_row["Correct Answer"]

    user_answer = st.radio(question, options)

    if st.button("Submit"):

        # ---------------------------
        # CHECK ANSWER
        # ---------------------------
        correct = user_answer == correct_answer

        if correct:
            st.success("Correct! Better chances 🎉")
        else:
            st.warning("Wrong answer 😅")

        # ---------------------------
        # FILTER ELIGIBLE PRIZES
        # ---------------------------
        available = prizes_df[prizes_df["Assigned To"] == ""]

        def is_eligible(row):
            sponsors = str(row["Sponsor"]).split(";") if row["Sponsor"] else []
            return name not in sponsors

        available = available[available.apply(is_eligible, axis=1)]

        if available.empty:
            st.error("No prizes left for you 😢")
            st.stop()

        # ---------------------------
        # WEIGHTED RANDOM
        # ---------------------------
        weighted_list = []

        for _, row in available.iterrows():
            category = row["Prize category"]

            if correct:
                weight = {"Small": 1, "Medium": 3, "Big": 5}.get(category, 1)
            else:
                weight = {"Small": 5, "Medium": 2, "Big": 1}.get(category, 1)

            weighted_list.extend([row] * weight)

        selected = random.choice(weighted_list)

        # ---------------------------
        # ASSIGN PRIZE
        # ---------------------------
        prize_number = selected["Prize Numbers"]

        cell = prize_sheet.find(str(prize_number))
        prize_sheet.update_cell(cell.row, 4, name)  # column 4 = Assigned To

        # ---------------------------
        # RESULT (hidden prize)
        # ---------------------------
        st.success("🎉 Your prize has been assigned!")
        st.info("You’ll discover it later 😉")
