import pandas as pd
import streamlit as st

from leaderboard.services.athlete_services import (
    filter_athlete,
    get_athlete,
    get_raw_athlete_activies_by_uid,
)

# Set wide layout for a modern, dashboard feel
st.set_page_config(page_title="Athlete Leaderboard", page_icon="🏃‍♂️", layout="wide")


# --- Model --- #


# --- 1. DATA FETCHING (Simulating your function) ---
def fetch_athlete_activities(uid: str) -> pd.DataFrame:
    resp = get_raw_athlete_activies_by_uid(uid)
    activities = resp.json().get("result", [])
    df = pd.DataFrame(activities)
    if df.empty:
        return df
    df["uid"] = uid
    return df


@st.cache_data(ttl=3600)
def fetch_leaderboard_payload():
    raw_data = filter_athlete(get_athlete())
    df = pd.DataFrame([athlete.model_dump() for athlete in raw_data])

    # Fetch and aggregate activities per athlete
    activity_frames = [
        fetch_athlete_activities(a["data_uid"]) for a in df.to_dict("records")
    ]
    activities_df = pd.concat(activity_frames, ignore_index=True)

    agg = (
        activities_df.groupby(["uid", "type"])["distanceKm"]
        .sum()
        .unstack(fill_value=0)
        .reset_index()
    )

    # Enrich leaderboard with aggregated distances
    df = df.merge(agg, left_on="data_uid", right_on="uid", how="left").drop(
        columns="uid"
    )

    return df


def main():

    # --- 3. APP HEADER & METRICS ---
    st.title("🏃‍♂️ Performance Leaderboard")
    st.markdown("Track real-time athlete rankings, points, and activity streaks.")
    st.write("---")

    df = fetch_leaderboard_payload()
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
            "data_uid": None,
            "activities": st.column_config.NumberColumn(
                "Activities Count", format="%d"
            ),
        },
        hide_index=True,
        use_container_width=True,
    )


main()
