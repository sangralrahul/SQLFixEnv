"""
SQLFixEnv Inference Script
Demonstrates how an RL agent interacts with the SQLFixEnv environment.
"""
import os
import requests
import json
from openai import OpenAI

API_BASE_URL = os.getenv("API_BASE_URL", "https://sangralrahul-sqlfixenv.hf.space")
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4o-mini")
HF_TOKEN = os.getenv("HF_TOKEN")

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", HF_TOKEN))

def run_full_benchmark():
    tasks = requests.get(f"{API_BASE_URL}/tasks").json()["tasks"]
    total = 0.0
    results = []
    print("START")
    for task in tasks:
        obs = requests.post(f"{API_BASE_URL}/reset", json={"task_id": task["id"]}).json()
        print(f"STEP task_id={task['id']} level={task['level']}")
        result = requests.post(f"{API_BASE_URL}/step", json={"action": obs["broken_query"]}).json()
        total += result["reward"]
        results.append({
            "task_id": task["id"],
            "level": task["level"],
            "reward": result["reward"],
            "success": result["success"],
        })
    print(f"END total={total:.3f}")
    return results

if __name__ == '__main__':
    run_full_benchmark()