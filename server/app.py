"""

SQLFixEnv FastAPI Server
OpenEnv-compatible REST API for the SQL Query Optimizer environment.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import sqlite3
import uvicorn

from environment import SQLFixEnv, SCHEMA_SQL

app = FastAPI(
    title="SQLFixEnv",
    description="Advanced SQL Query Optimizer RL Environment — Fix broken SQL queries across 5 difficulty levels with partial reward scoring.",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global env instance
env = SQLFixEnv()


class ResetRequest(BaseModel):
    task_id: Optional[int] = None


class StepRequest(BaseModel):
    action: str


@app.get("/")
def root():
    return {
        "name": "SQLFixEnv",
        "version": "2.0.0",
        "description": "SQL Query Optimizer RL Environment with 5 difficulty levels",
        "levels": ["easy", "medium", "hard", "expert", "master"],
        "total_tasks": len(env.tasks),
        "endpoints": ["/reset", "/step", "/tasks", "/schema", "/health"],
    }


@app.get("/health")
def health():
    return {"status": "ok", "tasks": len(env.tasks)}


@app.post("/reset")
def reset(req: ResetRequest = ResetRequest()):
    obs = env.reset(task_id=req.task_id)
    return obs


@app.post("/step")
def step(req: StepRequest):
    if not req.action or not req.action.strip():
        raise HTTPException(status_code=400, detail="Action (SQL query) cannot be empty.")
    result = env.step(req.action.strip())
    return result


@app.get("/tasks")
def get_tasks():
    return {"tasks": env.get_all_tasks(), "total": len(env.tasks)}


@app.get("/tasks/{task_id}")
def get_task(task_id: int):
    tasks = [t for t in env.get_all_tasks() if t["id"] == task_id]
    if not tasks:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found.")
    return tasks[0]


@app.get("/schema")
def get_schema():
    try:
        conn = sqlite3.connect(":memory:")
        conn.executescript(SCHEMA_SQL)
        cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [r[0] for r in cur.fetchall()]
        schema = {}
        for table in tables:
            cur2 = conn.execute(f"PRAGMA table_info({table})")
            schema[table] = [{"name": r[1], "type": r[2]} for r in cur2.fetchall()]
        conn.close()
        return {"schema": schema, "tables": list(schema.keys())}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/history")
def get_history():
    return {"history": env.history, "steps": env.steps, "total_reward": env.total_reward}


def main():
    uvicorn.run(app, host="0.0.0.0", port=7860)

if __name__ == '__main__':
    main() 
