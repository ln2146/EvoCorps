import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class ActionLogRecord:
    action_id: str
    effectiveness_score: float
    timestamp: Optional[str] = None
    execution_time: float = 0.0
    success: bool = True
    situation_context: Optional[Dict[str, Any]] = None
    strategic_decision: Optional[Dict[str, Any]] = None
    execution_details: Optional[Dict[str, Any]] = None
    lessons_learned: Optional[Dict[str, Any]] = None
    full_log: Optional[Dict[str, Any]] = None


ACTION_LOGS_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS action_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    action_id TEXT UNIQUE,
    timestamp TEXT,
    execution_time REAL,
    success BOOLEAN,
    effectiveness_score REAL,
    situation_context TEXT,
    strategic_decision TEXT,
    execution_details TEXT,
    lessons_learned TEXT,
    full_log TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
"""

def _json_default_serializer(value: Any) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def persist_action_log_record(db_path: Path, record: ActionLogRecord) -> None:
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    timestamp = record.timestamp or datetime.now().isoformat()

    situation_context = record.situation_context or {}
    strategic_decision = record.strategic_decision or {}
    execution_details = record.execution_details or {}
    lessons_learned = record.lessons_learned or {}
    full_log = record.full_log or {}

    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute(ACTION_LOGS_SCHEMA_SQL)
        cursor.execute(
            """
            INSERT OR REPLACE INTO action_logs (
                action_id, timestamp, execution_time, success, effectiveness_score,
                situation_context, strategic_decision, execution_details,
                lessons_learned, full_log
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record.action_id,
                timestamp,
                float(record.execution_time),
                bool(record.success),
                float(record.effectiveness_score),
                json.dumps(situation_context, ensure_ascii=False, default=_json_default_serializer),
                json.dumps(strategic_decision, ensure_ascii=False, default=_json_default_serializer),
                json.dumps(execution_details, ensure_ascii=False, default=_json_default_serializer),
                json.dumps(lessons_learned, ensure_ascii=False, default=_json_default_serializer),
                json.dumps(full_log, ensure_ascii=False, default=_json_default_serializer),
            ),
        )
        conn.commit()
    finally:
        conn.close()
