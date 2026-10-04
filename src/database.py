"""SQLite persistence: audit log, conditions, decisions."""
import datetime as dt
import sqlite3
from pathlib import Path

DB = Path(__file__).resolve().parent.parent / "data" / "underwriter.db"
SCHEMA = """
CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY, ts TEXT, loan_id TEXT, event TEXT, detail TEXT);
CREATE TABLE IF NOT EXISTS conditions(id INTEGER PRIMARY KEY, loan_id TEXT, condition TEXT, reason TEXT,
  evidence TEXT, guideline TEXT, status TEXT, created_by TEXT, created_at TEXT);
CREATE TABLE IF NOT EXISTS decisions(id INTEGER PRIMARY KEY, loan_id TEXT, decision TEXT, reason TEXT,
  ts TEXT, user TEXT);
"""


def now():
    return dt.datetime.now().strftime("%Y-%m-%d %H:%M")


def _run(sql, args=()):
    DB.parent.mkdir(exist_ok=True)
    with sqlite3.connect(DB) as c:
        c.row_factory = sqlite3.Row
        c.executescript(SCHEMA)
        cur = c.execute(sql, args)
        return [dict(r) for r in cur.fetchall()] if cur.description else cur.lastrowid


def log(loan_id, event, detail=""):
    _run("INSERT INTO audit(ts,loan_id,event,detail) VALUES(?,?,?,?)", (now(), loan_id, event, detail))


def audit(loan_id):
    return _run("SELECT * FROM audit WHERE loan_id=? ORDER BY id DESC", (loan_id,))


def add_condition(loan_id, condition, reason="", evidence="", guideline="", created_by="Underwriter"):
    _run("INSERT INTO conditions(loan_id,condition,reason,evidence,guideline,status,created_by,created_at)"
         " VALUES(?,?,?,?,?,?,?,?)", (loan_id, condition, reason, evidence, guideline, "Open", created_by, now()))
    log(loan_id, "Condition created", condition)


def conditions(loan_id):
    return _run("SELECT * FROM conditions WHERE loan_id=? ORDER BY id", (loan_id,))


def update_condition(loan_id, cid, **fields):
    for k, v in fields.items():
        if k in ("condition", "status"):  # whitelist columns
            _run(f"UPDATE conditions SET {k}=? WHERE id=?", (v, cid))
    log(loan_id, "Condition modified", f"#{cid}: {fields}")


def delete_condition(loan_id, cid):
    _run("DELETE FROM conditions WHERE id=?", (cid,))
    log(loan_id, "Condition deleted", f"#{cid}")


def add_decision(loan_id, decision, reason, user):
    _run("INSERT INTO decisions(loan_id,decision,reason,ts,user) VALUES(?,?,?,?,?)",
         (loan_id, decision, reason, now(), user))
    log(loan_id, "Underwriter decision", f"{decision} by {user}: {reason}")


def decisions(loan_id):
    return _run("SELECT * FROM decisions WHERE loan_id=? ORDER BY id DESC", (loan_id,))
