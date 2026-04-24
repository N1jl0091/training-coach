import os
import json
from openai import AsyncOpenAI
from coach.memory import save_message, get_recent_messages
from coach.tools import TOOL_SCHEMAS
import integrations.intervals as intervals

client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# ══════════════════════════════════════════════════════════════════════════════
#  EDIT THIS SECTION — your personal athlete profile
#  The AI coach reads this every conversation. Be specific.
# ══════════════════════════════════════════════════════════════════════════════

ATHLETE_PROFILE = """
Name: [YOUR NAME]
Age: [YOUR AGE]
Location: [YOUR CITY / COUNTRY]

Sports: [e.g. Running, Cycling, Swimming, Football/Soccer]
Current weekly volume: [e.g. Running ~40km, Cycling ~3hrs, Swimming ~2km]
Experience: [e.g. 4 years running, 2 years cycling, beginner swimming]

Main goal: [e.g. Olympic triathlon in under 2:30 by October 2025]
Secondary goals: [e.g. sub-45min 10km, maintain cycling base]

Training zones (if known):
  - Zone 2 / aerobic base: [e.g. HR < 145bpm]
  - Threshold: [e.g. HR ~165bpm, pace ~4:45/km]
  - VO2max: [e.g. HR > 175bpm]

Injuries / limitations: [e.g. Left knee — avoid back-to-back hard run days]
Preferred rest day: [e.g. Sunday]
Usual training days: [e.g. Mon/Tue/Thu/Sat]
Work schedule notes: [e.g. Very busy Mon-Fri mornings, sessions must be under 1hr on weekdays]

Equipment:
  - Bike: [e.g. Road bike with power meter]
  - Watch: [e.g. Garmin Forerunner 955]
  - Pool access: [e.g. Yes, 25m lane, available weekday evenings]

Other notes: [e.g. Plays 5-a-side football on random Wednesday evenings, needs to flag these]
"""

SYSTEM_PROMPT = f"""You are a personal endurance coach. You are direct, specific, and practical.
You know your athlete well, remember previous conversations, and have full access to their Intervals.icu training calendar.

Athlete profile:
{ATHLETE_PROFILE}

Behaviour rules:
- Keep all responses concise. No fluff or filler.
- When the athlete asks you to create, move, edit, or delete workouts — do it immediately using the tools. Do not ask for confirmation unless something is genuinely ambiguous.
- To move a workout, use list_workouts to find the ID then update_workout with the new start_date_local.
- When reviewing activities, reference the actual numbers (pace, HR, power, distance). Identify one thing that went well and one coaching observation.
- If the athlete mentions something like soccer practice or a social event, help them shuffle the training week around it without fuss.
- Never lecture. If they ask a question, answer it directly.
- Dates are always in YYYY-MM-DD format when calling tools.
"""

# ══════════════════════════════════════════════════════════════════════════════


async def chat(user_message: str) -> str:
    """Main chat handler. Saves message, calls GPT-4o with tools, returns reply."""
    save_message("user", user_message)
    history = get_recent_messages(30)
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + history

    response = await client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        tools=TOOL_SCHEMAS,
        tool_choice="auto",
    )

    msg = response.choices[0].message

    # Tool call loop — keeps going until the model has no more tool calls
    while msg.tool_calls:
        messages.append(msg)
        tool_results = []
        for tc in msg.tool_calls:
            result = await _run_tool(tc.function.name, json.loads(tc.function.arguments))
            tool_results.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": json.dumps(result),
            })
        messages.extend(tool_results)
        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            tools=TOOL_SCHEMAS,
            tool_choice="auto",
        )
        msg = response.choices[0].message

    reply = msg.content or "Done."
    save_message("assistant", reply)
    return reply


async def generate_activity_review(activity: dict) -> str:
    """Called automatically when Strava webhook fires. Returns formatted Telegram message."""
    sport = activity.get("sport_type", activity.get("type", "Activity"))
    name = activity.get("name", "Activity")
    distance_m = activity.get("distance", 0)
    distance_km = round(distance_m / 1000, 2) if distance_m else None
    moving_time_s = activity.get("moving_time", 0)
    duration_min = round(moving_time_s / 60, 1) if moving_time_s else None
    avg_hr = activity.get("average_heartrate")
    max_hr = activity.get("max_heartrate")
    avg_watts = activity.get("average_watts")
    elevation = activity.get("total_elevation_gain")
    suffer_score = activity.get("suffer_score")
    perceived_exertion = activity.get("perceived_exertion")

    # Pace for runs
    avg_pace = None
    if sport in ("Run", "VirtualRun") and distance_m and moving_time_s:
        secs_per_km = moving_time_s / (distance_m / 1000)
        avg_pace = f"{int(secs_per_km // 60)}:{int(secs_per_km % 60):02d}/km"

    # Build summary string for the AI
    summary_parts = [f"{sport}: {name}"]
    if distance_km:
        summary_parts.append(f"Distance: {distance_km}km")
    if duration_min:
        summary_parts.append(f"Duration: {duration_min}min")
    if avg_pace:
        summary_parts.append(f"Avg pace: {avg_pace}")
    if avg_watts:
        summary_parts.append(f"Avg power: {avg_watts}W")
    if avg_hr:
        summary_parts.append(f"Avg HR: {avg_hr}bpm")
    if max_hr:
        summary_parts.append(f"Max HR: {max_hr}bpm")
    if elevation:
        summary_parts.append(f"Elevation: {elevation}m")
    if suffer_score:
        summary_parts.append(f"Suffer score: {suffer_score}")
    if perceived_exertion:
        summary_parts.append(f"RPE: {perceived_exertion}/10")

    summary_str = " | ".join(summary_parts)

    prompt = (
        f"The athlete just completed this activity. Write a short coaching review — 3 to 5 sentences max. "
        f"Be specific about the numbers. Note what looks good and one actionable observation.\n\n"
        f"{summary_str}"
    )

    response = await client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        max_tokens=300,
    )

    review = response.choices[0].message.content

    # Format the Telegram message
    header = f"🏅 *{name}*\n_{summary_str}_\n\n"
    return header + review


# ── Tool executor ─────────────────────────────────────────────────────────────

async def _run_tool(name: str, args: dict) -> dict:
    try:
        if name == "list_workouts":
            return await intervals.list_workouts(args["start_date"], args["end_date"])
        elif name == "create_workout":
            return await intervals.create_workout(
                date=args["date"],
                name=args["name"],
                description=args.get("description", ""),
                sport_type=args["sport_type"],
                duration_seconds=args.get("duration_seconds"),
            )
        elif name == "update_workout":
            return await intervals.update_workout(args["event_id"], args["data"])
        elif name == "delete_workout":
            return await intervals.delete_workout(args["event_id"])
        else:
            return {"error": f"Unknown tool: {name}"}
    except Exception as e:
        return {"error": str(e)}
