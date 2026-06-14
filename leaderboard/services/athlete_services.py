from typing import List
from pydantic import BaseModel, RootModel
import json
import re
import requests
import streamlit as st
from leaderboard.services.crawler import crawl

ACTIVITIES_URL = st.secrets["ACTIVIES_URL"]
# ACTIVITIES_URL = os.environ.get("ACTIVITIES_URL")

class Athlete(BaseModel):
    rank: int
    name: str
    company: str
    points: int
    streak: int
    activities: int
    data_uid: str 


# Using Pydantic V2 RootModel to handle an un-keyed JSON array list
class AthleteList(RootModel[List[Athlete]]):
    pass


# 2. Define the JSON Cleanup Function
def clean_leaderboard_json(raw_data: List[dict]) -> List[dict]:
    """Sanitizes keys, transforms strings to integers,
    strips out emojis, and returns a Pydantic-compatible dictionary list.
    """
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
            "data_uid": item.get("data_uid"),
        }
        cleaned_list.append(cleaned_item)
    return cleaned_list


# 3. Refactored Data Ingestion Function
def get_athlete() -> List[Athlete]:
    raw_data = crawl()
    # Clean the data layer first
    cleaned_data_dicts = clean_leaderboard_json(raw_data)
    # Validate using Pydantic's Python object validator (.model_validate instead of _json)
    athlete_obj = AthleteList.model_validate(cleaned_data_dicts)
    return athlete_obj.root


def filter_athlete(list_ath: list[Athlete]):
    return [p for p in list_ath if "thoughtworks" in p.company.lower()]


def get_raw_athlete_activies_by_uid(uid: str):
    url = ACTIVITIES_URL 

    payload = json.dumps({"data": {"uid": uid}})
    headers = {"Content-Type": "application/json"}

    return requests.request("POST", url, headers=headers, data=payload)
