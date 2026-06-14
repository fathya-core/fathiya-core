"""
memory/session_memory.py — إدارة ذاكرة الجلسات باستخدام SQLite
يحفظ ويسترجع الجلسات من قاعدة بيانات fathiya_memory.db
"""

import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Tuple


class SessionMemory:
    """
    مدير ذاكرة الجلسات — يستخدم SQLite لحفظ واسترجاع الجلسات.

    جدول sessions:
        id              — معرف تلقائي
        created_at      — تاريخ الإنشاء (ISO 8601)
        user_input      — مدخل المستخدم
        framed_problem_json — تقرير التشخيص (JSON)
        solver_answer   — رد الـ Solver الأولي
        evaluator_verdict — حكم الـ Evaluator (approve / revise)
        evaluator_reason — سبب الحكم
        final_answer    — الرد النهائي بعد المراجعة
    """

    def __init__(self, db_path: str = "memory/fathiya_memory.db"):
        self.db_path = db_path
        Path("memory").mkdir(exist_ok=True)
        self._initialize_database()

    def _connect(self) -> sqlite3.Connection:
        """إنشاء اتصال بقاعدة البيانات"""
        return sqlite3.connect(self.db_path)

    def _initialize_database(self):
        """إنشاء جدول sessions إذا لم يكن موجوداً"""
        conn = self._connect()
        cursor = conn.cursor()

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            user_input TEXT NOT NULL,
            framed_problem_json TEXT NOT NULL,
            solver_answer TEXT NOT NULL,
            evaluator_verdict TEXT NOT NULL,
            evaluator_reason TEXT NOT NULL,
            final_answer TEXT NOT NULL
        )
        """)

        conn.commit()
        conn.close()

    def save_session(
        self,
        user_input: str,
        framed_problem_json: str,
        solver_answer: str,
        evaluator_verdict: str,
        evaluator_reason: str,
        final_answer: str
    ) -> int:
        """
        حفظ جلسة جديدة في قاعدة البيانات.
        يرجع session_id الخاص بالجلسة المحفوظة.
        """
        conn = self._connect()
        cursor = conn.cursor()

        cursor.execute("""
        INSERT INTO sessions (
            created_at,
            user_input,
            framed_problem_json,
            solver_answer,
            evaluator_verdict,
            evaluator_reason,
            final_answer
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.utcnow().isoformat(),
            user_input,
            framed_problem_json,
            solver_answer,
            evaluator_verdict,
            evaluator_reason,
            final_answer
        ))

        session_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return session_id

    def get_recent_sessions(self, limit: int = 5) -> List[Tuple]:
        """
        استرجاع آخر الجلسات المحفوظة.
        يرجع قائمة من tuples: (id, created_at, user_input, evaluator_verdict)
        """
        conn = self._connect()
        cursor = conn.cursor()

        cursor.execute("""
        SELECT id, created_at, user_input, evaluator_verdict
        FROM sessions
        ORDER BY id DESC
        LIMIT ?
        """, (limit,))

        rows = cursor.fetchall()
        conn.close()
        return rows

    def get_session_by_id(self, session_id: int) -> Optional[Tuple]:
        """
        استرجاع جلسة محددة بمعرّفها.
        يرجع tuple بكل حقول الجلسة أو None إذا لم تُوجد.
        """
        conn = self._connect()
        cursor = conn.cursor()

        cursor.execute("""
        SELECT *
        FROM sessions
        WHERE id = ?
        """, (session_id,))

        row = cursor.fetchone()
        conn.close()
        return row
