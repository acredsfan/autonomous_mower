"""
Database optimization module for autonomous mower.

This module provides tools for optimizing database operations
by implementing batching, connection pooling, and query optimization.
"""

import functools
import sqlite3
import threading
import time
from queue import Queue
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from mower.utilities.logger_config import LoggerConfigInfo

# Initialize logger
logger = LoggerConfigInfo.get_logger(__name__)


class ConnectionPool:
    """
    Database connection pool.

    This class provides a pool of database connections that can be reused,
    reducing the overhead of creating new connections.
    """

    def __init__(self, db_path: str, max_connections: int = 5):
        """
        Initialize the connection pool.

        Args:
            db_path: Path to the database file
            max_connections: Maximum number of connections in the pool
        """
        self.db_path = db_path
        self.max_connections = max_connections
        self.connections = Queue(maxsize=max_connections)
        self.active_connections = 0
        self.lock = threading.Lock()  # Pre-create connections
        for _ in range(max_connections):
            self._create_connection()

        logger.info(
            f"Connection pool initialized with {max_connections} connections "
            f"to {db_path}"
        )

    def _create_connection(self):
        """Create a new database connection and add it to the pool."""
        try:
            conn = sqlite3.connect(self.db_path)
            # Enable foreign keys
            conn.execute("PRAGMA foreign_keys = ON")
            # Set journal mode to WAL for better concurrency
            conn.execute("PRAGMA journal_mode = WAL")
            # Set synchronous mode to NORMAL for better performance
            conn.execute("PRAGMA synchronous = NORMAL")

            self.connections.put(conn)
            with self.lock:
                self.active_connections += 1

            logger.debug(
                f"Created new database connection (total: {self.active_connections})"
            )
        except Exception as e:
            logger.error(f"Error creating database connection: {e}")

    def get_connection(self) -> sqlite3.Connection:
        """
        Get a connection from the pool.

        Returns:
            A database connection
        """
        try:
            # Try to get a connection from the pool
            conn = self.connections.get(block=False)
            logger.debug("Got connection from pool")
            return conn
        except Exception:
            # If the pool is empty, create a new connection
            if self.active_connections < self.max_connections:
                self._create_connection()
                return self.connections.get()
            else:
                # If we've reached the maximum number of connections,
                # wait for one to become available
                logger.warning("Connection pool exhausted, waiting for a connection")
                return self.connections.get()

    def return_connection(self, conn: sqlite3.Connection):
        """
        Return a connection to the pool.

        Args:
            conn: The connection to return
        """
        try:
            # Reset the connection state
            conn.rollback()

            # Return the connection to the pool
            self.connections.put(conn)
            logger.debug("Returned connection to pool")
        except Exception as e:
            logger.error(f"Error returning connection to pool: {e}")
            # Close the connection and create a new one
            try:
                conn.close()
                with self.lock:
                    self.active_connections -= 1
                self._create_connection()
            except Exception as e2:
                logger.error(f"Error closing connection: {e2}")

    def close_all(self):
        """Close all connections in the pool."""
        logger.info("Closing all database connections")

        # Get all connections from the pool
        connections = []
        try:
            while not self.connections.empty():
                connections.append(self.connections.get(block=False))
        except Exception:
            pass

        # Close all connections
        for conn in connections:
            try:
                conn.close()
                with self.lock:
                    self.active_connections -= 1
            except Exception as e:
                logger.error(f"Error closing connection: {e}")

        logger.info(f"Closed {len(connections)} database connections")


