import os
import httpx
from base64 import b64encode
from typing import Optional

ATHLETE_ID = os.getenv("INTERVALS_ATHLETE_ID")
API_KEY = os.getenv("INTERVALS_API_KEY")
BASE = f"https://intervals.icu/api/v1/athlete/{ATHLETE_ID}"


def _headers() -> dict:
    # Intervals uses HTTP Basic auth: username="API_KEY", password=your_key
    token = b64encode(f"API_KEY:{API_KEY}".encode()).decode()
    return {
        "Authorization": f"Basic {token}",
        "Content-Type": "application/json",
    }


async def list_workouts(start_date: str, end_date: str) -> list:
    """Returns all events (workouts) between start_date and end_date (YYYY-MM-DD)."""
    async with httpx.AsyncClient() as client:
        r = await client.get(
            f"{BASE}/events",
            headers=_headers(),
            params={"oldest": start_date, "newest": end_date},
            timeout=15,
        )
        r.raise_for_status()
        events = r.json()
        # Return only planned workouts (category WORKOUT), not races or notes
        return [e for e in events if e.get("category") in ("WORKOUT", None)]


async def create_workout(
    date: str,
    name: str,
    description: str = "",
    sport_type: str = "Run",
    duration_seconds: Optional[int] = None,
) -> dict:
    """Create a planned workout on a given date."""
    payload = {
        "category": "WORKOUT",
        "start_date_local": date,
        "name": name,
        "description": description,
        "type": sport_type,
    }
    if duration_seconds:
        payload["moving_time"] = duration_seconds

    async with httpx.AsyncClient() as client:
        r = await client.post(
            f"{BASE}/events",
            headers=_headers(),
            json=payload,
            timeout=15,
        )
        r.raise_for_status()
        return r.json()


async def update_workout(event_id: str, data: dict) -> dict:
    """Edit any fields on an existing planned workout. Pass only the fields to change."""
    async with httpx.AsyncClient() as client:
        r = await client.put(
            f"{BASE}/events/{event_id}",
            headers=_headers(),
            json=data,
            timeout=15,
        )
        r.raise_for_status()
        return r.json()


async def delete_workout(event_id: str) -> dict:
    """Permanently delete a planned workout from Intervals.icu."""
    async with httpx.AsyncClient() as client:
        r = await client.delete(
            f"{BASE}/events/{event_id}",
            headers=_headers(),
            timeout=15,
        )
        r.raise_for_status()
        return {"deleted": event_id, "status": "ok"}
