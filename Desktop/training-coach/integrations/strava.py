import os
import time
import httpx
from fastapi import HTTPException
from coach.memory import save_activity, save_token, get_token

VERIFY_TOKEN = os.getenv("STRAVA_VERIFY_TOKEN")
CLIENT_ID = os.getenv("STRAVA_CLIENT_ID")
CLIENT_SECRET = os.getenv("STRAVA_CLIENT_SECRET")


# ── Webhook verification ──────────────────────────────────────────────────────

def verify_webhook(params: dict) -> dict:
    """Responds to Strava's hub challenge during webhook registration."""
    if params.get("hub.verify_token") != VERIFY_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid verify token")
    return {"hub.challenge": params.get("hub.challenge")}


# ── Token management ──────────────────────────────────────────────────────────

async def get_valid_access_token() -> str:
    """Returns a valid access token, refreshing if expired."""
    token = get_token()
    if not token:
        raise Exception(
            "No Strava token stored. "
            "Visit https://your-railway-url/strava-auth to authorise."
        )
    # Refresh if expires within 5 minutes
    if token["expires_at"] < time.time() + 300:
        async with httpx.AsyncClient() as client:
            r = await client.post(
                "https://www.strava.com/oauth/token",
                data={
                    "client_id": CLIENT_ID,
                    "client_secret": CLIENT_SECRET,
                    "refresh_token": token["refresh_token"],
                    "grant_type": "refresh_token",
                },
            )
            r.raise_for_status()
            data = r.json()
        save_token(data["access_token"], data["refresh_token"], data["expires_at"])
        return data["access_token"]
    return token["access_token"]


# ── Activity fetch ────────────────────────────────────────────────────────────

async def fetch_full_activity(activity_id: str, access_token: str) -> dict:
    """Fetches the full activity detail from Strava API."""
    async with httpx.AsyncClient() as client:
        r = await client.get(
            f"https://www.strava.com/api/v3/activities/{activity_id}",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=15,
        )
        r.raise_for_status()
        return r.json()


# ── Main webhook handler ──────────────────────────────────────────────────────

async def handle_strava_event(payload: dict):
    """
    Called on every Strava webhook POST.
    Only processes 'activity created' events.
    Fetches full activity, stores as JSON, triggers AI review via Telegram.
    """
    # Only handle new activity creation
    if payload.get("object_type") != "activity":
        return
    if payload.get("aspect_type") != "create":
        return

    activity_id = str(payload["object_id"])

    # Import here to avoid circular imports
    from bot.telegram import send_message
    from coach.ai import generate_activity_review

    try:
        access_token = await get_valid_access_token()
        activity = await fetch_full_activity(activity_id, access_token)

        sport_type = activity.get("sport_type") or activity.get("type") or "unknown"
        name = activity.get("name", "Activity")

        # Store full activity JSON, keyed by sport type
        save_activity(
            strava_id=activity_id,
            sport_type=sport_type,
            name=name,
            data=activity,
        )

        # Generate and send coaching review
        review = await generate_activity_review(activity)
        await send_message(review)

    except Exception as e:
        from bot.telegram import send_message
        await send_message(f"⚠️ Activity logged but review failed: {str(e)}")
