TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "list_workouts",
            "description": (
                "List planned workouts from Intervals.icu between two dates. "
                "Always call this first before editing, deleting, or shifting a workout "
                "so you can find the correct event ID."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "start_date": {
                        "type": "string",
                        "description": "Start date YYYY-MM-DD",
                    },
                    "end_date": {
                        "type": "string",
                        "description": "End date YYYY-MM-DD",
                    },
                },
                "required": ["start_date", "end_date"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_workout",
            "description": "Create a new planned workout in Intervals.icu on a specific date.",
            "parameters": {
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "Date YYYY-MM-DD",
                    },
                    "name": {
                        "type": "string",
                        "description": "Workout name e.g. 'Easy 10km run' or '45min threshold bike'",
                    },
                    "description": {
                        "type": "string",
                        "description": "Full workout instructions and structure",
                    },
                    "sport_type": {
                        "type": "string",
                        "enum": ["Run", "Ride", "Swim", "WeightTraining", "Workout"],
                        "description": "Sport type",
                    },
                    "duration_seconds": {
                        "type": "integer",
                        "description": "Planned duration in seconds (optional)",
                    },
                },
                "required": ["date", "name", "sport_type"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_workout",
            "description": (
                "Edit an existing planned workout in Intervals.icu. "
                "Use list_workouts first to get the event ID. "
                "To shift a workout to a different date, update start_date_local."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "event_id": {
                        "type": "string",
                        "description": "The Intervals.icu event ID (from list_workouts)",
                    },
                    "data": {
                        "type": "object",
                        "description": (
                            "Fields to update. Common fields: "
                            "name (string), description (string), "
                            "start_date_local (YYYY-MM-DD to move the workout), "
                            "moving_time (integer seconds)"
                        ),
                    },
                },
                "required": ["event_id", "data"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete_workout",
            "description": (
                "Delete a planned workout from Intervals.icu permanently. "
                "Use list_workouts first to confirm the correct event ID."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "event_id": {
                        "type": "string",
                        "description": "The Intervals.icu event ID to delete",
                    },
                },
                "required": ["event_id"],
            },
        },
    },
]
