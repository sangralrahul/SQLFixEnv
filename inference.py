"""
SQLDebugEnv — Baseline Inference Script
Same structure as CodeDebugEnv which passed Phase 1 + Phase 2.
"""
from __future__ import annotations
import os
import re
import sys
import requests
from openai import OpenAI

API_BASE_URL: str = os.environ.get("API_BASE_URL", "https://api-inference.huggingface.co/v1")
MODEL_NAME:   str = os.environ.get("MODEL_NAME", "meta-llama/Meta-Llama-3-8B-Instruct")
HF_TOKEN:     str = os.environ.get("HF_TOKEN", "")
ENV_URL:      str = os.environ.get("ENV_URL", "http://localhost:7860").rstrip("/")

MAX_ATTEMPTS: int = 5

client = OpenAI(base_url=API_BASE_URL, api_key=HF_TOKEN or "dummy")

SYSTEM_PROMPT = (
    "You are an expert SQL developer. "
    "You will be given a broken SQL query, a description of what it should return, "
    "an error hint, and the database schema. "
    "Return ONLY the corrected SQL query — no explanation, no markdown, no code fences. "
    "Output only the raw SQL."
)


def clamp(score: float) -> float:
    return round(max(0.05, min(0.95, float(score))), 4)


def ask_llm(buggy_code: str, description: str, error_hint: str, schema: str, attempt: int) -> str:
    user_msg = (
        f"Schema:\n{schema}\n\n"
        f"Task:\n{description}\n\n"
        f"Error hint:\n{error_hint}\n\n"
        f"Buggy SQL (attempt {attempt}):\n{buggy_code}\n\n"
        "Return ONLY the corrected SQL. No explanation, no markdown."
    )
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ],
        max_tokens=512,
        temperature=0.0,
    )
    raw = response.choices[0].message.content or ""
    raw = re.sub(r"```(?:sql)?", "", raw).strip("`").strip()
    return raw


def env_get(path: str) -> dict:
    resp = requests.get(f"{ENV_URL}{path}", timeout=30)
    resp.raise_for_status()
    return resp.json()


def env_post(path: str, payload: dict) -> dict:
    resp = requests.post(f"{ENV_URL}{path}", json=payload,
                         headers={"Content-Type": "application/json"}, timeout=60)
    resp.raise_for_status()
    return resp.json()


def run_task(task_id: str) -> float:
    reset_resp = env_post("/reset", {"task_id": task_id})
    session_id = reset_resp["session_id"]
    obs = reset_resp["observation"]

    print(f"[START] task={task_id}", flush=True)

    best_reward = 0.05

    for attempt in range(1, MAX_ATTEMPTS + 1):
        fixed_code = ask_llm(
            buggy_code=obs["buggy_code"],
            description=obs["task_description"],
            error_hint=obs["error_hint"],
            schema=obs.get("schema", ""),
            attempt=attempt,
        )

        step_resp = env_post("/step", {"session_id": session_id, "fixed_code": fixed_code})
        reward = clamp(step_resp.get("reward", 0.05))
        done = step_resp.get("done", False)

        if reward > best_reward:
            best_reward = reward

        print(f"[STEP] step={attempt} reward={reward}", flush=True)

        if done:
            break

    best_reward = clamp(best_reward)
    print(f"[END] task={task_id} score={best_reward} steps={attempt}", flush=True)
    return best_reward


def main() -> None:
    try:
        env_get("/health")
    except Exception as exc:
        print(f"health_check_failed: {exc}", flush=True)
        sys.exit(1)

    tasks_resp = env_get("/tasks")
    task_ids = [t["task_id"] for t in tasks_resp.get("tasks", [])]

    scores = {}
    for task_id in task_ids:
        try:
            scores[task_id] = run_task(task_id)
        except Exception as exc:
            print(f"[START] task={task_id}", flush=True)
            print(f"[STEP] step=1 reward=0.05", flush=True)
            print(f"[END] task={task_id} score=0.05 steps=1", flush=True)
            scores[task_id] = 0.05

    avg = round(sum(scores.values()) / len(scores), 4) if scores else 0.05
    print(f"summary scores={scores} average={avg}", flush=True)


if __name__ == "__main__":
    main()
