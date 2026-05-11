#!/usr/bin/env python3
"""
MODEL ROUTER - March 2026
Auto-selects model based on task complexity
"""

import json
import sys


def route_task(task_description: str) -> dict:
    """Route task to appropriate model"""

    task_lower = task_description.lower()

    # Pattern matching for complexity
    simple_tasks = ["summarize", "explain", "review", "check", "find", "list"]
    complex_tasks = ["architect", "design", "refactor", "debug", "optimize", "plan"]
    deep_tasks = ["analyze", "research", "theory", "strategy", "decision"]

    scores = {"haiku": 0, "sonnet": 0, "opus": 0}

    for word in simple_tasks:
        if word in task_lower:
            scores["haiku"] += 1

    for word in complex_tasks:
        if word in task_lower:
            scores["sonnet"] += 1

    for word in deep_tasks:
        if word in task_lower:
            scores["opus"] += 1

    # Decision logic
    if scores["opus"] > 0:
        return {
            "model": "claude-opus-4-6",
            "reason": "Deep reasoning required",
            "cost": "high",
        }
    elif scores["sonnet"] > scores["haiku"]:
        return {"model": "claude-sonnet-4-6", "reason": "Coding task", "cost": "medium"}
    else:
        return {"model": "claude-haiku-4-5", "reason": "Lightweight", "cost": "low"}


if __name__ == "__main__":
    task = sys.argv[1] if len(sys.argv) > 1 else "code review"
    result = route_task(task)
    print(json.dumps(result, indent=2))