class BatchProcessor:
    """
    Batch processor for database operations.

    This class provides methods for batching database operations
    to reduce the overhead of multiple individual operations.
    """

    def __init__(
        self,
        connection_pool: ConnectionPool,
        batch_size: int = 100,
        auto_commit: bool = True,
    ):
        """
        Initialize the batch processor.

        Args:
            connection_pool: The connection pool to use
            batch_size: Maximum number of operations in a batch
            auto_commit: Whether to automatically commit after each batch
        """
        self.connection_pool = connection_pool
        self.batch_size = batch_size
        self.auto_commit = auto_commit
        self.insert_batches = {}
        self.update_batches = {}
        self.delete_batches = {}
        self.lock = threading.Lock()

        logger.info(f"Batch processor initialized with batch size {batch_size}")

    def add_insert(self, table: str, data: Dict[str, Any]):
        """
        Add an insert operation to the batch.

        Args:
            table: Name of the table
            data: Dictionary of column names to values
        """
        with self.lock:
            if table not in self.insert_batches:
                self.insert_batches[table] = []

            self.insert_batches[table].append(data)

            # Process batch if it reaches the maximum size
            if len(self.insert_batches[table]) >= self.batch_size:
                self._process_insert_batch(table)

    def add_update(
        self, table: str, data: Dict[str, Any], condition: str, params: Tuple
    ):
        """
        Add an update operation to the batch.

        Args:
            table: Name of the table
            data: Dictionary of column names to values
            condition: WHERE condition
            params: Parameters for the condition
        """
        with self.lock:
            if table not in self.update_batches:
                self.update_batches[table] = []

            self.update_batches[table].append((data, condition, params))

            # Process batch if it reaches the maximum size
            if len(self.update_batches[table]) >= self.batch_size:
                self._process_update_batch(table)

    def add_delete(self, table: str, condition: str, params: Tuple):
        """
        Add a delete operation to the batch.

        Args:
            table: Name of the table
            condition: WHERE condition
            params: Parameters for the condition
        """
        with self.lock:
            if table not in self.delete_batches:
                self.delete_batches[table] = []

            self.delete_batches[table].append((condition, params))

            # Process batch if it reaches the maximum size
            if len(self.delete_batches[table]) >= self.batch_size:
                self._process_delete_batch(table)

    def _process_insert_batch(self, table: str):
        """
        Process a batch of insert operations.

        Args:
            table: Name of the table
        """
        if table not in self.insert_batches or not self.insert_batches[table]:
            return

        batch = self.insert_batches[table]
        self.insert_batches[table] = []

        # Get column names from the first item
        columns = list(batch[0].keys())

        # Create the SQL query
        placeholders = ", ".join(["?"] * len(columns))
        column_str = ", ".join(columns)
        query = f"INSERT INTO {table} ({column_str}) VALUES ({placeholders})"

        # Create parameter list
        params = [tuple(item[col] for col in columns) for item in batch]

        # Execute the batch
        self._execute_batch(query, params)

        logger.debug(f"Processed batch of {len(batch)} inserts for table {table}")

    def _process_update_batch(self, table: str):
        """
        Process a batch of update operations.

        Args:
            table: Name of the table
        """
        if table not in self.update_batches or not self.update_batches[table]:
            return

        batch = self.update_batches[table]
        self.update_batches[table] = []

        # Get a connection
        conn = self.connection_pool.get_connection()
        cursor = conn.cursor()

        try:
            # Process each update separately (can't easily batch different
            # updates)
            for data, condition, condition_params in batch:
                # Create the SET clause
                set_clause = ", ".join([f"{col} = ?" for col in data.keys()])

                # Create the SQL query
                query = f"UPDATE {table} SET {set_clause} WHERE {condition}"

                # Create parameter list
                params = list(data.values()) + list(condition_params)

                # Execute the query
                cursor.execute(query, params)

            # Commit if auto-commit is enabled
            if self.auto_commit:
                conn.commit()

            logger.debug(f"Processed batch of {len(batch)} updates for table {table}")
            logger.error(f"Error processing update batch: {e}")
            conn.rollback()
        finally:
            # Return the connection to the pool
            self.connection_pool.return_connection(conn)

    def _process_delete_batch(self, table: str):
        """
        Process a batch of delete operations.

        Args:
            table: Name of the table
        """
        if table not in self.delete_batches or not self.delete_batches[table]:
            return

        batch = self.delete_batches[table]
        self.delete_batches[table] = []

        # Get a connection
        conn = self.connection_pool.get_connection()
        cursor = conn.cursor()

        try:
            # Process each delete separately (can't easily batch different
            # deletes)
            for condition, params in batch:
                # Create the SQL query
                query = f"DELETE FROM {table} WHERE {condition}"

                # Execute the query
                cursor.execute(query, params)

            # Commit if auto-commit is enabled
            if self.auto_commit:
                conn.commit()

            logger.debug(f"Processed batch of {len(batch)} deletes for table {table}")
            conn.rollback()
        finally:
            # Return the connection to the pool
            self.connection_pool.return_connection(conn)

    def _execute_batch(self, query: str, params: List[Tuple]):
        """
        Execute a batch of operations with the same query.

        Args:
            query: SQL query
            params: List of parameter tuples
        """
        # Get a connection
        conn = self.connection_pool.get_connection()
        cursor = conn.cursor()

        try:
            # Execute the batch
            cursor.executemany(query, params)

            # Commit if auto-commit is enabled
            if self.auto_commit:
                conn.commit()
        except Exception as e:
            logger.error(f"Error executing batch: {e}")
            conn.rollback()
        finally:
            # Return the connection to the pool
            self.connection_pool.return_connection(conn)

    def flush_all(self):
        """Process all pending batches."""
        logger.info("Flushing all pending batches")

        # Process insert batches
        for table in list(self.insert_batches.keys()):
            self._process_insert_batch(table)

        # Process update batches
        for table in list(self.update_batches.keys()):
            self._process_update_batch(table)

        # Process delete batches
        for table in list(self.delete_batches.keys()):
            self._process_delete_batch(table)

        logger.info("All batches flushed")


