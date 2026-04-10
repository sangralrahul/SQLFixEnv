"""
SQLFixEnv - Advanced SQL Query Optimizer Environment
A reinforcement learning environment where agents fix broken SQL queries
against a real SQLite database with 5 difficulty levels.
"""

import sqlite3
import json
import re
import difflib
from typing import Any

# ── Database Schema ──────────────────────────────────────────────────────────

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS employees (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    department_id INTEGER,
    salary REAL,
    hire_date TEXT,
    manager_id INTEGER
);

CREATE TABLE IF NOT EXISTS departments (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    budget REAL,
    location TEXT
);

CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    department_id INTEGER,
    start_date TEXT,
    end_date TEXT,
    budget REAL
);

CREATE TABLE IF NOT EXISTS assignments (
    employee_id INTEGER,
    project_id INTEGER,
    role TEXT,
    hours_allocated INTEGER,
    PRIMARY KEY (employee_id, project_id)
);

CREATE TABLE IF NOT EXISTS salaries (
    id INTEGER PRIMARY KEY,
    employee_id INTEGER,
    amount REAL,
    effective_date TEXT,
    bonus REAL DEFAULT 0
);
"""

SEED_SQL = """
INSERT OR IGNORE INTO departments VALUES
(1,'Engineering',500000,'San Francisco'),
(2,'Marketing',200000,'New York'),
(3,'Sales',300000,'Chicago'),
(4,'HR',150000,'Austin'),
(5,'Finance',250000,'Boston');

INSERT OR IGNORE INTO employees VALUES
(1,'Alice Chen',1,95000,'2019-03-15',NULL),
(2,'Bob Smith',1,85000,'2020-06-01',1),
(3,'Carol White',2,75000,'2018-11-20',NULL),
(4,'David Lee',3,70000,'2021-01-10',NULL),
(5,'Eve Johnson',1,90000,'2019-08-22',1),
(6,'Frank Brown',4,65000,'2022-03-01',NULL),
(7,'Grace Kim',5,80000,'2020-09-15',NULL),
(8,'Henry Davis',2,72000,'2021-05-30',3),
(9,'Iris Wilson',3,68000,'2022-01-15',4),
(10,'Jack Taylor',1,88000,'2019-12-01',1);

INSERT OR IGNORE INTO projects VALUES
(1,'Apollo',1,'2023-01-01','2023-12-31',120000),
(2,'Beacon',2,'2023-03-01','2023-09-30',80000),
(3,'Catalyst',1,'2023-06-01','2024-06-01',200000),
(4,'Delta',3,'2023-02-15','2023-11-30',60000),
(5,'Echo',4,'2023-04-01','2023-10-31',40000);

INSERT OR IGNORE INTO assignments VALUES
(1,1,'Lead',40),(2,1,'Developer',35),(5,1,'Developer',30),
(3,2,'Manager',40),(8,2,'Analyst',35),
(1,3,'Architect',20),(2,3,'Developer',40),(10,3,'Developer',40),
(4,4,'Manager',40),(9,4,'Analyst',35),
(6,5,'Coordinator',40);

