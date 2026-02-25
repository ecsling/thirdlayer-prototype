"""SQLite storage for actions and transitions.

Uses stdlib sqlite3 with no ORM. Maintains schema consistency.
"""
import sqlite3
import json
import time
from pathlib import Path
from typing import Any

from thirdlayer_prototype.models.action import Action


class Storage:
    """SQLite storage manager for action transitions."""
    
    def __init__(self, db_path: str = "thirdlayer.db"):
        self.db_path = db_path
        self.conn: sqlite3.Connection | None = None
        
    def connect(self) -> None:
        """Connect to database and initialize schema."""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self._initialize_schema()
    
    def _initialize_schema(self) -> None:
        """Load and execute schema.sql."""
        schema_path = Path(__file__).parent / "schema.sql"
        with open(schema_path, "r") as f:
            schema_sql = f.read()
        self.conn.executescript(schema_sql)
        self.conn.commit()
    
    def close(self) -> None:
        """Close database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None
    
    def record_action(self, action: Action, url: str = "", success: bool = True) -> int:
        """Record an action execution.
        
        Returns the action ID.
        """
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO actions (action_signature, action_json, timestamp, url, success)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                action.signature(),
                action.to_json(),
                time.time(),
                url,
                1 if success else 0,
            ),
        )
        self.conn.commit()
        return cursor.lastrowid
    
    def record_transition_first_order(self, from_action: Action, to_action: Action) -> None:
        """Record or increment first-order transition count."""
        from_sig = from_action.signature()
        to_sig = to_action.signature()
        
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO transitions_first_order (from_action, to_action, count)
            VALUES (?, ?, 1)
            ON CONFLICT(from_action, to_action)
            DO UPDATE SET count = count + 1
            """,
            (from_sig, to_sig),
        )
        self.conn.commit()
    
    def record_transition_second_order(
        self, from_action_1: Action, from_action_2: Action, to_action: Action
    ) -> None:
        """Record or increment second-order transition count."""
        sig_1 = from_action_1.signature()
        sig_2 = from_action_2.signature()
        to_sig = to_action.signature()
        
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO transitions_second_order (from_action_1, from_action_2, to_action, count)
            VALUES (?, ?, ?, 1)
            ON CONFLICT(from_action_1, from_action_2, to_action)
            DO UPDATE SET count = count + 1
            """,
            (sig_1, sig_2, to_sig),
        )
        self.conn.commit()
    
    def get_first_order_transitions(self, from_action: Action) -> list[dict[str, Any]]:
        """Get all first-order transitions from given action.
        
        Returns list of dicts with keys: to_action, count.
        """
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT to_action, count
            FROM transitions_first_order
            WHERE from_action = ?
            ORDER BY count DESC
            """,
            (from_action.signature(),),
        )
        return [{"to_action": row["to_action"], "count": row["count"]} for row in cursor.fetchall()]
    
    def get_second_order_transitions(
        self, from_action_1: Action, from_action_2: Action
    ) -> list[dict[str, Any]]:
        """Get all second-order transitions from given action pair.
        
        Returns list of dicts with keys: to_action, count.
        """
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT to_action, count
            FROM transitions_second_order
            WHERE from_action_1 = ? AND from_action_2 = ?
            ORDER BY count DESC
            """,
            (from_action_1.signature(), from_action_2.signature()),
        )
        return [{"to_action": row["to_action"], "count": row["count"]} for row in cursor.fetchall()]
    
    def get_recent_actions(self, limit: int = 10) -> list[Action]:
        """Get most recent actions.
        
        Returns list of Action objects.
        """
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT action_json
            FROM actions
            ORDER BY timestamp DESC
            LIMIT ?
            """,
            (limit,),
        )
        return [Action.from_json(row["action_json"]) for row in cursor.fetchall()]
    
    def get_top_transitions(self, k: int = 10) -> list[dict[str, Any]]:
        """Get top K most common transitions (first-order).
        
        Returns list of dicts with keys: from_action, to_action, count.
        """
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT from_action, to_action, count
            FROM transitions_first_order
            ORDER BY count DESC
            LIMIT ?
            """,
            (k,),
        )
        return [
            {
                "from_action": row["from_action"],
                "to_action": row["to_action"],
                "count": row["count"],
            }
            for row in cursor.fetchall()
        ]
    
    def get_total_transition_count(self) -> int:
        """Get total number of recorded transitions."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT SUM(count) as total FROM transitions_first_order")
        result = cursor.fetchone()
        return result["total"] if result["total"] else 0
    
    def clear_all(self) -> None:
        """Clear all data (for testing)."""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM actions")
        cursor.execute("DELETE FROM transitions_first_order")
        cursor.execute("DELETE FROM transitions_second_order")
        self.conn.commit()
