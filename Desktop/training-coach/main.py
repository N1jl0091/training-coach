from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from contextlib import asynccontextmanager
import httpx
import os
from dotenv import load_dotenv

load_dotenv()

from coach.memory import init_db, save_token
from bot.telegram import handle_telegram_update
from integrations.strava import verify_webhook, handle_strava_event

CLIENT_ID = os.getenv("STRAVA_CLIENT_ID")
CLIENT_SECRET = os.getenv("STRAVA_CLIENT_SECRET")
RAILWAY_URL = os.getenv("RAILWAY_PUBLIC_DOMAIN", "localhost:8000")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(lifespan=lifespan)


@app.get("/")
def health():
    return {"status": "coach is running"}


# ── Strava OAuth ──────────────────────────────────────────────────────────────
# Visit https://your-railway-url/strava-auth once after deploy to connect Strava

@app.get("/strava-auth")
def strava_auth():
    redirect = f"https://{RAILWAY_URL}/strava-callback"
    url = (
        f"https://www.strava.com/oauth/authorize"
        f"?client_id={CLIENT_ID}"
        f"&response_type=code"
        f"&redirect_uri={redirect}"
        f"&approval_prompt=force"
        f"&scope=activity:read_all"
    )
    return RedirectResponse(url)


@app.get("/strava-callback")
async def strava_callback(code: str):
    async with httpx.AsyncClient() as client:
        r = await client.post(
            "https://www.strava.com/oauth/token",
            data={
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "code": code,
                "grant_type": "authorization_code",
            },
        )
        data = r.json()
    save_token(data["access_token"], data["refresh_token"], data["expires_at"])
    return HTMLResponse("<h2>✅ Strava connected. You can close this tab.</h2>")


# ── Strava webhook ────────────────────────────────────────────────────────────

@app.get("/strava-webhook")
def strava_verify(request: Request):
    return verify_webhook(dict(request.query_params))


@app.post("/strava-webhook")
async def strava_event(request: Request):
    payload = await request.json()
    await handle_strava_event(payload)
    return {"status": "ok"}


# ── Telegram webhook ──────────────────────────────────────────────────────────

@app.post("/telegram-webhook")
async def telegram_update(request: Request):
    payload = await request.json()
    await handle_telegram_update(payload)
    return {"status": "ok"}