INSERT OR IGNORE INTO salaries VALUES
(1,1,95000,'2023-01-01',5000),
(2,2,85000,'2023-01-01',3000),
(3,3,75000,'2023-01-01',2000),
(4,4,70000,'2023-01-01',1500),
(5,5,90000,'2023-01-01',4000),
(6,6,65000,'2023-01-01',1000),
(7,7,80000,'2023-01-01',2500),
(8,8,72000,'2023-01-01',1800),
(9,9,68000,'2023-01-01',1200),
(10,10,88000,'2023-01-01',3500);
"""

# ── Tasks: 5 Difficulty Levels ───────────────────────────────────────────────

TASKS = [
    # ── LEVEL 1: Easy – single table, simple fixes ──
    {
        "id": 1,
        "level": "easy",
        "description": "Fix the query to get all employee names and salaries from the employees table, ordered by salary descending.",
        "broken_query": "SELCT name, salaray FROM employes ORDER BY salaray DESK",
        "correct_query": "SELECT name, salary FROM employees ORDER BY salary DESC",
        "hint": "Check spelling of SELECT, column names, table name, and DESC keyword.",
        "max_reward": 1.0,
    },
    {
        "id": 2,
        "level": "easy",
        "description": "Fix the query to count total employees in each department (show department_id and count).",
        "broken_query": "SELECT department_id, CONT(*) AS total FORM employees GRUP BY department_id",
        "correct_query": "SELECT department_id, COUNT(*) AS total FROM employees GROUP BY department_id",
        "hint": "Fix COUNT, FROM, and GROUP BY keywords.",
        "max_reward": 1.0,
    },

    # ── LEVEL 2: Medium – WHERE clauses, aggregations ──
    {
        "id": 3,
        "level": "medium",
        "description": "Fix the query to get employees with salary above 80000 hired after 2019-01-01.",
        "broken_query": "SELECT name, salary, hire_date FROM employees WERE salary > 80000 AND hire_date > '2019-01-01' OREDER BY hire_date",
        "correct_query": "SELECT name, salary, hire_date FROM employees WHERE salary > 80000 AND hire_date > '2019-01-01' ORDER BY hire_date",
        "hint": "Fix WHERE and ORDER BY keywords.",
        "max_reward": 1.0,
    },
    {
        "id": 4,
        "level": "medium",
        "description": "Fix the query to get the average salary per department, only for departments with average salary above 75000.",
        "broken_query": "SELECT department_id, AVG(salary) as avg_sal FROM employees GROUP BY department_id HAVING AVG(salaray) > 75000 ORDER BY avg_sal DESK",
        "correct_query": "SELECT department_id, AVG(salary) as avg_sal FROM employees GROUP BY department_id HAVING AVG(salary) > 75000 ORDER BY avg_sal DESC",
        "hint": "Fix the typo in AVG(salary) inside HAVING and the sort direction.",
        "max_reward": 1.0,
    },

    # ── LEVEL 3: Hard – JOINs ──
    {
        "id": 5,
        "level": "hard",
        "description": "Fix the JOIN query to get employee names with their department names.",
        "broken_query": "SELECT e.name, d.name as dept_name FORM employees e INNER JION departments d ON e.department_id = d.id ORDER BY d.name",
        "correct_query": "SELECT e.name, d.name as dept_name FROM employees e INNER JOIN departments d ON e.department_id = d.id ORDER BY d.name",
        "hint": "Fix FROM and JOIN keywords.",
        "max_reward": 1.0,
    },
    {
        "id": 6,
        "level": "hard",
        "description": "Fix the query to get employees and their project names using assignments table.",
        "broken_query": "SELECT e.name, p.name as project FROM employees e JOIN assigments a ON e.id = a.employe_id JOIN projects p ON a.project_id = p.id",
        "correct_query": "SELECT e.name, p.name as project FROM employees e JOIN assignments a ON e.id = a.employee_id JOIN projects p ON a.project_id = p.id",
        "hint": "Fix the table name 'assignments' and column name 'employee_id'.",
        "max_reward": 1.0,
    },

    # ── LEVEL 4: Expert – subqueries, multi-join ──
    {
        "id": 7,
        "level": "expert",
        "description": "Fix the query to get employees who earn more than the average salary of their department.",
        "broken_query": "SELECT e.name, e.salary, e.department_id FROM employees e WHERE e.salary > (SELECT AVG(salary) FROM employees WHERE department_id = e.department_id) ORDRE BY e.department_id, e.salaray DESC",
        "correct_query": "SELECT e.name, e.salary, e.department_id FROM employees e WHERE e.salary > (SELECT AVG(salary) FROM employees WHERE department_id = e.department_id) ORDER BY e.department_id, e.salary DESC",
        "hint": "Fix ORDER BY keyword and salary column name in the ORDER BY clause.",
        "max_reward": 1.0,
    },
    {
        "id": 8,
        "level": "expert",
        "description": "Fix the query to get department names with their total project budgets and number of projects.",
        "broken_query": "SELECT d.name, COUNT(p.id) as num_projects, SUM(p.budget) as total_budget FROM departments d LEFT JION projects p ON d.id = p.department_id GRUP BY d.id, d.name OREDER BY total_budget DESC",
        "correct_query": "SELECT d.name, COUNT(p.id) as num_projects, SUM(p.budget) as total_budget FROM departments d LEFT JOIN projects p ON d.id = p.department_id GROUP BY d.id, d.name ORDER BY total_budget DESC",
        "hint": "Fix JOIN, GROUP BY, and ORDER BY keywords.",
        "max_reward": 1.0,
    },

    # ── LEVEL 5: Master – CTEs, window functions ──
    {
        "id": 9,
        "level": "master",
        "description": "Fix the CTE query to rank employees by salary within each department using window functions.",
        "broken_query": "WITH ranked AS (SELECT name, salary, department_id, RANK() OVER (PARTITON BY department_id ORDRE BY salary DESC) as rnk FROM employees) SELECT * FORM ranked WHERE rnk <= 2",
        "correct_query": "WITH ranked AS (SELECT name, salary, department_id, RANK() OVER (PARTITION BY department_id ORDER BY salary DESC) as rnk FROM employees) SELECT * FROM ranked WHERE rnk <= 2",
        "hint": "Fix PARTITION, ORDER BY inside window function, and FROM keyword.",
        "max_reward": 1.0,
    },
    {
        "id": 10,
        "level": "master",
        "description": "Fix the complex query to get employees with total compensation (salary + bonus), their department, and project count.",
        "broken_query": "SELECT e.name, d.name as department, (s.amount + s.bonus) as total_comp, COUNT(DISTINCT a.project_id) as num_projects FROM employees e JOIN departmens d ON e.id = d.id JOIN salarys s ON e.id = s.employee_id LEFT JOIN assigments a ON e.id = a.employee_id GRUP BY e.id, e.name, d.name, s.amount, s.bonus ODER BY total_comp DESC",
        "correct_query": "SELECT e.name, d.name as department, (s.amount + s.bonus) as total_comp, COUNT(DISTINCT a.project_id) as num_projects FROM employees e JOIN departments d ON e.department_id = d.id JOIN salaries s ON e.id = s.employee_id LEFT JOIN assignments a ON e.id = a.employee_id GROUP BY e.id, e.name, d.name, s.amount, s.bonus ORDER BY total_comp DESC",
        "hint": "Fix table names (departments, salaries, assignments), JOIN condition (department_id), GROUP BY and ORDER BY keywords.",
        "max_reward": 1.0,
    },
]

# ── Reward Logic ─────────────────────────────────────────────────────────────

def get_db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA_SQL)
    conn.executescript(SEED_SQL)
    return conn


def normalize_query(q: str) -> str:
    return re.sub(r'\s+', ' ', q.strip().upper())


def execute_query(conn, query: str):
    try:
        cur = conn.execute(query)
        rows = [dict(r) for r in cur.fetchall()]
        cols = [d[0] for d in cur.description] if cur.description else []
        return {"success": True, "rows": rows, "columns": cols, "error": None}
    except Exception as e:
        return {"success": False, "rows": [], "columns": [], "error": str(e)}


def compute_reward(agent_result: dict, correct_result: dict, agent_query: str, correct_query: str) -> dict:
    """
    Multi-dimensional reward:
    - 0.5 for executing without error
    - 0.3 for matching result rows
    - 0.2 for column similarity
    Partial credit given at each stage.
    """
    reward = 0.0
    breakdown = {}

    # 1. Syntax reward — did it run?
    if agent_result["success"]:
        reward += 0.5
        breakdown["syntax"] = 0.5
    else:
        breakdown["syntax"] = 0.0
        breakdown["rows"] = 0.0
        breakdown["columns"] = 0.0
        return {"total": 0.0, "breakdown": breakdown, "feedback": agent_result["error"]}

    # 2. Row match reward
    agent_rows = [json.dumps(r, sort_keys=True) for r in agent_result["rows"]]
    correct_rows = [json.dumps(r, sort_keys=True) for r in correct_result["rows"]]

    if agent_rows == correct_rows:
        reward += 0.3
        breakdown["rows"] = 0.3
    elif set(agent_rows) == set(correct_rows):
        reward += 0.2  # right data, wrong order
        breakdown["rows"] = 0.2
    elif len(agent_rows) > 0 and len(correct_rows) > 0:
        # partial overlap
        overlap = len(set(agent_rows) & set(correct_rows)) / max(len(correct_rows), 1)
        partial = round(0.15 * overlap, 3)
        reward += partial
        breakdown["rows"] = partial
    else:
        breakdown["rows"] = 0.0

    # 3. Column match reward
    agent_cols = set(c.upper() for c in agent_result["columns"])
    correct_cols = set(c.upper() for c in correct_result["columns"])
    if agent_cols == correct_cols:
        reward += 0.2
        breakdown["columns"] = 0.2
    elif agent_cols & correct_cols:
        partial = round(0.2 * len(agent_cols & correct_cols) / max(len(correct_cols), 1), 3)
        reward += partial
        breakdown["columns"] = partial
    else:
        breakdown["columns"] = 0.0

    feedback = "Perfect!" if reward >= 1.0 else f"Partial score: {round(reward, 3)}"
    return {"total": round(reward, 3), "breakdown": breakdown, "feedback": feedback}


# ── Environment Class ─────────────────────────────────────────────────────────

class SQLFixEnv:
    def __init__(self):
        self.tasks = TASKS
        self.current_task_idx = 0
        self.current_task = None
        self.done = False
        self.total_reward = 0.0
        self.steps = 0
        self.history = []
        self._conn = get_db()

    def reset(self, task_id: int | None = None) -> dict:
        self._conn = get_db()
        self.done = False
        self.total_reward = 0.0
        self.steps = 0
        self.history = []

        if task_id is not None:
            matches = [t for t in self.tasks if t["id"] == task_id]
            self.current_task = matches[0] if matches else self.tasks[0]
        else:
            self.current_task = self.tasks[self.current_task_idx % len(self.tasks)]
            self.current_task_idx += 1

        return {
            "task_id": self.current_task["id"],
            "level": self.current_task["level"],
            "description": self.current_task["description"],
            "broken_query": self.current_task["broken_query"],
            "hint": self.current_task["hint"],
            "observation": f"Fix this SQL query:\n{self.current_task['broken_query']}",
            "done": False,
        }

    def step(self, action: str) -> dict:
        if self.done:
            return {"error": "Episode done. Call reset()."}

        self.steps += 1
        task = self.current_task

        # Execute agent query
        agent_result = execute_query(self._conn, action)

        # Execute correct query
        correct_result = execute_query(self._conn, task["correct_query"])

        # Compute reward
        reward_info = compute_reward(agent_result, correct_result, action, task["correct_query"])
        reward = reward_info["total"]
        self.total_reward += reward

        # Episode ends on perfect score or max 5 attempts
        self.done = reward >= 1.0 or self.steps >= 5

        step_result = {
            "task_id": task["id"],
            "level": task["level"],
            "action": action,
            "reward": reward,
            "reward_breakdown": reward_info["breakdown"],
            "feedback": reward_info["feedback"],
            "agent_result": agent_result,
            "correct_result": correct_result if reward < 1.0 else None,
            "done": self.done,
            "steps": self.steps,
            "total_reward": round(self.total_reward, 3),
            "success": reward >= 1.0,
        }

        self.history.append(step_result)
        return step_result

    def get_all_tasks(self) -> list:
        return [
            {
                "id": t["id"],
                "level": t["level"],
                "description": t["description"],
                "broken_query": t["broken_query"],
                "hint": t["hint"],
            }
            for t in self.tasks
        ]

    def get_schema(self) -> dict:
        cur = self._conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [r[0] for r in cur.fetchall()]
        schema = {}
        for table in tables:
            cur = self._conn.execute(f"PRAGMA table_info({table})")
            schema[table] = [{"name": r[1], "type": r[2]} for r in cur.fetchall()]
        return schema
