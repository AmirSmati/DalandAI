SCHEDULE_FOLLOWUP_TOOL = {
    "type": "function",
    "function": {
        "name": "schedule_followup",
        "description": (
            "Schedule another agent task to be executed after the current "
            "task. Use this when additional work should be performed later "
            "as a separate task."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "task": {
                    "type": "string",
                    "description": "The task that should be executed later.",
                }
            },
            "required": ["task"],
        },
    },
}