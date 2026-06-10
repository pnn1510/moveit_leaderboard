import json
import re
from typing import List

import pandas as pd
import streamlit as st
from pydantic import BaseModel, RootModel

# Set wide layout for a modern, dashboard feel
st.set_page_config(
    page_title="Athlete Leaderboard", page_icon="🏃‍♂️", layout="wide"
)

# --- Model --- #

class Athlete(BaseModel):
    rank: int
    name: str
    company: str
    points: int
    streak: int
    activities: int


# Using Pydantic V2 RootModel to handle an un-keyed JSON array list
class AthleteList(RootModel[List[Athlete]]):
    pass


# 2. Define the JSON Cleanup Function
def clean_leaderboard_json(raw_json_string: str) -> List[dict]:
    """Parses raw JSON string, sanitizes keys, transforms strings to integers,

    strips out emojis, and returns a Pydantic-compatible dictionary list.
    """
    raw_data = json.loads(raw_json_string)
    cleaned_list = []

    for item in raw_data:
        # Extract only digits from the Streak field (e.g., "🔥 3" -> 3)
        streak_raw = item.get("Streak", "0")
        streak_match = re.search(r"\d+", streak_raw)
        streak_val = int(streak_match.group()) if streak_match else 0

        # Remove the pin emoji and excess trailing space from the Athlete name
        clean_name = item.get("Athlete", "").replace(" 📍", "").strip()

        # Build the clean dictionary matching Pydantic fields exactly
        cleaned_item = {
            "rank": int(item.get("Rank", 0)),
            "name": clean_name,
            "company": item.get("Company / School", "").strip(),
            "points": int(item.get("Points", 0)),
            "streak": streak_val,
            "activities": int(item.get("Activities", 0)),
        }
        cleaned_list.append(cleaned_item)

    return cleaned_list


# 3. Refactored Data Ingestion Function
def get_athlete() -> List[Athlete]:
    with open("./downloads/leaderboard.json", "r", encoding="utf-8") as file:
        athlete_string = file.read()

    # Clean the data layer first
    cleaned_data_dicts = clean_leaderboard_json(athlete_string)

    # Validate using Pydantic's Python object validator (.model_validate instead of _json)
    athlete_obj = AthleteList.model_validate(cleaned_data_dicts)

    return athlete_obj.root

def filter_athlete(list_ath: list[Athlete]):
    return [p for p in list_ath if "thoughtworks" in p.company.lower()]
    
# --- 1. DATA FETCHING (Simulating your function) ---
@st.cache_data
def fetch_leaderboard_payload():
    # Replace this block with your actual function call, e.g., requests.get().json()
    payload: list[Athlete] = get_athlete()
    
    payload = filter_athlete(payload)
    return payload


# --- 2. DATA PROCESSING ---
def get_clean_dataframe():
    raw_data = fetch_leaderboard_payload()
    df = pd.DataFrame([athlete.model_dump() for athlete in raw_data])

    # # Convert numeric strings to actual integers for proper sorting/rendering
    # df["Rank"] = pd.to_numeric(df["Rank"])
    # df["Points"] = pd.to_numeric(df["Points"])
    # df["Activities"] = pd.to_numeric(df["Activities"])

    # # Clean up empty strings in Company/School
    # df["Company / School"] = df["Company / School"].replace("", "Independent")

    # # Clean up the 📍 character if you prefer text-only search matching
    # df["Athlete"] = df["Athlete"].str.replace(" 📍", "", regex=False)

    return df

def main():
    df = get_clean_dataframe()

    # --- 3. APP HEADER & METRICS ---
    st.title("🏃‍♂️ Performance Leaderboard")
    st.markdown("Track real-time athlete rankings, points, and activity streaks.")
    st.write("---")

    # Top 3 Podium Highlights
    st.subheader("🏆 Top Performers")
    pod1, pod2, pod3 = st.columns(3)

    # Safeguard in case dataframe is empty
    if not df.empty:
        with pod1:
            top_1 = df.iloc[0]
            st.metric(
                label="🥇 1st Place",
                value=top_1["name"],
                delta=f"{top_1['points']} Pts ({top_1['streak']})",
            )

        with pod2:
            if len(df) > 1:
                top_2 = df.iloc[1]
                st.metric(
                    label="🥈 2nd Place",
                    value=top_2["name"],
                    delta=f"{top_2['points']} Pts ({top_2['streak']})",
                )

        with pod3:
            if len(df) > 2:
                top_3 = df.iloc[2]
                st.metric(
                    label="🥉 3rd Place",
                    value=top_3["name"],
                    delta=f"{top_3['points']} Pts ({top_3['streak']})",
                )

    st.write("---")

    # --- 4. SIDEBAR FILTERS ---
    st.sidebar.header("Filter & Search")

    # Search by Athlete Name
    search_query = st.sidebar.text_input("🔍 Search Athlete Name", "").strip()


    # --- 5. FILTER LOGIC & MAIN TABLE ---
    # Apply interactive filters to the dataframe
    filtered_df = df[
       (df["name"].str.contains(search_query, case=False, na=False))
    ]

    # Display total count of visible records
    st.write(f"Showing **{len(filtered_df)}** out of **{len(df)}** athletes.")

    # Modern Streamlit Dataframe configuration with custom columns
    st.dataframe(
        filtered_df,
        column_config={
            "Rank": st.column_config.NumberColumn(
                "Rank", format="%d", help="Current leaderboard standing"
            ),
            "Athlete": st.column_config.TextColumn("Athlete Name"),
            "Company / School": st.column_config.TextColumn(
                "Organization / Team"
            ),
            "Points": st.column_config.ProgressColumn(
                "Total Points",
                help="Accumulated activity points",
                format="%d",
                min_value=0,
                max_value=int(df["points"].max()),
            ),
            "Streak": st.column_config.TextColumn(
                "Current Streak", help="Consecutive active days"
            ),
            "Activities": st.column_config.NumberColumn(
                "Activities Logged", format="%d"
            ),
        },
        hide_index=True,
        use_container_width=True,
    )
    
main()