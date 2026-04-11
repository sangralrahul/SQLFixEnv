---
title: SQLDebugEnv
emoji: 🗄️
colorFrom: blue
colorTo: green
sdk: docker
pinned: false
tags:
  - openenv
---

# SQLDebugEnv 🗄️

> **Meta × PyTorch OpenEnv Hackathon submission**
> An OpenEnv environment where AI agents fix broken SQL queries against a real SQLite database.

## Overview

SQLDebugEnv presents an agent with broken SQL queries and challenges it to produce working fixes. Tasks range from simple syntax errors to complex subqueries.

## Tasks

| Task ID | Difficulty | Description |
|---|---|---|
| `easy_syntax` | Easy | Fix SELCT/GRUP syntax errors |
| `easy_filter` | Easy | Fix reversed WHERE condition |
| `medium_aggregate` | Medium | Fix SUM vs AVG aggregation |
| `medium_join` | Medium | Fix wrong JOIN condition |
| `hard_subquery` | Hard | Fix correlated subquery wrong table |

## API

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Liveness check |
| GET | `/tasks` | List all tasks |
| POST | `/reset` | Start new episode |
| POST | `/step` | Submit fixed SQL |
| GET | `/state/{session_id}` | Get episode state |

## Reward

Score = 0.05 to 0.95 based on 4 checks:
1. No SQL error (25%)
2. Correct row count (25%)
3. Correct columns (25%)
4. Data correctness (25%)

## Setup

```bash
pip install -r requirements.txt
uvicorn app:app --host 0.0.0.0 --port 7860
```
