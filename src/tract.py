"""Tract connector for SQLite-based entity store and context engine.

This module provides initialization and basic operations for the Tract context
engine, which maintains the persistent state for the UAOS orchestration system.

Tract is a SQLite-based store that maintains:
- Reasoning chain (goals, CSFs, NCs, SOs, capabilities, epics, features)
- Planning layer (FWUs, boundaries, dependencies, design decisions, etc.)
- Execution layer (implementation contexts, entity specs, test seeds, etc.)
"""

from __future__ import annotations

import sqlite3
import uuid
from pathlib import Path
from typing import Any

# Default path for Tract database
DEFAULT_TRACT_DB = ".tract/tract.db"

# SQL to initialize basic schema (simplified version)
TRACT_SCHEMA_SQL = """
-- Sync metadata table (required for source tracking)
CREATE TABLE IF NOT EXISTS sync_meta (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id TEXT UNIQUE NOT NULL,
    last_sync_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Feature Work Units (FWUs) table
CREATE TABLE IF NOT EXISTS fwus (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    status TEXT DEFAULT 'pending',
    intent TEXT,
    addresses_acs TEXT,
    planning_version TEXT,
    feature_id TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- FWU Boundaries
CREATE TABLE IF NOT EXISTS fwu_boundaries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fwu_id TEXT NOT NULL,
    scope TEXT,
    description TEXT,
    owner_fwu_id TEXT,
    FOREIGN KEY (fwu_id) REFERENCES fwus(id) ON DELETE CASCADE
);

-- FWU Dependencies
CREATE TABLE IF NOT EXISTS fwu_dependencies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fwu_id TEXT NOT NULL,
    dependency_type TEXT,
    target_fwu_id TEXT,
    description TEXT,
    FOREIGN KEY (fwu_id) REFERENCES fwus(id) ON DELETE CASCADE
);

-- FWU Design Decisions
CREATE TABLE IF NOT EXISTS fwu_design_decisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fwu_id TEXT NOT NULL,
    decision TEXT,
    resolution TEXT,
    rationale TEXT,
    FOREIGN KEY (fwu_id) REFERENCES fwus(id) ON DELETE CASCADE
);

-- FWU Interface Contracts
CREATE TABLE IF NOT EXISTS fwu_interface_contracts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fwu_id TEXT NOT NULL,
    direction TEXT,
    counterpart_fwu_id TEXT,
    counterpart_system TEXT,
    description TEXT,
    FOREIGN KEY (fwu_id) REFERENCES fwus(id) ON DELETE CASCADE
);

-- FWU Verification Gates
CREATE TABLE IF NOT EXISTS fwu_verification_gates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fwu_id TEXT NOT NULL,
    gate TEXT,
    expectation TEXT,
    FOREIGN KEY (fwu_id) REFERENCES fwus(id) ON DELETE CASCADE
);

-- Implementation Contexts (IC)
CREATE TABLE IF NOT EXISTS implementation_contexts (
    id TEXT PRIMARY KEY,
    fwu_id TEXT NOT NULL UNIQUE,
    attempt INTEGER,
    status TEXT DEFAULT 'in_progress',
    planning_version TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (fwu_id) REFERENCES fwus(id) ON DELETE CASCADE
);

-- Entity Specifications
CREATE TABLE IF NOT EXISTS entity_specs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ic_id TEXT NOT NULL,
    entity_name TEXT,
    code_block TEXT,
    FOREIGN KEY (ic_id) REFERENCES implementation_contexts(id) ON DELETE CASCADE
);

-- Features (for reasoning chain)
CREATE TABLE IF NOT EXISTS features (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Epics (for reasoning chain)
CREATE TABLE IF NOT EXISTS epics (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    feature_id TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (feature_id) REFERENCES features(id) ON DELETE SET NULL
);

-- Capabilities (for reasoning chain)
CREATE TABLE IF NOT EXISTS capabilities (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    epic_id TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (epic_id) REFERENCES epics(id) ON DELETE SET NULL
);

-- Strategic Objectives (for reasoning chain)
CREATE TABLE IF NOT EXISTS strategic_objectives (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    capability_id TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (capability_id) REFERENCES capabilities(id) ON DELETE SET NULL
);

-- Necessary Conditions (for reasoning chain)
CREATE TABLE IF NOT EXISTS necessary_conditions (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    so_id TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (so_id) REFERENCES strategic_objectives(id) ON DELETE SET NULL
);

-- Critical Success Factors (for reasoning chain)
CREATE TABLE IF NOT EXISTS critical_success_factors (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    nc_id TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (nc_id) REFERENCES necessary_conditions(id) ON DELETE SET NULL
);

-- Goals (for reasoning chain)
CREATE TABLE IF NOT EXISTS goals (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    csf_id TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (csf_id) REFERENCES critical_success_factors(id) ON DELETE SET NULL
);
"""


