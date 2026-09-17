import os
import sqlite3
from datetime import datetime

from local_llm_benchmark.config import BenchmarkConfig

DATABASE_NAME = "benchmark_results.db"


class DatabaseManager:
    """
    Handles all database interactions for the local LLM benchmark.
    Uses SQLite for persistence.
    """

    def __init__(self, db_path=None):
        """
        Initializes the DatabaseManager.
        If db_path is None, it uses the default name within the current working directory.
        """
        if db_path:
            self.db_path = db_path
        else:
            # Assuming the database file should reside in the project root or a designated 'data' directory
            self.db_path = os.path.join(os.getcwd(), "data", DATABASE_NAME)
            # Ensure the parent directory exists
            os.makedirs(os.path.dirname(self.db_path) or ".", exist_ok=True)

        self.conn = None
        self.cursor = None
        self._connect()

    def _connect(self):
        """Establishes the connection to the SQLite database."""
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.cursor = self.conn.cursor()
        except sqlite3.Error as e:
            print(f"Database connection error: {e}")
            self.conn = None
            self.cursor = None

    def initialize_schema(self):
        """
        Creates the necessary tables if they do not already exist.
        Ensures the 'benchmark_results' table is present with the required schema.
        """
        if not self.cursor:
            print("Cannot initialize schema: Database connection is not established.")
            return False

        print("Initializing database schema...")
        try:
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS benchmark_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_timestamp TEXT NOT NULL,
                    benchmarkId TEXT NOT NULL,
                    model TEXT NOT NULL,
                    engine TEXT NOT NULL,
                    score REAL,
                    latencyMs INTEGER,
                    passed INTEGER,
                    scoreStr TEXT,
                    latencyStr TEXT,
                    status TEXT
                );
            """)
            self.conn.commit()
            print("Schema initialization complete. 'benchmark_results' table is ready.")
            return True
        except sqlite3.Error as e:
            print(f"Error initializing schema: {e}")
            return False

    def insert_result(self, data: dict) -> bool:
        """
        Inserts a single benchmark result record into the database.

        Args:
            data: A dictionary containing the result fields.
        Returns:
            True if insertion was successful, False otherwise.
        """
        if not self.cursor:
            print("Cannot insert data: Database connection is not established.")
            return False

        try:
            cursor = self.cursor

            # Using parameterized query to prevent SQL injection
            query = """
                INSERT INTO benchmark_results (
                    run_timestamp, benchmarkId, model, engine, score, latencyMs, passed, scoreStr, latencyStr, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """

            # Mapping dictionary values to the query order
            values = (
                data.get("run_timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                data.get("benchmarkId"),
                data.get("model"),
                data.get("engine"),
                data.get("score"),
                data.get("latencyMs"),
                data.get("passed"),
                data.get("scoreStr"),
                data.get("latencyStr"),
                data.get("status"),
            )

            cursor.execute(query, values)
            self.conn.commit()
            print(
                f"Successfully inserted result for benchmark {data.get('benchmarkId')} on {data.get('model')}."
            )
            return True
        except sqlite3.Error as e:
            print(f"Error inserting result: {e}")
            self.conn.rollback()
            return False

    def fetch_all_results(self):
        """
        Retrieves all records from the benchmark_results table.
        Returns a list of dictionaries, or None if an error occurs.
        """
        if not self.cursor:
            print("Cannot fetch results: Database connection is not established.")
            return None

        try:
            self.cursor.execute("SELECT * FROM benchmark_results ORDER BY run_timestamp DESC;")
            rows = self.cursor.fetchall()

            # Get column names for dictionary mapping
            columns = [description[0] for description in self.cursor.description]

            results = []
            for row in rows:
                results.append(dict(zip(columns, row, strict=False)))
            return results
        except sqlite3.Error as e:
            print(f"Error fetching results: {e}")
            return []

    def get_config_from_db(self) -> BenchmarkConfig:
        """
        Retrieves the entire benchmark configuration (including engines)
        from the database.

        NOTE: In a real-world scenario, configuration data would need
        a dedicated table/schema. This function implements a placeholder
        and assumes the structure retrieved from the database can
        be used to instantiate BenchmarkConfig.
        """
        # Placeholder implementation: Assume configuration is stored under a 'config' key
        # and that we can reconstruct the full object structure.
        # For now, we return an instance representing default/empty config.
        # Real implementation would involve querying multiple tables.
        from local_llm_benchmark.config import BenchmarkConfig
        
        # We return a default (or empty) config to prevent immediate failure
        # and signal where the actual DB logic needs to go.
        print("Warning: get_config_from_db called. Returning default/empty config structure.")
        return BenchmarkConfig(
            tasks=None,
            engines={},
            default_results_dir=os.path.join(os.getcwd(), "data", "results")
        )

# Export the function at the module level for easy import
def get_config_from_db():
    """Module-level function to get config from DB."""
    db_manager = DatabaseManager(db_path=None)
    # Ensure schema is initialized when calling this function
    db_manager.initialize_schema()
    try:
        config = db_manager.get_config_from_db()
        return config
    finally:
        db_manager.close()


# Global variable for easy usage outside the class if needed
# db_manager = DatabaseManager()
