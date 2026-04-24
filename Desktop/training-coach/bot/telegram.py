import os
import httpx

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"


# ── Outbound ──────────────────────────────────────────────────────────────────

async def send_message(text: str, parse_mode: str = "Markdown"):
    """Send a message to your Telegram chat."""
    async with httpx.AsyncClient() as client:
        await client.post(
            f"{BASE_URL}/sendMessage",
            json={
                "chat_id": CHAT_ID,
                "text": text,
                "parse_mode": parse_mode,
            },
            timeout=15,
        )


# ── Inbound ───────────────────────────────────────────────────────────────────

async def handle_telegram_update(payload: dict):
    """
    Receives Telegram webhook payload.
    Ignores anyone who isn't you (CHAT_ID check).
    Passes message text to the AI coach and replies.
    """
    from coach.ai import chat

    message = payload.get("message") or payload.get("edited_message")
    if not message:
        return

    incoming_chat_id = str(message.get("chat", {}).get("id", ""))

    # Security: only respond to your own chat
    if incoming_chat_id != str(CHAT_ID):
        return

    text = (message.get("text") or "").strip()
    if not text:
        return

    # Handle /start command
    if text == "/start":
        await send_message(
            "Coach online 💪\nTell me what's on your schedule or ask me anything."
        )
        return

    # Typing indicator
    async with httpx.AsyncClient() as client:
        await client.post(
            f"{BASE_URL}/sendChatAction",
            json={"chat_id": CHAT_ID, "action": "typing"},
            timeout=5,
        )

    try:
        reply = await chat(text)
        await send_message(reply)
    except Exception as e:
        await send_message(f"⚠️ Something went wrong: {str(e)}")
