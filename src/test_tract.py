"""Tests for the Tract connector module."""

import sqlite3
import tempfile
from pathlib import Path

import pytest

from tract import TractConnector, get_tract_connector


class TestTractConnectorBasics:
    """Tests for basic TractConnector functionality."""

    def test_connector_creation_with_default_path(self) -> None:
        """Test creating a connector with default path."""
        connector = TractConnector()
        assert connector.db_path.name == "tract.db"  # nosec: B101

    def test_connector_creation_with_custom_path(self) -> None:
        """Test creating a connector with custom path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            custom_path = Path(tmpdir) / "custom_tract.db"
            connector = TractConnector(custom_path)
            assert connector.db_path == custom_path  # nosec: B101

    def test_connector_creation_with_string_path(self) -> None:
        """Test creating a connector with string path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            custom_path = str(Path(tmpdir) / "test_tract.db")
            connector = TractConnector(custom_path)
            assert connector.db_path == Path(custom_path)  # nosec: B101


class TestTractConnectorConnection:
    """Tests for Tract database connection."""

    def test_connect(self) -> None:
        """Test establishing database connection."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "tract.db"
            connector = TractConnector(db_path)
            connector.connect()
            assert connector.connection is not None  # nosec: B101
            connector.disconnect()

    def test_disconnect(self) -> None:
        """Test disconnecting from database."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "tract.db"
            connector = TractConnector(db_path)
            connector.connect()
            connector.disconnect()
            assert connector.connection is None  # nosec: B101

    def test_multiple_connects_idempotent(self) -> None:
        """Test that multiple connects don't create new connections."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "tract.db"
            connector = TractConnector(db_path)
            connector.connect()
            first_conn = connector.connection
            connector.connect()
            second_conn = connector.connection
            # Should be same connection object
            assert first_conn is second_conn  # nosec: B101
            connector.disconnect()


class TestTractConnectorInitialization:
    """Tests for Tract database initialization."""

    def test_initialize(self) -> None:
        """Test database initialization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "tract.db"
            connector = TractConnector(db_path)
            connector.initialize()
            assert connector._initialized is True  # nosec: B101
            assert connector.connection is not None  # nosec: B101
            connector.disconnect()

    def test_initialize_idempotent(self) -> None:
        """Test that initialize is idempotent."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "tract.db"
            connector = TractConnector(db_path)
            connector.initialize()
            connector.initialize()  # Second call should be no-op
            assert connector._initialized is True  # nosec: B101
            connector.disconnect()

    def test_tables_created_on_initialize(self) -> None:
        """Test that all required tables are created."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "tract.db"
            connector = TractConnector(db_path)
            connector.initialize()

            # Check that tables exist
            assert connector.connection is not None  # nosec: B101
            cursor = connector.connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
            tables = {row[0] for row in cursor.fetchall()}

            required_tables = {
                "sync_meta",
                "fwus",
                "fwu_boundaries",
                "fwu_dependencies",
                "fwu_design_decisions",
                "fwu_interface_contracts",
                "fwu_verification_gates",
                "implementation_contexts",
                "entity_specs",
                "features",
                "epics",
                "capabilities",
                "strategic_objectives",
                "necessary_conditions",
                "critical_success_factors",
                "goals",
            }

            assert required_tables.issubset(tables)  # nosec: B101
            connector.disconnect()


class TestSourceIdManagement:
    """Tests for source_id management."""

    def test_get_source_id(self) -> None:
        """Test retrieving source_id."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "tract.db"
            connector = TractConnector(db_path)
            connector.initialize()

            source_id = connector.get_source_id()
            assert source_id is not None  # nosec: B101
            assert len(source_id) > 0  # nosec: B101
            connector.disconnect()

    def test_source_id_persistence(self) -> None:
        """Test that source_id persists across connections."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "tract.db"

            # First connection
            connector1 = TractConnector(db_path)
            connector1.initialize()
            source_id1 = connector1.get_source_id()
            connector1.disconnect()

            # Second connection
            connector2 = TractConnector(db_path)
            connector2.initialize()
            source_id2 = connector2.get_source_id()
            connector2.disconnect()

            # Should be the same
            assert source_id1 == source_id2  # nosec: B101

    def test_get_source_id_before_init(self) -> None:
        """Test getting source_id before initialization raises error."""
        connector = TractConnector()
        with pytest.raises(RuntimeError):
            connector.get_source_id()


