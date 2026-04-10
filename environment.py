"""
SQLFixEnv — Core Environment
An OpenEnv environment where AI agents fix broken SQL queries.
Real SQLite execution, dense partial rewards, 5 difficulty levels.
"""

import sqlite3
import textwrap
import uuid
from typing import Any


# ---------------------------------------------------------------------------
# Database setup — creates an in-memory SQLite DB with realistic schema
# ---------------------------------------------------------------------------

SCHEMA_SQL = """
CREATE TABLE employees (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    department TEXT NOT NULL,
    salary REAL NOT NULL,
    hire_date TEXT NOT NULL,
    manager_id INTEGER
);

CREATE TABLE departments (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    budget REAL NOT NULL,
    location TEXT NOT NULL
);

CREATE TABLE projects (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    department_id INTEGER NOT NULL,
    start_date TEXT NOT NULL,
    end_date TEXT,
    budget REAL NOT NULL
);

CREATE TABLE employee_projects (
    employee_id INTEGER NOT NULL,
    project_id INTEGER NOT NULL,
    role TEXT NOT NULL,
    hours_allocated INTEGER NOT NULL
);

INSERT INTO departments VALUES
    (1, 'Engineering', 500000, 'San Francisco'),
    (2, 'Marketing', 200000, 'New York'),
    (3, 'Sales', 300000, 'Chicago'),
    (4, 'HR', 150000, 'Austin');

INSERT INTO employees VALUES
    (1, 'Alice Johnson', 'Engineering', 95000, '2019-03-15', NULL),
    (2, 'Bob Smith', 'Engineering', 85000, '2020-07-01', 1),
    (3, 'Carol White', 'Marketing', 75000, '2018-11-20', NULL),
    (4, 'David Brown', 'Sales', 70000, '2021-01-10', NULL),
    (5, 'Eve Davis', 'Engineering', 90000, '2019-06-01', 1),
    (6, 'Frank Miller', 'HR', 65000, '2022-02-14', NULL),
    (7, 'Grace Wilson', 'Marketing', 80000, '2020-09-30', 3),
    (8, 'Henry Taylor', 'Sales', 72000, '2021-05-20', 4),
    (9, 'Iris Anderson', 'Engineering', 88000, '2020-03-01', 1),
    (10, 'Jack Thomas', 'Sales', 68000, '2022-08-15', 4);

INSERT INTO projects VALUES
    (1, 'Platform Rebuild', 1, '2023-01-01', '2023-12-31', 150000),
    (2, 'Marketing Campaign', 2, '2023-03-01', '2023-06-30', 50000),
    (3, 'Sales Automation', 3, '2023-02-01', NULL, 80000),
    (4, 'HR Portal', 4, '2023-04-01', '2023-09-30', 40000),
    (5, 'AI Integration', 1, '2023-06-01', NULL, 200000);

INSERT INTO employee_projects VALUES
    (1, 1, 'Lead', 40), (2, 1, 'Developer', 35),
    (5, 1, 'Developer', 30), (9, 1, 'Developer', 35),
    (1, 5, 'Lead', 20), (2, 5, 'Developer', 25),
    (3, 2, 'Lead', 40), (7, 2, 'Analyst', 30),
    (4, 3, 'Lead', 40), (8, 3, 'Analyst', 35),
    (6, 4, 'Lead', 40);
"""

EXPECTED_RESULTS = {
    "easy_syntax": [
        ("Engineering", 3), ("HR", 1), ("Marketing", 2), ("Sales", 3)
    ],
    "easy_filter": [
        (1, "Alice Johnson", "Engineering", 95000.0),
        (5, "Eve Davis", "Engineering", 90000.0),
        (9, "Iris Anderson", "Engineering", 88000.0),
    ],
    "medium_join": [
        ("Alice Johnson", "Platform Rebuild", "Lead"),
        ("Alice Johnson", "AI Integration", "Lead"),
        ("Bob Smith", "Platform Rebuild", "Developer"),
        ("Bob Smith", "AI Integration", "Developer"),
        ("Eve Davis", "Platform Rebuild", "Developer"),
        ("Iris Anderson", "Platform Rebuild", "Developer"),
        ("Iris Anderson", "AI Integration", None),  # flexible
    ],
    "medium_aggregate": [
        ("Engineering", 4, 89500.0),
        ("HR", 1, 65000.0),
        ("Marketing", 2, 77500.0),
        ("Sales", 3, 70000.0),
    ],
    "hard_subquery": [
        (1, "Alice Johnson", "Engineering", 95000.0),
        (5, "Eve Davis", "Engineering", 90000.0),
        (9, "Iris Anderson", "Engineering", 88000.0),
    ],
}


def _make_db() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.executescript(SCHEMA_SQL)
    return conn