class TractConnector:
    """Connector for Tract SQLite database."""

    def __init__(self, db_path: Path | str | None = None) -> None:
        """Initialize Tract connector.

        Args:
            db_path: Path to Tract SQLite database. If None, uses default path.

        Raises:
            sqlite3.Error: If database initialization fails.
        """
        if db_path is None:
            db_path = Path.cwd() / DEFAULT_TRACT_DB
        elif isinstance(db_path, str):
            db_path = Path(db_path)

        self.db_path = db_path
        self.connection: sqlite3.Connection | None = None
        self._initialized = False

    def connect(self) -> None:
        """Connect to the Tract database.

        Enables WAL mode for concurrency and foreign key constraints.

        Raises:
            sqlite3.Error: If connection fails.
        """
        if self.connection is not None:
            return

        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(str(self.db_path))
        self.connection.row_factory = sqlite3.Row

        # Enable WAL mode for concurrent access
        self.connection.execute("PRAGMA journal_mode=WAL")
        # Enable foreign key constraints
        self.connection.execute("PRAGMA foreign_keys=ON")

    def disconnect(self) -> None:
        """Disconnect from the database."""
        if self.connection:
            self.connection.close()
            self.connection = None

    def initialize(self) -> None:
        """Initialize the Tract database schema.

        Creates all necessary tables if they don't exist.
        Initializes source_id in sync_meta if needed.

        Raises:
            sqlite3.Error: If initialization fails.
        """
        if self._initialized:
            return

        self.connect()
        if self.connection is None:
            raise RuntimeError("Database connection failed")

        # Execute schema creation
        self.connection.executescript(TRACT_SCHEMA_SQL)
        self.connection.commit()

        # Initialize or get source_id
        cursor = self.connection.execute("SELECT COUNT(*) FROM sync_meta")
        count = cursor.fetchone()[0]  # type: ignore

        if count == 0:
            source_id = str(uuid.uuid4())
            self.connection.execute(
                "INSERT INTO sync_meta (source_id) VALUES (?)",
                (source_id,),
            )
            self.connection.commit()

        self._initialized = True

    def get_source_id(self) -> str:
        """Get the source_id for this connector instance.

        Returns:
            UUID string identifying this Tract connector.

        Raises:
            RuntimeError: If database is not initialized.
        """
        if not self._initialized or self.connection is None:
            raise RuntimeError("Database not initialized")

        cursor = self.connection.execute("SELECT source_id FROM sync_meta LIMIT 1")
        row = cursor.fetchone()
        if row is None:
            raise RuntimeError("source_id not found in database")
        return str(row[0])

    def create_fwu(
        self,
        fwu_id: str,
        name: str,
        status: str = "pending",
        intent: str | None = None,
        addresses_acs: str | None = None,
        planning_version: str | None = None,
        feature_id: str | None = None,
    ) -> dict[str, Any]:
        """Create a new Feature Work Unit (FWU).

        Args:
            fwu_id: Unique identifier for the FWU.
            name: Name of the FWU.
            status: Current status (default: "pending").
            intent: Intent description.
            addresses_acs: Addressed architectural concerns.
            planning_version: Planning version identifier.
            feature_id: Associated feature ID.

        Returns:
            Dictionary containing the created FWU data.

        Raises:
            RuntimeError: If database is not initialized.
        """
        if not self._initialized or self.connection is None:
            raise RuntimeError("Database not initialized")

        self.connection.execute(
            """
            INSERT INTO fwus (id, name, status, intent, addresses_acs,
                              planning_version, feature_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (fwu_id, name, status, intent, addresses_acs, planning_version,
             feature_id),
        )
        self.connection.commit()

        return {
            "id": fwu_id,
            "name": name,
            "status": status,
            "intent": intent,
            "addresses_acs": addresses_acs,
            "planning_version": planning_version,
            "feature_id": feature_id,
        }

    def get_fwu(self, fwu_id: str) -> dict[str, Any] | None:
        """Retrieve a Feature Work Unit by ID.

        Args:
            fwu_id: The FWU identifier.

        Returns:
            Dictionary containing FWU data, or None if not found.

        Raises:
            RuntimeError: If database is not initialized.
        """
        if not self._initialized or self.connection is None:
            raise RuntimeError("Database not initialized")

        cursor = self.connection.execute(
            "SELECT * FROM fwus WHERE id = ?",
            (fwu_id,),
        )
        row = cursor.fetchone()
        if row is None:
            return None

        return dict(row)

    def create_implementation_context(
        self,
        ic_id: str,
        fwu_id: str,
        attempt: int,
        status: str = "in_progress",
        planning_version: str | None = None,
    ) -> dict[str, Any]:
        """Create a new Implementation Context for an FWU.

        Args:
            ic_id: Unique identifier for the IC.
            fwu_id: Associated FWU ID.
            attempt: Attempt number.
            status: Current status (default: "in_progress").
            planning_version: Planning version identifier.

        Returns:
            Dictionary containing the created IC data.

        Raises:
            RuntimeError: If database is not initialized.
        """
        if not self._initialized or self.connection is None:
            raise RuntimeError("Database not initialized")

        self.connection.execute(
            """
            INSERT INTO implementation_contexts
            (id, fwu_id, attempt, status, planning_version)
            VALUES (?, ?, ?, ?, ?)
            """,
            (ic_id, fwu_id, attempt, status, planning_version),
        )
        self.connection.commit()

        return {
            "id": ic_id,
            "fwu_id": fwu_id,
            "attempt": attempt,
            "status": status,
            "planning_version": planning_version,
        }

    def get_implementation_context(
        self, ic_id: str
    ) -> dict[str, Any] | None:
        """Retrieve an Implementation Context by ID.

        Args:
            ic_id: The IC identifier.

        Returns:
            Dictionary containing IC data, or None if not found.

        Raises:
            RuntimeError: If database is not initialized.
        """
        if not self._initialized or self.connection is None:
            raise RuntimeError("Database not initialized")

        cursor = self.connection.execute(
            "SELECT * FROM implementation_contexts WHERE id = ?",
            (ic_id,),
        )
        row = cursor.fetchone()
        if row is None:
            return None

        return dict(row)

    def list_fwus(self, status: str | None = None) -> list[dict[str, Any]]:
        """List all Feature Work Units, optionally filtered by status.

        Args:
            status: Optional status filter.

        Returns:
            List of FWU dictionaries.

        Raises:
            RuntimeError: If database is not initialized.
        """
        if not self._initialized or self.connection is None:
            raise RuntimeError("Database not initialized")

        if status is None:
            cursor = self.connection.execute("SELECT * FROM fwus")
        else:
            cursor = self.connection.execute(
                "SELECT * FROM fwus WHERE status = ?",
                (status,),
            )

        return [dict(row) for row in cursor.fetchall()]

    def health_check(self) -> bool:
        """Check if the Tract database connection is healthy.

        Returns:
            True if connected and operational, False otherwise.
        """
        if not self._initialized or self.connection is None:
            return False

        try:
            self.connection.execute("SELECT 1")
            return True
        except sqlite3.Error:
            return False


def get_tract_connector(
    db_path: Path | str | None = None
) -> TractConnector:
    """Factory function to create and initialize a Tract connector.

    Args:
        db_path: Optional path to Tract database.

    Returns:
        Initialized TractConnector instance.

    Raises:
        sqlite3.Error: If initialization fails.
    """
    connector = TractConnector(db_path)
    connector.initialize()
    return connector
