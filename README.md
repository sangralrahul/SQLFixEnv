---
title: SQLFixEnv
emoji: 🗄️
colorFrom: blue
colorTo: green
sdk: docker
pinned: true
license: mit
short_description: Advanced SQL Query Optimizer RL Environment — 5 difficulty levels
---

# 🗄️ SQLFixEnv — SQL Query Optimizer RL Environment

> **Fix broken SQL queries. Train smarter agents. Master 5 difficulty levels.**

[![HuggingFace Space](https://img.shields.io/badge/🤗-Live%20Demo-yellow)](https://huggingface.co/spaces/SANGRALRAHUL/SQLFixEnv)
[![GitHub](https://img.shields.io/badge/GitHub-SQLFixEnv-black)](https://github.com/sangralrahul/SQLFixEnv)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## 🎯 What is SQLFixEnv?

SQLFixEnv is an **OpenEnv-compatible reinforcement learning environment** where AI agents learn to fix broken SQL queries against a real multi-table SQLite database.

Unlike simple code-fixing environments, SQLFixEnv features:
- **5 progressive difficulty levels** — from easy typos to complex window functions
- **Partial reward scoring** — agents get credit for partially correct solutions
- **5-table relational database** — employees, departments, projects, assignments, salaries
- **Multi-dimensional rewards** — syntax correctness + result accuracy + column matching
- **Real-world enterprise SQL** — JOINs, subqueries, CTEs, window functions

---

## 🏗️ Database Schema

```
employees    ──┐
               ├── departments
assignments  ──┤
               ├── projects
salaries     ──┘
```

| Table | Rows | Key Columns |
|-------|------|-------------|
| employees | 10 | id, name, department_id, salary, hire_date |
| departments | 5 | id, name, budget, location |
| projects | 5 | id, name, department_id, budget |
| assignments | 11 | employee_id, project_id, role, hours_allocated |
| salaries | 10 | employee_id, amount, bonus, effective_date |

---

## 🎮 Difficulty Levels

| Level | Tasks | Skills Tested |
|-------|-------|--------------|
| 🟢 Easy | 2 | Keyword typos (SELECT, FROM, ORDER BY) |
| 🟡 Medium | 2 | WHERE, GROUP BY, HAVING, aggregations |
| 🟠 Hard | 2 | Multi-table JOINs, table/column name errors |
| 🔴 Expert | 2 | Subqueries, complex multi-joins |
| ⚫ Master | 2 | CTEs, window functions, PARTITION BY |

---

## 🏆 Reward System

```
Total Reward = Syntax (0.5) + Row Match (0.3) + Column Match (0.2)
```

| Component | Weight | Condition |
|-----------|--------|-----------|
| Syntax | 0.5 | Query executes without error |
| Row Match | 0.3 | Result rows match exactly (0.2 if unordered, partial for overlap) |
| Column Match | 0.2 | Output columns match exactly (partial for overlap) |

**Partial credit** is awarded at every stage — agents learn progressively.

---

## 🚀 Quick Start

### Reset Environment
```bash
curl -X POST https://SANGRALRAHUL-sqlfixenv.hf.space/reset \
  -H "Content-Type: application/json" \
  -d '{"task_id": 1}'
```

**Response:**
```json
{
  "task_id": 1,
  "level": "easy",
  "description": "Fix the query to get all employee names and salaries...",
  "broken_query": "SELCT name, salaray FROM employes ORDER BY salaray DESK",
  "hint": "Check spelling of SELECT, column names, table name, and DESC keyword.",
  "observation": "Fix this SQL query:\nSELCT name, salaray FROM employes ORDER BY salaray DESK"
}
```

### Submit a Fix
```bash
curl -X POST https://SANGRALRAHUL-sqlfixenv.hf.space/step \
  -H "Content-Type: application/json" \
  -d '{"action": "SELECT name, salary FROM employees ORDER BY salary DESC"}'
```

**Response:**
```json
{
  "task_id": 1,
  "level": "easy",
  "reward": 1.0,
  "reward_breakdown": {"syntax": 0.5, "rows": 0.3, "columns": 0.2},
  "feedback": "Perfect!",
  "success": true,
  "done": true
}
```

### Get All Tasks
```bash
curl https://SANGRALRAHUL-sqlfixenv.hf.space/tasks
```

### Get Database Schema
```bash
curl https://SANGRALRAHUL-sqlfixenv.hf.space/schema
```

---

## 🤖 Python Agent Example

```python
import requests

BASE = "https://SANGRALRAHUL-sqlfixenv.hf.space"

# Start episode on master-level task
obs = requests.post(f"{BASE}/reset", json={"task_id": 9}).json()
print(f"Level: {obs['level']}")
print(f"Broken: {obs['broken_query']}")

# Submit fixed query
result = requests.post(f"{BASE}/step", json={
    "action": "WITH ranked AS (SELECT name, salary, department_id, RANK() OVER (PARTITION BY department_id ORDER BY salary DESC) as rnk FROM employees) SELECT * FROM ranked WHERE rnk <= 2"
}).json()

print(f"Reward: {result['reward']}")  # 1.0
print(f"Success: {result['success']}")  # True
```

---

## 📡 API Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/reset` | POST | Start new episode (optional task_id 1-10) |
| `/step` | POST | Submit SQL fix, get reward |
| `/tasks` | GET | List all 10 tasks |
| `/tasks/{id}` | GET | Get specific task |
| `/schema` | GET | Full database schema |
| `/history` | GET | Episode history & total reward |
| `/health` | GET | Health check |

---

## 🧠 Why SQLFixEnv?

SQL debugging is a **$50B+ enterprise problem**. Companies spend enormous resources on:
- Fixing broken queries in production databases
- Training junior developers to write correct SQL
- Automated query optimization and repair

SQLFixEnv trains AI agents to solve this real-world challenge using reinforcement learning with dense, multi-dimensional rewards.

---

## 📁 Project Structure

```
SQLFixEnv/
├── environment.py    # Core RL environment (tasks, rewards, DB)
├── app.py           # FastAPI REST server
├── inference.py     # Agent demo & benchmark script
├── openenv.yaml     # OpenEnv specification
├── Dockerfile       # Container configuration
├── requirements.txt # Python dependencies
└── README.md        # This file
```

---

## 🛠️ Built With

- **FastAPI** — High-performance REST API
- **SQLite** — In-memory relational database
- **Python 3.11** — Core language
- **Docker** — Containerized deployment
- **OpenEnv** — Standard RL environment spec

---

*Built for Meta × HuggingFace PyTorch Hackathon 2025 by [@SANGRALRAHUL](https://huggingface.co/SANGRALRAHUL)*