# ---------------------------------------------------------------------------
# Task bank
# ---------------------------------------------------------------------------

TASKS: dict[str, dict[str, Any]] = {
    # ── EASY 1 — Syntax error ────────────────────────────────────────────
    "easy_syntax": {
        "difficulty": "easy",
        "description": (
            "Count the number of employees in each department. "
            "Return department name and count, ordered by department name. "
            "The query has a syntax error — fix it."
        ),
        "buggy_sql": textwrap.dedent("""\
            SELCT department, COUNT(*) as employee_count
            FROM employees
            GRUP BY department
            ORDER BY department;
        """),
        "error_hint": "Error: near 'SELCT': syntax error (SELCT should be SELECT, GRUP should be GROUP)",
        "expected_columns": ["department", "employee_count"],
        "expected_rows": 4,
    },

    # ── EASY 2 — Wrong filter ────────────────────────────────────────────
    "easy_filter": {
        "difficulty": "easy",
        "description": (
            "Find all employees in the Engineering department with salary above 85000. "
            "Return id, name, department, salary ordered by salary descending. "
            "The WHERE clause has the wrong condition — fix it."
        ),
        "buggy_sql": textwrap.dedent("""\
            SELECT id, name, department, salary
            FROM employees
            WHERE department = 'Engineering' AND salary < 85000
            ORDER BY salary DESC;
        """),
        "error_hint": "Query returns wrong rows — salary condition is reversed (< should be >)",
        "expected_columns": ["id", "name", "department", "salary"],
        "expected_rows": 3,
    },

    # ── MEDIUM 1 — Missing JOIN ───────────────────────────────────────────
    "medium_join": {
        "difficulty": "medium",
        "description": (
            "Find all Engineering employees and the projects they work on. "
            "Return employee name, project name, and their role. "
            "The JOIN is missing — fix it."
        ),
        "buggy_sql": textwrap.dedent("""\
            SELECT e.name, p.name as project_name, ep.role
            FROM employees e
            JOIN employee_projects ep ON e.id = ep.employee_id
            WHERE e.department = 'Engineering'
            ORDER BY e.name, p.name;
        """),
        "error_hint": "Error: no such column: p.name — missing JOIN to projects table",
        "expected_columns": ["name", "project_name", "role"],
        "expected_rows": 6,
    },

    # ── MEDIUM 2 — Wrong aggregation ─────────────────────────────────────
    "medium_aggregate": {
        "difficulty": "medium",
        "description": (
            "For each department, find the number of employees and average salary. "
            "Return department, employee_count, avg_salary ordered by department. "
            "The aggregation function is wrong — fix it."
        ),
        "buggy_sql": textwrap.dedent("""\
            SELECT department,
                   COUNT(*) as employee_count,
                   SUM(salary) as avg_salary
            FROM employees
            GROUP BY department
            ORDER BY department;
        """),
        "error_hint": "avg_salary is showing SUM instead of AVG — wrong aggregation function",
        "expected_columns": ["department", "employee_count", "avg_salary"],
        "expected_rows": 4,
    },

    # ── HARD — Subquery ───────────────────────────────────────────────────
    "hard_subquery": {
        "difficulty": "hard",
        "description": (
            "Find all employees whose salary is above the average salary of their department. "
            "Return id, name, department, salary ordered by salary descending. "
            "The subquery is referencing the wrong table — fix it."
        ),
        "buggy_sql": textwrap.dedent("""\
            SELECT e.id, e.name, e.department, e.salary
            FROM employees e
            WHERE e.salary > (
                SELECT AVG(salary)
                FROM departments
                WHERE name = e.department
            )
            ORDER BY e.salary DESC;
        """),
        "error_hint": "Subquery uses wrong table 'departments' — should use 'employees' to calculate avg salary per department",
        "expected_columns": ["id", "name", "department", "salary"],
        "expected_rows": 3,
    },
}


# ---------------------------------------------------------------------------
# Grader
# ---------------------------------------------------------------------------

def _safe_score(raw: float) -> float:
    """Map [0,1] strictly into (0.05, 0.95) — never 0.0 or 1.0."""
    return round(0.05 + raw * 0.90, 4)


