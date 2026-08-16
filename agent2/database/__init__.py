"""Database layer for Agent 2.

Manages SQLite persistence for claims, versions, evidence, and audit logs.
"""

from .db_manager import get_db_connection, init_db

__all__ = ["get_db_connection", "init_db"]
