"""
SQLDebugEnv — Core Environment
An OpenEnv environment where AI agents fix broken SQL queries.
Uses the same structure as CodeDebugEnv which passed Phase 1 + Phase 2.
"""

import sqlite3
import textwrap
import uuid
from typing import Any


# ---------------------------------------------------------------------------
# Database setup
# ---------------------------------------------------------------------------

SCHEMA_SQL = """
CREATE TABLE employees (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    department TEXT NOT NULL,
    salary REAL NOT NULL,
    hire_date TEXT NOT NULL
);
CREATE TABLE departments (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    budget REAL NOT NULL
);
CREATE TABLE projects (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    department_id INTEGER NOT NULL,
    budget REAL NOT NULL
);
INSERT INTO departments VALUES (1,'Engineering',500000),(2,'Marketing',200000),(3,'Sales',300000);
INSERT INTO employees VALUES
    (1,'Alice','Engineering',95000,'2019-03-15'),
    (2,'Bob','Engineering',85000,'2020-07-01'),
    (3,'Carol','Marketing',75000,'2018-11-20'),
    (4,'David','Sales',70000,'2021-01-10'),
    (5,'Eve','Engineering',90000,'2019-06-01'),
    (6,'Frank','Marketing',80000,'2020-09-30'),
    (7,'Grace','Sales',72000,'2021-05-20');
INSERT INTO projects VALUES
    (1,'Platform Rebuild',1,150000),
    (2,'Marketing Campaign',2,50000),
    (3,'Sales Automation',3,80000);
"""


def _make_db():
    conn = sqlite3.connect(":memory:")
    conn.executescript(SCHEMA_SQL)
    return conn


def _safe_score(passed: int, total: int) -> float:
    if total == 0:
        return 0.5
    raw = passed / total
    return round(0.05 + raw * 0.90, 4)


# ---------------------------------------------------------------------------
# Task bank
# ---------------------------------------------------------------------------

TASKS: dict[str, dict[str, Any]] = {
    "easy_syntax": {
        "difficulty": "easy",
        "description": (
            "Fix the SQL query to count employees per department. "
            "Return department name and count ordered by department name. "
            "The query has a syntax error — fix it."
        ),
        "buggy_code": textwrap.dedent("""\
            SELCT department, COUNT(*) as employee_count
            FROM employees
            GRUP BY department
            ORDER BY department;
        """),
        "error_hint": "SyntaxError: 'SELCT' should be 'SELECT', 'GRUP' should be 'GROUP'",
        "expected_rows": 3,
        "expected_cols": ["department", "employee_count"],
        "correct_sql": "SELECT department, COUNT(*) as employee_count FROM employees GROUP BY department ORDER BY department;",
    },
    "easy_filter": {
        "difficulty": "easy",
        "description": (
            "Fix the SQL query to find Engineering employees with salary above 85000. "
            "Return id, name, salary ordered by salary descending. "
            "The WHERE condition is wrong — fix it."
        ),
        "buggy_code": textwrap.dedent("""\
            SELECT id, name, salary
            FROM employees
            WHERE department = 'Engineering' AND salary < 85000
            ORDER BY salary DESC;
        """),
        "error_hint": "Wrong condition: salary < 85000 should be salary > 85000",
        "expected_rows": 2,
        "expected_cols": ["id", "name", "salary"],
        "correct_sql": "SELECT id, name, salary FROM employees WHERE department = 'Engineering' AND salary > 85000 ORDER BY salary DESC;",
    },
    "medium_aggregate": {
        "difficulty": "medium",
        "description": (
            "Fix the SQL query to get each department's employee count and average salary. "
            "Return department, employee_count, avg_salary ordered by department. "
            "The wrong aggregation function is used — fix it."
        ),
        "buggy_code": textwrap.dedent("""\
            SELECT department,
                   COUNT(*) as employee_count,
                   SUM(salary) as avg_salary
            FROM employees
            GROUP BY department
            ORDER BY department;
        """),
        "error_hint": "Wrong function: SUM(salary) should be AVG(salary) for avg_salary",
        "expected_rows": 3,
        "expected_cols": ["department", "employee_count", "avg_salary"],
        "correct_sql": "SELECT department, COUNT(*) as employee_count, AVG(salary) as avg_salary FROM employees GROUP BY department ORDER BY department;",
    },
    "medium_join": {
        "difficulty": "medium",
        "description": (
            "Fix the SQL query to get each department name and its total budget from departments table. "
            "Return department name and budget ordered by budget descending. "
            "The JOIN condition is wrong — fix it."
        ),
        "buggy_code": textwrap.dedent("""\
            SELECT e.department, d.budget
            FROM employees e
            JOIN departments d ON e.department = d.budget
            GROUP BY e.department, d.budget
            ORDER BY d.budget DESC;
        """),
        "error_hint": "Wrong JOIN: d.budget should be d.name in the ON condition",
        "expected_rows": 3,
        "expected_cols": ["department", "budget"],
        "correct_sql": "SELECT e.department, d.budget FROM employees e JOIN departments d ON e.department = d.name GROUP BY e.department, d.budget ORDER BY d.budget DESC;",
    },
    "hard_subquery": {
        "difficulty": "hard",
        "description": (
            "Fix the SQL query to find employees earning above their department average. "
            "Return name, department, salary ordered by salary descending. "
            "The subquery references wrong table — fix it."
        ),
        "buggy_code": textwrap.dedent("""\
            SELECT name, department, salary
            FROM employees e
            WHERE salary > (
                SELECT AVG(salary)
                FROM departments
                WHERE name = e.department
            )
            ORDER BY salary DESC;
        """),
        "error_hint": "Wrong table in subquery: 'departments' should be 'employees'",
        "expected_rows": 3,
        "expected_cols": ["name", "department", "salary"],
        "correct_sql": "SELECT name, department, salary FROM employees e WHERE salary > (SELECT AVG(salary) FROM employees WHERE department = e.department) ORDER BY salary DESC;",
    },
}


