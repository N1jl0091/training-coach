# AI Training Coach

A personal AI coach that lives in Telegram. Talks to GPT-4o, manages your Intervals.icu schedule, and auto-reviews Strava activities.

---

## Setup — do these steps in order

### 1. Intervals.icu
1. Sign up at [intervals.icu](https://intervals.icu) (free)
2. Connect Strava inside Intervals: **Settings → Connections → Strava** — this auto-syncs completed activities
3. Get your API credentials: **Settings → Developer**
   - Copy **API Key** → `INTERVALS_API_KEY`
   - Your Athlete ID is in your profile URL: `intervals.icu/athlete/XXXXX` → `INTERVALS_ATHLETE_ID`
4. **Outlook calendar sync (no code):**
   - In Intervals: **Settings → Calendar → copy iCal URL**
   - In Outlook: **Add Calendar → Subscribe from web → paste URL**

---

### 2. Strava API app
1. Go to [strava.com/settings/api](https://www.strava.com/settings/api)
2. Create an app — fill in any name/description, set **Website** to `http://localhost`
3. Copy **Client ID** → `STRAVA_CLIENT_ID`
4. Copy **Client Secret** → `STRAVA_CLIENT_SECRET`
5. Set **Authorization Callback Domain** to your Railway domain (fill this in after step 5)

---

### 3. Telegram bot
1. Open Telegram and message [@BotFather](https://t.me/BotFather)
2. Send `/newbot` → follow prompts → copy the **token** → `TELEGRAM_BOT_TOKEN`
3. Message your new bot once (just say hi)
4. Get your Chat ID — visit this URL in a browser (replace YOUR_TOKEN):
   ```
   https://api.telegram.org/botYOUR_TOKEN/getUpdates
   ```
   Find `"chat":{"id":XXXXXXX}` — that number is your `TELEGRAM_CHAT_ID`

---

### 4. OpenAI
1. Sign up at [platform.openai.com](https://platform.openai.com)
2. Add a payment method (Billing → Add payment method)
3. **Set a spend limit**: Billing → Limits → set $20/month max (this project uses ~$5-10/mo)
4. Create an API key → `OPENAI_API_KEY`

---

### 5. GitHub + Railway
1. Create a new GitHub repo named `training-coach`
2. Push this code:
   ```bash
   git init
   git add .
   git commit -m "init"
   git remote add origin https://github.com/YOUR_USERNAME/training-coach.git
   git push -u origin main
   ```
3. Sign up at [railway.app](https://railway.app) → **New Project → Deploy from GitHub repo** → pick `training-coach`
4. **Add a Volume**: In Railway → your service → Volumes → Add Volume → Mount path: `/data`
5. **Add all environment variables**: Railway → your service → Variables → add each one from `.env.example`
6. Copy your Railway public domain (Settings → Networking → Public domain) — looks like `training-coach-xxxx.up.railway.app`
7. Paste that domain into your Strava API app's **Authorization Callback Domain**

---

### 6. Connect Strava OAuth (one-time, after deploy)
Visit this URL in your browser:
```
https://your-railway-domain/strava-auth
```
Authorise the app. You'll be redirected back and see a success message. This stores your tokens in the database permanently (they auto-refresh).

---

### 7. Register the Strava webhook
Run this curl command once (replace placeholders):
```bash
curl -X POST https://www.strava.com/api/v3/push_subscriptions \
  -F client_id=YOUR_STRAVA_CLIENT_ID \
  -F client_secret=YOUR_STRAVA_CLIENT_SECRET \
  -F callback_url=https://your-railway-domain/strava-webhook \
  -F verify_token=YOUR_STRAVA_VERIFY_TOKEN
```
You should get back a subscription ID. That's it — webhook is live.

---

### 8. Register the Telegram webhook
Run this curl command once (replace placeholders):
```bash
curl "https://api.telegram.org/botYOUR_TELEGRAM_BOT_TOKEN/setWebhook?url=https://your-railway-domain/telegram-webhook"
```
You should get `{"ok":true,"result":true}`.

---

### 9. Edit your athlete profile
Open `coach/ai.py` and fill in the `ATHLETE_PROFILE` section with your real details. Commit and push — Railway auto-redeploys.

---

## You're live

- Message your Telegram bot to chat with your coach
- Complete a Strava activity — you'll get an automatic review in Telegram
- Your Intervals.icu workouts appear in Outlook via iCal

---

## File structure

```
training-coach/
├── main.py                  FastAPI app + all routes
├── requirements.txt
├── railway.toml             Deploy config
├── .env.example             Variable names (never commit .env)
├── .gitignore
│
├── coach/
│   ├── ai.py                GPT-4o, system prompt, tool execution
│   ├── memory.py            SQLite — messages + activities + tokens
│   └── tools.py             Tool schemas for function calling
│
├── integrations/
│   ├── intervals.py         Intervals.icu CRUD
│   └── strava.py            Webhook + OAuth + activity fetch
│
└── bot/
    └── telegram.py          Send + receive Telegram messages
```

---

## Troubleshooting

**Coach not responding in Telegram:** Check Railway logs. Verify `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` are set correctly.

**Strava webhook not firing:** Confirm the webhook is registered (`GET https://www.strava.com/api/v3/push_subscriptions?client_id=X&client_secret=Y`). Check Railway logs for incoming requests.

**"No Strava token" error:** Visit `/strava-auth` again to re-authorise.

**Activities not saving:** Check Railway volume is mounted at `/data`. Verify `DB_PATH=/data/coach.db` is set in Railway variables.

**Intervals API errors:** Double-check `INTERVALS_API_KEY` and `INTERVALS_ATHLETE_ID`. The athlete ID is the number in your intervals.icu profile URL.
