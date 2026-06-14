import pandas as pd
import streamlit as st
import requests
import subprocess
import time 
import os 

os.environ["ACTIVIES_URL"] = st.secrets["ACTIVIES_URL"]
os.environ["LEADERBOARD_URL"] = st.secrets["ACTIVIES_URL"]

# 1. Start FastAPI in the background on localhost
@st.cache_resource
def start_fastapi():
    process = subprocess.Popen(
        ["uvicorn", "fastapi_app:app", "--host", "127.0.0.1", "--port", "8000"]
    )
    time.sleep(2) # Give the server a moment to spin up
    return process

# Trigger the background process
fastapi_process = start_fastapi()

# Set wide layout for a modern, dashboard feel
st.set_page_config(page_title="Athlete Leaderboard", page_icon="🏃‍♂️", layout="wide")

FASTAPI_URL = "http://127.0.0.1:8000/leaderboard"

@st.cache_data(ttl=60)  # short TTL, just to avoid hammering API on every rerun
def fetch_leaderboard_payload():
    try:
        resp = requests.get(FASTAPI_URL)
        resp.raise_for_status()
        payload = resp.json()
        return pd.DataFrame(payload["data"]), payload["last_updated"]
    
    except requests.exceptions.HTTPError:
        st.error(f"Backend API returned an HTTP error: {resp.status_code}")
        # Render the raw HTML/text response so you can see what went wrong
        st.code(resp.text[:1000], language="html") 
        return pd.DataFrame(), None

    except requests.exceptions.JSONDecodeError:
        st.error("Backend did not return valid JSON. It might be sending an HTML error page.")
        st.code(resp.text[:1000], language="html")
        return pd.DataFrame(), None

    except Exception as e:
        st.error(f"Could not connect to the backend: {e}")
        return pd.DataFrame(), None

@st.cache_data(ttl=3600)
def refresh_leaderboard_payload():
    requests.post(FASTAPI_URL + "/refresh")
    return 
    

def main():
    st.title("🏃‍♂️ Performance Leaderboard")
    st.markdown("Track real-time athlete rankings, points, and activity streaks.")
    st.write("---")
    refresh_leaderboard_payload()
    df, last_updated = fetch_leaderboard_payload()
   
    st.caption(f"Last updated: {last_updated}")

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
            )

        with pod2:
            if len(df) > 1:
                top_2 = df.iloc[1]
                st.metric(
                    label="🥈 2nd Place",
                    value=top_2["name"],
                )

        with pod3:
            if len(df) > 2:
                top_3 = df.iloc[2]
                st.metric(
                    label="🥉 3rd Place",
                    value=top_3["name"],
                )

    st.write("---")

    # --- 4. SIDEBAR FILTERS ---
    st.sidebar.header("Filter & Search")

    # Search by Athlete Name
    search_query = st.sidebar.text_input("🔍 Search Athlete Name", "").strip()
    if st.sidebar.button("Refresh Data"):
        fetch_leaderboard_payload.clear()
        st.rerun()

    # --- 5. FILTER LOGIC & MAIN TABLE ---
    # Apply interactive filters to the dataframe

    # Modern Streamlit Dataframe configuration with custom columns
    if not df.empty:
        filtered_df = df[(df["name"].str.contains(search_query, case=False, na=False))]

        st.dataframe(
            filtered_df,
            column_config={
                "rank": st.column_config.NumberColumn(
                    "Rank", format="%d", help="Current leaderboard standing"
                ),
                "name": st.column_config.TextColumn("Athlete Name"),
                "points": st.column_config.ProgressColumn(
                    "Total Points",
                    help="Accumulated activity points",
                    format="%d",
                    min_value=0,
                    max_value=int(df["points"].max()),
                ),
                "streak": st.column_config.TextColumn(
                    "Current Streak", help="Consecutive active days"
                ),
                "company": None,
                "data_uid": None,
                "activities": st.column_config.NumberColumn(
                    "Activities Count", format="%d"
                ),
                "Run": st.column_config.NumberColumn(
                    "Run", format="%f km"
                ),
            },
            hide_index=True,
            width='content',
        )
    else:
        with st.spinner("Processing data, please wait..."):
            # Put your time-consuming code block here
            time.sleep(3) 
            st.rerun()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        fastapi_process.kill()
