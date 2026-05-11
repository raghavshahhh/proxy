#!/usr/bin/env python3
"""
COST TRACKER - March 2026
Tracks API usage and costs per session
"""

import json
from datetime import datetime
from pathlib import Path

COST_FILE = Path.home() / ".claude" / "telemetry" / "costs.json"

# March 2026 rates (per 1K tokens)
RATES = {
    "claude-haiku-4-5": {"input": 0.25, "output": 1.25},
    "claude-sonnet-4-6": {"input": 3.00, "output": 15.00},
    "claude-opus-4-6": {"input": 15.00, "output": 75.00},
}


class CostTracker:
    def __init__(self):
        self.sessions = []
        self.load()

    def load(self):
        if COST_FILE.exists():
            with open(COST_FILE) as f:
                data = json.load(f)
                self.sessions = data.get("sessions", [])

    def save(self):
        with open(COST_FILE, "w") as f:
            json.dump(
                {"sessions": self.sessions, "last_updated": datetime.now().isoformat()},
                f,
                indent=2,
            )

    def log_interaction(
        self, model: str, input_tokens: int, output_tokens: int, task: str
    ):
        """Log a single API call"""
        if model not in RATES:
            return

        rate = RATES[model]
        input_cost = (input_tokens / 1000) * rate["input"]
        output_cost = (output_tokens / 1000) * rate["output"]
        total = input_cost + output_cost

        entry = {
            "timestamp": datetime.now().isoformat(),
            "model": model,
            "task": task[:50],  # Truncate long tasks
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost_usd": round(total, 4),
        }

        self.sessions.append(entry)
        self.save()
        return entry

    def get_summary(self):
        """Get cost summary"""
        if not self.sessions:
            return "No sessions tracked yet"

        total_cost = sum(s["cost_usd"] for s in self.sessions)
        today = [
            s
            for s in self.sessions
            if s["timestamp"].startswith(datetime.now().strftime("%Y-%m-%d"))
        ]
        today_cost = sum(s["cost_usd"] for s in today)

        return {
            "total_cost_usd": round(total_cost, 2),
            "total_sessions": len(self.sessions),
            "today_cost_usd": round(today_cost, 2),
            "today_calls": len(today),
        }


if __name__ == "__main__":
    tracker = CostTracker()
    print(json.dumps(tracker.get_summary(), indent=2))