class QueryOptimizer:
    """
    Query optimizer for database operations.

    This class provides methods for optimizing database queries
    by analyzing and rewriting them for better performance.
    """

    def __init__(self, connection_pool: ConnectionPool):
        """
        Initialize the query optimizer.

        Args:
            connection_pool: The connection pool to use
        """
        self.connection_pool = connection_pool
        self.query_stats = {}
        self.query_cache = {}
        self.cache_size = 100
        self.lock = threading.Lock()

        logger.info("Query optimizer initialized")

    def optimize_query(self, query: str) -> str:
        """
        Optimize a SQL query.

        Args:
            query: The SQL query to optimize

        Returns:
            The optimized query
        """
        # Simple optimizations for now
        optimized_query = query

        # Add LIMIT if not present
        if "SELECT" in query.upper() and "LIMIT" not in query.upper():
            optimized_query += " LIMIT 1000"

        # Use indexed columns in WHERE clauses
        # This is a simple example; a real implementation would analyze the
        # schema

        return optimized_query

    def execute_query(
        self,
        query: str,
        params: Optional[Tuple] = None,
        use_cache: bool = True,
    ) -> List[Tuple]:
        """
        Execute a SQL query with optimization.

        Args:
            query: The SQL query to execute
            params: Query parameters
            use_cache: Whether to use query caching

        Returns:
            Query results
        """
        # Check cache if enabled
        cache_key = (query, str(params))
        if use_cache and cache_key in self.query_cache:
            logger.debug(f"Using cached result for query: {query}")
            return self.query_cache[cache_key]

        # Optimize the query
        optimized_query = self.optimize_query(query)

        # Record query execution time
        start_time = time.time()

        # Get a connection and execute the query
        conn = self.connection_pool.get_connection()
        cursor = conn.cursor()

        try:
            if params:
                cursor.execute(optimized_query, params)
            else:
                cursor.execute(optimized_query)

            # Get the results
            results = cursor.fetchall()

            # Record execution time
            execution_time = time.time() - start_time

            # Update query stats
            with self.lock:
                if query in self.query_stats:
                    self.query_stats[query]["count"] += 1
                    self.query_stats[query]["total_time"] += execution_time
                    self.query_stats[query]["avg_time"] = (
                        self.query_stats[query]["total_time"]
                        / self.query_stats[query]["count"]
                    )
                else:
                    self.query_stats[query] = {
                        "count": 1,
                        "total_time": execution_time,
                        "avg_time": execution_time,
                    }

            # Cache the result if caching is enabled
            if use_cache:
                with self.lock:
                    # Limit cache size
                    if len(self.query_cache) >= self.cache_size:
                        # Remove the oldest entry
                        self.query_cache.pop(next(iter(self.query_cache)))

                    self.query_cache[cache_key] = results

            logger.debug(
                f"Executed query in {execution_time:.4f} seconds: {optimized_query}"
            )
            return results
        except Exception as e:
            logger.error(f"Error executing query: {e}")
            return []
        finally:
            # Return the connection to the pool
            self.connection_pool.return_connection(conn)

    def get_slow_queries(self, threshold: float = 0.1) -> Dict[str, Dict[str, float]]:
        """
        Get statistics for slow queries.

        Args:
            threshold: Minimum average execution time to consider a query slow

        Returns:
            Dictionary of slow queries with statistics
        """
        slow_queries = {}

        with self.lock:
            for query, stats in self.query_stats.items():
                if stats["avg_time"] >= threshold:
                    slow_queries[query] = stats

        return slow_queries

    def clear_cache(self):
        """Clear the query cache."""
        with self.lock:
            self.query_cache.clear()

        logger.info("Query cache cleared")


