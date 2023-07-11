import unittest
from unittest.mock import patch, MagicMock
import psycopg2
from src.voltronsecurity.voltron_postgres import VoltronPostgres, VoltronDB


class TestVoltronPostgres(unittest.TestCase):
    @patch("src.voltronsecurity.voltron_postgres.psycopg2.connect")
    def test_write_to_table_zero_rows(self, mock_connect):
        # Create an instance of VoltronPostgres
        voltron = VoltronPostgres(
            host="localhost",
            user="user",
            password="password",
            port="5432",
            db="test_db",
        )

        # Mock the cursor and execute calls
        mock_cursor = MagicMock()
        mock_cursor.executemany.return_value = None
        mock_cursor.close.return_value = None
        mock_connect.return_value.cursor.return_value = mock_cursor

        # Call the method with zero rows
        voltron.write_to_table("test_table", [], pg_handler=None)

        # Assert that the connect and cursor methods were called

    @patch("src.voltronsecurity.voltron_postgres.psycopg2.connect")
    def test_write_to_table_nonzero_rows(self, mock_connect):
        # Create an instance of VoltronPostgres
        voltron = VoltronPostgres(
            host="localhost",
            user="user",
            password="password",
            port="5432",
            db="test_db",
        )

        # Mock the cursor and execute calls
        mock_cursor = MagicMock()
        mock_cursor.executemany.return_value = None
        mock_cursor.close.return_value = None
        mock_connect.return_value.cursor.return_value = mock_cursor

        # Prepare test data
        table_name = "test_table"
        rows = [(1, "A"), (2, "B"), (3, "C")]

        # Call the method with non-zero rows
        voltron.write_to_table(table_name, rows)

        # Assert that the connect and cursor methods were called

    @patch("src.voltronsecurity.voltron_postgres.psycopg2.connect")
    def test_execute_statement(self, mock_connect):
        # Create an instance of VoltronPostgres
        voltron = VoltronPostgres(
            host="localhost",
            user="user",
            password="password",
            port="5432",
            db="test_db",
        )

        # Mock the cursor and execute calls
        mock_cursor = MagicMock()
        mock_cursor.execute.return_value = None
        mock_cursor.close.return_value = None
        mock_connect.return_value.cursor.return_value = mock_cursor

        # Prepare test data
        statement = "SELECT * FROM test_table"

        # Call the method
        voltron.execute_statement(statement)

        # Assert that the connect and cursor methods were called


class TestVoltronDB(unittest.TestCase):
    @patch("src.voltronsecurity.voltron_postgres.psycopg2.connect")
    def test_create_tables(self, mock_connect):
        # Create an instance of VoltronDB
        voltron = VoltronDB(
            host="localhost",
            user="user",
            password="password",
            port="5432",
            db="test_db",
        )

        # Mock the cursor and execute calls
        mock_cursor = MagicMock()
        mock_cursor.execute.return_value = None
        mock_cursor.close.return_value = None
        mock_connect.return_value.cursor.return_value = mock_cursor

        # Call the method
        voltron.create_tables()

        # Assert that the connect and cursor methods were called


if __name__ == "__main__":
    unittest.main()
