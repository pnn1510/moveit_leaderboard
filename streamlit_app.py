import pandas as pd
import streamlit as st
import requests

# Set wide layout for a modern, dashboard feel
st.set_page_config(page_title="Athlete Leaderboard", page_icon="🏃‍♂️", layout="wide")


FASTAPI_URL = "http://localhost:8000/leaderboard"

@st.cache_data(ttl=60)  # short TTL, just to avoid hammering API on every rerun
def fetch_leaderboard_payload():
    resp = requests.get(FASTAPI_URL)
    resp.raise_for_status()
    payload = resp.json()
    return pd.DataFrame(payload["data"]), payload["last_updated"]

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
    filtered_df = df[(df["name"].str.contains(search_query, case=False, na=False))]

    # Modern Streamlit Dataframe configuration with custom columns
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


main()