class DatabaseOptimizer:
    """
    Database optimizer for the autonomous mower system.

    This class provides methods for optimizing database operations
    by implementing connection pooling, batching, and query optimization.
    """

    def __init__(self, db_path: str, max_connections: int = 5, batch_size: int = 100):
        """
        Initialize the database optimizer.

        Args:
            db_path: Path to the database file
            max_connections: Maximum number of connections in the pool
            batch_size: Maximum number of operations in a batch
        """
        self.db_path = db_path
        self.connection_pool = ConnectionPool(db_path, max_connections)
        self.batch_processor = BatchProcessor(self.connection_pool, batch_size)
        self.query_optimizer = QueryOptimizer(self.connection_pool)

        logger.info(f"Database optimizer initialized for {db_path}")

    def optimize_schema(self):
        """Optimize the database schema."""
        logger.info("Optimizing database schema")

        # Get a connection
        conn = self.connection_pool.get_connection()
        cursor = conn.cursor()

        try:
            # Enable foreign keys
            cursor.execute("PRAGMA foreign_keys = ON")

            # Set journal mode to WAL for better concurrency
            cursor.execute("PRAGMA journal_mode = WAL")

            # Set synchronous mode to NORMAL for better performance
            cursor.execute("PRAGMA synchronous = NORMAL")

            # Set cache size to 10000 pages (about 40MB)
            cursor.execute("PRAGMA cache_size = 10000")

            # Set temp store to memory
            cursor.execute("PRAGMA temp_store = MEMORY")

            # Analyze the database to update statistics
            cursor.execute("ANALYZE")

            # Vacuum the database to reclaim space
            cursor.execute("VACUUM")

            conn.commit()

            logger.info("Database schema optimized")
        except Exception as e:
            logger.error(f"Error optimizing database schema: {e}")
        finally:
            # Return the connection to the pool
            self.connection_pool.return_connection(conn)

    def create_indexes(self, table: str, columns: List[str]):
        """
        Create indexes on specified columns.

        Args:
            table: Name of the table
            columns: List of columns to index
        """
        logger.info(f"Creating indexes on {table} ({', '.join(columns)})")

        # Get a connection
        conn = self.connection_pool.get_connection()
        cursor = conn.cursor()

        try:
            for column in columns:
                index_name = f"idx_{table}_{column}"
                query = f"CREATE INDEX IF NOT EXISTS {index_name} ON {table} ({column})"
                cursor.execute(query)

            conn.commit()

            logger.info(f"Created indexes on {table}")
        except Exception as e:
            logger.error(f"Error creating indexes: {e}")
            conn.rollback()
        finally:
            # Return the connection to the pool
            self.connection_pool.return_connection(conn)

    def insert(self, table: str, data: Dict[str, Any], batch: bool = True):
        """
        Insert data into a table.

        Args:
            table: Name of the table
            data: Dictionary of column names to values
            batch: Whether to batch the operation
        """
        if batch:
            # Add to batch
            self.batch_processor.add_insert(table, data)
        else:
            # Execute immediately
            columns = list(data.keys())
            placeholders = ", ".join(["?"] * len(columns))
            column_str = ", ".join(columns)
            query = f"INSERT INTO {table}  ({column_str}) VALUES ({placeholders}) "
            params = tuple(data.values())

            # Get a connection
            conn = self.connection_pool.get_connection()
            cursor = conn.cursor()

            try:
                cursor.execute(query, params)
                conn.commit()
            except Exception as e:
                logger.error(f"Error inserting data: {e}")
                conn.rollback()
            finally:
                # Return the connection to the pool
                self.connection_pool.return_connection(conn)

    def update(
        self,
        table: str,
        data: Dict[str, Any],
        condition: str,
        params: Tuple,
        batch: bool = True,
    ):
        """
        Update data in a table.

        Args:
            table: Name of the table
            data: Dictionary of column names to values
            condition: WHERE condition
            params: Parameters for the condition
            batch: Whether to batch the operation
        """
        if batch:
            # Add to batch
            self.batch_processor.add_update(table, data, condition, params)
        else:
            # Execute immediately
            set_clause = ", ".join([f"{col} = ?" for col in data.keys()])
            query = f"UPDATE {table} SET {set_clause} WHERE {condition}"
            update_params = list(data.values()) + list(params)

            # Get a connection
            conn = self.connection_pool.get_connection()
            cursor = conn.cursor()

            try:
                cursor.execute(query, update_params)
                conn.commit()
            except Exception as e:
                logger.error(f"Error updating data: {e}")
                conn.rollback()
            finally:
                # Return the connection to the pool
                self.connection_pool.return_connection(conn)

    def delete(self, table: str, condition: str, params: Tuple, batch: bool = True):
        """
        Delete data from a table.

        Args:
            table: Name of the table
            condition: WHERE condition
            params: Parameters for the condition
            batch: Whether to batch the operation
        """
        if batch:
            # Add to batch
            self.batch_processor.add_delete(table, condition, params)
        else:
            # Execute immediately
            query = f"DELETE FROM {table} WHERE {condition}"

            # Get a connection
            conn = self.connection_pool.get_connection()
            cursor = conn.cursor()

            try:
                cursor.execute(query, params)
                conn.commit()
            except Exception as e:
                logger.error(f"Error deleting data: {e}")
                conn.rollback()
            finally:
                # Return the connection to the pool
                self.connection_pool.return_connection(conn)

    def query(
        self,
        query: str,
        params: Optional[Tuple] = None,
        use_cache: bool = True,
    ) -> List[Tuple]:
        """
        Execute a SQL query.

        Args:
            query: The SQL query to execute
            params: Query parameters
            use_cache: Whether to use query caching

        Returns:
            Query results
        """
        return self.query_optimizer.execute_query(query, params, use_cache)

    def flush_batches(self):
        """Process all pending batches."""
        self.batch_processor.flush_all()

    def clear_query_cache(self):
        """Clear the query cache."""
        self.query_optimizer.clear_cache()

    def get_slow_queries(self, threshold: float = 0.1) -> Dict[str, Dict[str, float]]:
        """
        Get statistics for slow queries.

        Args:
            threshold: Minimum average execution time to consider a query slow

        Returns:
            Dictionary of slow queries with statistics
        """
        return self.query_optimizer.get_slow_queries(threshold)

    def cleanup(self):
        """Clean up resources used by the optimizer."""
        logger.info("Cleaning up database optimizer")

        # Flush any pending batches
        self.batch_processor.flush_all()

        # Close all connections
        self.connection_pool.close_all()

        logger.info("Database optimizer cleaned up")


