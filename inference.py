"""
SQLFixEnv Inference Script
Demonstrates how an RL agent interacts with the SQLFixEnv environment.
"""

import requests
import json

BASE_URL = "http://localhost:7860"


def run_episode(task_id: int = None, agent_query: str = None):
    """Run a single episode against the environment."""

    # Reset
    reset_payload = {"task_id": task_id} if task_id else {}
    obs = requests.post(f"{BASE_URL}/reset", json=reset_payload).json()

    print(f"\n{'='*60}")
    print(f"Task {obs['task_id']} | Level: {obs['level'].upper()}")
    print(f"Description: {obs['description']}")
    print(f"Broken Query: {obs['broken_query']}")
    print(f"Hint: {obs['hint']}")
    print(f"{'='*60}")

    # Step with agent action
    action = agent_query or obs["broken_query"]  # naive baseline: submit as-is
    result = requests.post(f"{BASE_URL}/step", json={"action": action}).json()

    print(f"\nAgent Query: {action}")
    print(f"Reward: {result['reward']} / 1.0")
    print(f"Breakdown: {json.dumps(result['reward_breakdown'], indent=2)}")
    print(f"Feedback: {result['feedback']}")
    print(f"Success: {result['success']}")

    return result


def run_full_benchmark():
    """Run all 10 tasks and report total score."""
    tasks = requests.get(f"{BASE_URL}/tasks").json()["tasks"]
    total = 0.0
    results = []

    print("\n🏆 SQLFixEnv Full Benchmark\n")

    for task in tasks:
        obs = requests.post(f"{BASE_URL}/reset", json={"task_id": task["id"]}).json()
        # Submit correct query as the "perfect agent"
        correct = requests.get(f"{BASE_URL}/tasks/{task['id']}").json()

        # For demo: agent submits broken query (baseline)
        result = requests.post(f"{BASE_URL}/step", json={"action": obs["broken_query"]}).json()
        total += result["reward"]
        results.append({
            "task_id": task["id"],
            "level": task["level"],
            "reward": result["reward"],
            "success": result["success"],
        })
        print(f"  Task {task['id']} ({task['level']:8s}): reward={result['reward']:.3f} | {'✅' if result['success'] else '❌'}")

    print(f"\n  Total Score: {total:.3f} / {len(tasks):.1f}")
    print(f"  Accuracy: {total/len(tasks)*100:.1f}%")
    return results


if __name__ == "__main__":
    print("SQLFixEnv Inference Demo")
    print("Running baseline agent (submits broken queries as-is)...")
    run_full_benchmark()