class TestFWUOperations:
    """Tests for Feature Work Unit operations."""

    def test_create_fwu(self) -> None:
        """Test creating a Feature Work Unit."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "tract.db"
            connector = TractConnector(db_path)
            connector.initialize()

            result = connector.create_fwu(
                fwu_id="FWU-001",
                name="Test FWU",
                status="pending",
                intent="Test intent",
            )

            assert result["id"] == "FWU-001"  # nosec: B101
            assert result["name"] == "Test FWU"  # nosec: B101
            assert result["status"] == "pending"  # nosec: B101
            connector.disconnect()

    def test_get_fwu(self) -> None:
        """Test retrieving a Feature Work Unit."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "tract.db"
            connector = TractConnector(db_path)
            connector.initialize()

            connector.create_fwu(
                fwu_id="FWU-001",
                name="Test FWU",
                status="pending",
            )

            fwu = connector.get_fwu("FWU-001")
            assert fwu is not None  # nosec: B101
            assert fwu["id"] == "FWU-001"  # nosec: B101
            assert fwu["name"] == "Test FWU"  # nosec: B101
            connector.disconnect()

    def test_get_nonexistent_fwu(self) -> None:
        """Test retrieving a nonexistent FWU returns None."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "tract.db"
            connector = TractConnector(db_path)
            connector.initialize()

            fwu = connector.get_fwu("NONEXISTENT")
            assert fwu is None  # nosec: B101
            connector.disconnect()

    def test_list_fwus(self) -> None:
        """Test listing Feature Work Units."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "tract.db"
            connector = TractConnector(db_path)
            connector.initialize()

            connector.create_fwu("FWU-001", "FWU 1", status="pending")
            connector.create_fwu("FWU-002", "FWU 2", status="in_progress")
            connector.create_fwu("FWU-003", "FWU 3", status="pending")

            fwus = connector.list_fwus()
            assert len(fwus) == 3  # nosec: B101

            pending_fwus = connector.list_fwus(status="pending")
            assert len(pending_fwus) == 2  # nosec: B101
            connector.disconnect()


class TestImplementationContextOperations:
    """Tests for Implementation Context operations."""

    def test_create_implementation_context(self) -> None:
        """Test creating an Implementation Context."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "tract.db"
            connector = TractConnector(db_path)
            connector.initialize()

            # First create an FWU
            connector.create_fwu("FWU-001", "Test FWU")

            # Then create an IC
            result = connector.create_implementation_context(
                ic_id="IC-001",
                fwu_id="FWU-001",
                attempt=1,
                status="in_progress",
            )

            assert result["id"] == "IC-001"  # nosec: B101
            assert result["fwu_id"] == "FWU-001"  # nosec: B101
            assert result["attempt"] == 1  # nosec: B101
            connector.disconnect()

    def test_get_implementation_context(self) -> None:
        """Test retrieving an Implementation Context."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "tract.db"
            connector = TractConnector(db_path)
            connector.initialize()

            connector.create_fwu("FWU-001", "Test FWU")
            connector.create_implementation_context(
                ic_id="IC-001",
                fwu_id="FWU-001",
                attempt=1,
            )

            ic = connector.get_implementation_context("IC-001")
            assert ic is not None  # nosec: B101
            assert ic["id"] == "IC-001"  # nosec: B101
            assert ic["fwu_id"] == "FWU-001"  # nosec: B101
            connector.disconnect()

    def test_get_nonexistent_ic(self) -> None:
        """Test retrieving a nonexistent IC returns None."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "tract.db"
            connector = TractConnector(db_path)
            connector.initialize()

            ic = connector.get_implementation_context("NONEXISTENT")
            assert ic is None  # nosec: B101
            connector.disconnect()


class TestHealthCheck:
    """Tests for health check functionality."""

    def test_health_check_healthy(self) -> None:
        """Test health check on healthy connection."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "tract.db"
            connector = TractConnector(db_path)
            connector.initialize()

            assert connector.health_check() is True  # nosec: B101
            connector.disconnect()

    def test_health_check_not_initialized(self) -> None:
        """Test health check on uninitialized connector."""
        connector = TractConnector()
        assert connector.health_check() is False  # nosec: B101

    def test_health_check_disconnected(self) -> None:
        """Test health check after disconnection."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "tract.db"
            connector = TractConnector(db_path)
            connector.initialize()
            connector.disconnect()

            assert connector.health_check() is False  # nosec: B101


class TestFactoryFunction:
    """Tests for factory function."""

    def test_get_tract_connector(self) -> None:
        """Test factory function creates initialized connector."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "tract.db"
            connector = get_tract_connector(db_path)

            assert connector._initialized is True  # nosec: B101
            assert connector.connection is not None  # nosec: B101

            source_id = connector.get_source_id()
            assert source_id is not None  # nosec: B101
            connector.disconnect()

    def test_factory_with_default_path(self) -> None:
        """Test factory function with default path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Temporarily change to temp dir
            import os

            old_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                connector = get_tract_connector()
                assert connector._initialized is True  # nosec: B101
                connector.disconnect()
            finally:
                os.chdir(old_cwd)


class TestDatabaseIntegrity:
    """Tests for database integrity."""

    def test_foreign_key_constraints_enabled(self) -> None:
        """Test that foreign key constraints are enforced."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "tract.db"
            connector = TractConnector(db_path)
            connector.initialize()

            # Try to insert IC with nonexistent FWU
            # This should fail if foreign keys are enforced
            assert connector.connection is not None  # nosec: B101
            with pytest.raises(sqlite3.IntegrityError):
                connector.connection.execute(
                    """
                    INSERT INTO implementation_contexts
                    (id, fwu_id, attempt, status)
                    VALUES (?, ?, ?, ?)
                    """,
                    ("IC-001", "NONEXISTENT", 1, "pending"),
                )
                connector.connection.commit()

            connector.disconnect()


class TestConcurrentAccess:
    """Tests for concurrent access (WAL mode)."""

    def test_wal_mode_enabled(self) -> None:
        """Test that WAL mode is enabled."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "tract.db"
            connector = TractConnector(db_path)
            connector.initialize()

            # Check WAL mode
            assert connector.connection is not None  # nosec: B101
            cursor = connector.connection.execute("PRAGMA journal_mode")
            mode = cursor.fetchone()[0]  # type: ignore
            assert mode.upper() == "WAL"  # nosec: B101

            connector.disconnect()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