def grade(task_id: str, fixed_sql: str) -> dict[str, Any]:
    task = TASKS.get(task_id)
    if task is None:
        return {"score": 0.05, "error": f"Unknown task '{task_id}'", "details": {}}

    conn = _make_db()
    try:
        cursor = conn.execute(fixed_sql)
        rows = cursor.fetchall()
        columns = [d[0] for d in cursor.description] if cursor.description else []
    except Exception as exc:
        conn.close()
        return {"score": 0.05, "error": f"SQL Error: {exc}", "details": {"rows": [], "columns": []}}
    finally:
        conn.close()

    checks = {}
    score_parts = []

    # Check 1: correct number of rows (25%)
    expected_rows = task["expected_rows"]
    row_ok = len(rows) == expected_rows
    checks["row_count"] = {"got": len(rows), "expected": expected_rows, "passed": row_ok}
    score_parts.append(0.25 if row_ok else 0.0)

    # Check 2: correct columns present (25%)
    expected_cols = [c.lower() for c in task["expected_columns"]]
    got_cols = [c.lower() for c in columns]
    cols_ok = all(ec in got_cols for ec in expected_cols)
    checks["columns"] = {"got": got_cols, "expected": expected_cols, "passed": cols_ok}
    score_parts.append(0.25 if cols_ok else 0.0)

    # Check 3: no SQL error (25%)
    checks["no_error"] = {"passed": True}
    score_parts.append(0.25)

    # Check 4: data correctness — spot check key values (25%)
    data_ok = False
    if rows and task_id in EXPECTED_RESULTS:
        expected = EXPECTED_RESULTS[task_id]
        # Check first row matches
        try:
            first_row = tuple(rows[0])
            first_expected = tuple(expected[0])
            data_ok = len(rows) == len(expected) and str(first_row[0]) == str(first_expected[0])
        except Exception:
            data_ok = False
    checks["data_correctness"] = {"passed": data_ok}
    score_parts.append(0.25 if data_ok else 0.0)

    raw_score = sum(score_parts)
    score = _safe_score(raw_score)

    return {
        "score": score,
        "error": None,
        "details": {
            "checks": checks,
            "rows_returned": len(rows),
            "sample_rows": [list(r) for r in rows[:3]],
            "columns": columns,
        },
    }


# ---------------------------------------------------------------------------
# Episode / Session
# ---------------------------------------------------------------------------

class Episode:
    MAX_ATTEMPTS = 5

    def __init__(self, task_id: str):
        self.episode_id = str(uuid.uuid4())
        self.task_id = task_id
        self.attempt = 0
        self.done = False
        self.best_score = 0.05
        self.history: list[dict] = []

    def observation(self) -> dict[str, Any]:
        task = TASKS[self.task_id]
        return {
            "task_id": self.task_id,
            "difficulty": task["difficulty"],
            "buggy_sql": task["buggy_sql"],
            "task_description": task["description"],
            "error_hint": task["error_hint"],
            "schema": "Tables: employees(id,name,department,salary,hire_date,manager_id), departments(id,name,budget,location), projects(id,name,department_id,start_date,end_date,budget), employee_projects(employee_id,project_id,role,hours_allocated)",
            "attempt": self.attempt,
            "max_attempts": self.MAX_ATTEMPTS,
        }

    def step(self, fixed_sql: str) -> dict[str, Any]:
        if self.done:
            return {"observation": self.observation(), "reward": 0.05, "done": True, "info": {}}
        self.attempt += 1
        result = grade(self.task_id, fixed_sql)
        score = result["score"]
        if score > self.best_score:
            self.best_score = score
        self.done = score >= 0.94 or self.attempt >= self.MAX_ATTEMPTS
        self.history.append({"attempt": self.attempt, "score": score, "error": result["error"]})
        return {
            "observation": self.observation(),
            "reward": score,
            "done": self.done,
            "info": {
                "grader_error": result["error"],
                "details": result["details"],
                "best_score": self.best_score,
            },
        }

    def state(self) -> dict[str, Any]:
        return {
            "episode_id": self.episode_id,
            "task_id": self.task_id,
            "attempt": self.attempt,
            "max_attempts": self.MAX_ATTEMPTS,
            "done": self.done,
            "best_score": self.best_score,
            "history": self.history,
        }


# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------

class SQLFixEnv:
    def __init__(self):
        self._sessions: dict[str, Episode] = {}

    def reset(self, task_id: str | None = None) -> dict[str, Any]:
        if task_id is None:
            task_id = "easy_syntax"
        if task_id not in TASKS:
            raise ValueError(f"Unknown task_id '{task_id}'. Valid: {list(TASKS)}")
        ep = Episode(task_id)
        self._sessions[ep.episode_id] = ep
        return {"session_id": ep.episode_id, "observation": ep.observation()}

    def step(self, session_id: str, fixed_sql: str) -> dict[str, Any]:
        ep = self._sessions.get(session_id)
        if ep is None:
            raise KeyError(f"session_id '{session_id}' not found.")
        return ep.step(fixed_sql)

    def state(self, session_id: str) -> dict[str, Any]:
        ep = self._sessions.get(session_id)
        if ep is None:
            raise KeyError(f"session_id '{session_id}' not found.")
        return ep.state()

    @staticmethod
    def list_tasks() -> list[dict[str, str]]:
        return [
            {"task_id": tid, "difficulty": t["difficulty"], "description": t["description"]}
            for tid, t in TASKS.items()
        ]