# Singleton instance
_database_optimizer = None


def get_database_optimizer(
    db_path: str = "mower.db", max_connections: int = 5, batch_size: int = 100
) -> DatabaseOptimizer:
    """
    Get or create the singleton database optimizer instance.

    Args:
        db_path: Path to the database file
        max_connections: Maximum number of connections in the pool
        batch_size: Maximum number of operations in a batch

    Returns:
        The database optimizer instance
    """
    global _database_optimizer

    if _database_optimizer is None:
        _database_optimizer = DatabaseOptimizer(db_path, max_connections, batch_size)

    return _database_optimizer


def optimize_database(db_path: str = "mower.db"):
    """
    Optimize the database.

    Args:
        db_path: Path to the database file
    """
    logger.info(f"Optimizing database {db_path}")

    # Get optimizer
    optimizer = get_database_optimizer(db_path)

    # Optimize schema
    optimizer.optimize_schema()

    # Create indexes on commonly queried columns
    optimizer.create_indexes("sensor_readings", ["timestamp", "sensor_id"])
    optimizer.create_indexes("mower_positions", ["timestamp"])
    optimizer.create_indexes("system_logs", ["timestamp", "level"])

    logger.info("Database optimization complete")

    return optimizer


if __name__ == "__main__":
    # Run database optimization
    optimize_database()