# ---------------------------------------------------------------------------
# Grader
# ---------------------------------------------------------------------------

def grade(task_id: str, fixed_code: str) -> dict[str, Any]:
    task = TASKS.get(task_id)
    if task is None:
        return {"score": 0.05, "error": f"Unknown task '{task_id}'", "test_results": []}

    conn = _make_db()
    try:
        cursor = conn.execute(fixed_code.strip())
        rows = cursor.fetchall()
        cols = [d[0].lower() for d in cursor.description] if cursor.description else []
    except Exception as exc:
        conn.close()
        return {"score": 0.05, "error": f"SQL Error: {exc}", "test_results": [
            {"check": "syntax", "passed": False, "detail": str(exc)}
        ]}
    finally:
        conn.close()

    checks = []
    passed = 0

    # Check 1: no error (already passed if we got here)
    checks.append({"check": "no_sql_error", "passed": True, "detail": "Query executed successfully"})
    passed += 1

    # Check 2: correct row count
    expected_rows = task["expected_rows"]
    row_ok = len(rows) == expected_rows
    checks.append({"check": "row_count", "passed": row_ok,
                   "detail": f"got {len(rows)} rows, expected {expected_rows}"})
    if row_ok:
        passed += 1

    # Check 3: correct columns
    expected_cols = [c.lower() for c in task["expected_cols"]]
    cols_ok = all(ec in cols for ec in expected_cols)
    checks.append({"check": "columns", "passed": cols_ok,
                   "detail": f"got {cols}, expected {expected_cols}"})
    if cols_ok:
        passed += 1

    # Check 4: data correctness - run correct SQL and compare
    conn2 = _make_db()
    try:
        correct_cursor = conn2.execute(task["correct_sql"])
        correct_rows = correct_cursor.fetchall()
        data_ok = sorted(str(r) for r in rows) == sorted(str(r) for r in correct_rows)
    except Exception:
        data_ok = False
    finally:
        conn2.close()

    checks.append({"check": "data_correctness", "passed": data_ok,
                   "detail": "data matches expected output" if data_ok else "data does not match expected"})
    if data_ok:
        passed += 1

    score = _safe_score(passed, 4)
    return {"score": score, "error": None, "test_results": checks}


# ---------------------------------------------------------------------------
# Episode
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
            "buggy_code": task["buggy_code"],
            "task_description": task["description"],
            "error_hint": task["error_hint"],
            "schema": "Tables: employees(id,name,department,salary,hire_date), departments(id,name,budget), projects(id,name,department_id,budget)",
            "attempt": self.attempt,
            "max_attempts": self.MAX_ATTEMPTS,
        }

    def step(self, fixed_code: str) -> dict[str, Any]:
        if self.done:
            return {"observation": self.observation(), "reward": 0.05, "done": True, "info": {}}
        self.attempt += 1
        result = grade(self.task_id, fixed_code)
        score = result["score"]
        if score > self.best_score:
            self.best_score = score
        self.done = score >= 0.94 or self.attempt >= self.MAX_ATTEMPTS
        self.history.append({"attempt": self.attempt, "score": score})
        return {
            "observation": self.observation(),
            "reward": score,
            "done": self.done,
            "info": {
                "grader_error": result["error"],
                "test_results": result["test_results"],
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

class SQLDebugEnv:
    def __init__(self):
        self._sessions: dict[str, Episode] = {}

    def reset(self, task_id=None):
        if task_id is None:
            task_id = "easy_syntax"
        if task_id not in TASKS:
            raise ValueError(f"Unknown task_id '{task_id}'. Valid: {list(TASKS)}")
        ep = Episode(task_id)
        self._sessions[ep.episode_id] = ep
        return {"session_id": ep.episode_id, "observation": ep.observation()}

    def step(self, session_id: str, fixed_code: str):
        ep = self._sessions.get(session_id)
        if ep is None:
            raise KeyError(f"session_id '{session_id}' not found.")
        return ep.step(fixed_code)

    def state(self, session_id: str):
        ep = self._sessions.get(session_id)
        if ep is None:
            raise KeyError(f"session_id '{session_id}' not found.")
        return ep.state()

    @staticmethod
    def list_tasks():
        return [
            {"task_id": tid, "difficulty": t["difficulty"], "description": t["description"]}
            for tid, t in TASKS.items()
        ]
