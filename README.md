---
title: SQLFixEnv
emoji: 🗄️
colorFrom: indigo
colorTo: cyan
sdk: docker
pinned: false
tags:
  - openenv
---

# SQLFixEnv 🗄️

> **Meta × PyTorch OpenEnv Hackathon submission**
> An OpenEnv environment where AI agents learn to fix broken SQL queries against a real database.

---

## Overview

SQLFixEnv presents an agent with broken SQL queries and challenges it to produce working fixes against a real SQLite database. This environment models **automated SQL debugging** — a high-value enterprise task with direct real-world application for evaluating and training code-capable LLM agents.

**Why SQL debugging is great for RL:**
- **Dense partial rewards** — 4 independent correctness checks provide rich signal
- **Real execution feedback** — queries run against actual SQLite database
- **Iterative refinement** — agent sees exact errors and can improve
- **5 difficulty tiers** — natural curriculum from syntax → logic → joins → aggregates → subqueries

---

## Database Schema

```sql
employees(id, name, department, salary, hire_date, manager_id)
departments(id, name, budget, location)
projects(id, name, department_id, start_date, end_date, budget)
employee_projects(employee_id, project_id, role, hours_allocated)
```

---

## Tasks

| Task ID | Difficulty | Bug Type | Description |
|---|---|---|---|
| `easy_syntax` | Easy | Syntax error | Fix SELCT/GRUP typos in GROUP BY query |
| `easy_filter` | Easy | Logic bug | Fix reversed WHERE condition |
| `medium_join` | Medium | Missing JOIN | Add missing JOIN to projects table |
| `medium_aggregate` | Medium | Wrong function | Fix SUM → AVG aggregation |
| `hard_subquery` | Hard | Wrong table | Fix correlated subquery referencing wrong table |

### Reward Design

Each query is graded on 4 independent checks (25% each):
1. **Row count** — correct number of rows returned
2. **Columns** — correct column names present
3. **No error** — query executes without SQL errors
4. **Data correctness** — spot-check key values match expected

Score range: **0.05 – 0.95** (strictly between 0 and 1)

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Liveness check |
| `GET` | `/tasks` | List all tasks |
| `POST` | `/reset` | Start new episode |
| `POST` | `/step` | Submit fixed SQL |
| `GET` | `/state/{session_id}` | Get episode state |

### Example

```bash
# Reset
curl -X POST https://sangralrahul-sqlfixenv.hf.space/reset \
  -H "Content-Type: application/json" \
  -d '{"task_id": "easy_syntax"}'

# Step
curl -X POST https://sangralrahul-sqlfixenv.hf.space/step \
  -H "Content-Type: application/json" \
  -d '{"session_id": "<id>", "fixed_sql": "SELECT department, COUNT(*) as employee_count FROM employees GROUP BY department ORDER BY department;"}'
```

---

## Setup

```bash
# Docker
docker build -t sql-fix-env .
docker run -p 7860:7860 sql-fix-env

# Local
pip install -r requirements.txt
uvicorn app:app --host 0.0.0.0 --port 7860
```

## Inference

```bash
export API_BASE_URL="https://api-inference.huggingface.co/v1"
export MODEL_NAME="meta-llama/Meta-Llama-3-8B-Instruct"
export HF_TOKEN="hf_..."
export ENV_URL="http://localhost:7860"
python inference.py
```
