from fastapi import FastAPI, BackgroundTasks
import pandas as pd
import asyncio
import datetime
from contextlib import asynccontextmanager
from leaderboard.services.athlete_services import (
    get_raw_athlete_activies_by_uid,
    filter_athlete,
    get_athlete,
)
from leaderboard.install import run_once

run_once()

REFRESH_INTERVAL_SECONDS = 3600
TIMEZONE = datetime.timezone(datetime.timedelta(hours=+7), "UTC")


# In-memory cache
class Cache:
    def __init__(self):
        self.df: pd.DataFrame | None = None
        # Set to None initially so frontend doesn't get a fake "loaded" timestamp
        self.last_updated: pd.Timestamp | None = None
        self.is_refreshing: bool = False


cache = Cache()
refresh_lock = asyncio.Lock()


def build_leaderboard() -> pd.DataFrame:
    raw_data = filter_athlete(get_athlete())
    df = pd.DataFrame([athlete.model_dump() for athlete in raw_data])

    def fetch_athlete_activities(uid: str) -> pd.DataFrame:
        resp = get_raw_athlete_activies_by_uid(uid)
        activities = resp.json().get("result", [])
        df = pd.DataFrame(activities)
        if df.empty:
            return df
        df["uid"] = uid
        return df

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

    df = df.merge(agg, left_on="data_uid", right_on="uid", how="left").drop(
        columns="uid"
    )
    return df


async def refresh_cache(force: bool = False):
    """Refresh the in-memory cache. Skips if a refresh is already in progress,
    unless force=True is passed (force still waits for the lock, it just
    doesn't bail out early)."""
    if cache.is_refreshing and not force:
        return

    async with refresh_lock:
        cache.is_refreshing = True
        try:
            new_df = await asyncio.to_thread(build_leaderboard)
            cache.df = new_df
            cache.last_updated = pd.Timestamp.now(TIMEZONE)
        except Exception as e:
            print(f"[refresh_cache] Error refreshing leaderboard: {e}")
        finally:
            cache.is_refreshing = False


async def refresh_cache_loop():
    while True:
        await refresh_cache()
        await asyncio.sleep(REFRESH_INTERVAL_SECONDS)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # REMOVED: `await refresh_cache()`
    # The API will now start immediately. The loop below will handle the
    # initial fetch in the background as soon as the event loop starts.
    task = asyncio.create_task(refresh_cache_loop())
    yield
    task.cancel()


app = FastAPI(lifespan=lifespan)


@app.get("/leaderboard")
def get_leaderboard():
    # Pass 'is_refreshing' so the frontend can show a loader if needed
    if cache.df is None:
        return {"data": [], "last_updated": None, "is_refreshing": cache.is_refreshing}
    return {
        "data": cache.df.to_dict(orient="records"),
        "last_updated": cache.last_updated.isoformat() if cache.last_updated else None,
        "is_refreshing": cache.is_refreshing,
    }


@app.post("/leaderboard/refresh")
async def trigger_refresh(background_tasks: BackgroundTasks):
    """Manually trigger a leaderboard refresh in the background.
    Returns immediately with the currently cached data while the
    refresh runs asynchronously."""
    background_tasks.add_task(refresh_cache, True)
    return {
        "message": "Leaderboard refresh scheduled",
        "last_updated": cache.last_updated.isoformat() if cache.last_updated else None,
        "is_refreshing": True,
        "data": cache.df.to_dict(orient="records") if cache.df is not None else [],
    }
