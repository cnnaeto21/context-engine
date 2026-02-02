"""
Neo4j Graph Client

Manages connections to Neo4j database and provides low-level query execution.
"""

import logging
from typing import Dict, List, Optional, Any
from contextlib import contextmanager

from neo4j import GraphDatabase, Driver, Session, Result
from neo4j.exceptions import ServiceUnavailable, AuthError

logger = logging.getLogger(__name__)


class GraphClient:
    """
    Neo4j database client for managing graph database connections and queries.
    """

    def __init__(self, uri: str, user: str, password: str):
        """
        Initialize Neo4j connection.

        Args:
            uri: Neo4j connection URI (e.g., bolt://localhost:7687)
            user: Database username
            password: Database password

        Raises:
            ServiceUnavailable: If cannot connect to Neo4j
            AuthError: If authentication fails
        """
        self.uri = uri
        self.user = user
        self._driver: Optional[Driver] = None
        logger.info(f"Initializing GraphClient for {uri}")

        try:
            self._driver = GraphDatabase.driver(uri, auth=(user, password))
            # Test connection
            self._driver.verify_connectivity()
            logger.info("Successfully connected to Neo4j")
        except ServiceUnavailable as e:
            logger.error(f"Cannot connect to Neo4j at {uri}: {e}")
            raise
        except AuthError as e:
            logger.error(f"Authentication failed for Neo4j: {e}")
            raise

    def close(self) -> None:
        """Close the Neo4j driver connection."""
        if self._driver:
            self._driver.close()
            logger.info("Neo4j connection closed")

    @contextmanager
    def get_session(self) -> Session:
        """
        Context manager for Neo4j sessions.

        Yields:
            Neo4j Session object

        Example:
            with client.get_session() as session:
                result = session.run("MATCH (n) RETURN count(n)")
        """
        if not self._driver:
            raise RuntimeError("GraphClient not connected to Neo4j")

        session = self._driver.session()
        try:
            yield session
        finally:
            session.close()

    def execute_query(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Execute a Cypher query and return results as a list of dictionaries.

        Args:
            query: Cypher query string
            parameters: Optional query parameters

        Returns:
            List of result records as dictionaries

        Raises:
            RuntimeError: If query execution fails
        """
        logger.debug(f"Executing query: {query[:100]}...")

        try:
            with self.get_session() as session:
                result = session.run(query, parameters or {})
                records = [record.data() for record in result]
                logger.debug(f"Query returned {len(records)} records")
                return records
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            raise RuntimeError(f"Failed to execute query: {e}")

    def execute_write_transaction(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Execute a write transaction (CREATE, UPDATE, DELETE).

        Args:
            query: Cypher query string
            parameters: Optional query parameters

        Returns:
            List of result records as dictionaries

        Raises:
            RuntimeError: If transaction fails
        """
        logger.debug(f"Executing write transaction: {query[:100]}...")

        try:
            with self.get_session() as session:
                result = session.write_transaction(
                    lambda tx: tx.run(query, parameters or {}).data()
                )
                logger.debug(f"Write transaction completed successfully")
                return result
        except Exception as e:
            logger.error(f"Write transaction failed: {e}")
            raise RuntimeError(f"Failed to execute write transaction: {e}")

    def initialize_schema(self, schema_file_path: str) -> None:
        """
        Initialize database schema from a Cypher file.

        Args:
            schema_file_path: Path to .cypher file with schema definitions

        Raises:
            FileNotFoundError: If schema file doesn't exist
            RuntimeError: If schema initialization fails
        """
        logger.info(f"Initializing schema from {schema_file_path}")

        try:
            with open(schema_file_path, 'r') as f:
                schema_script = f.read()

            # Split by semicolon and execute each statement
            statements = [s.strip() for s in schema_script.split(';') if s.strip()]

            for statement in statements:
                # Skip comments and empty lines
                if statement.startswith('//') or not statement:
                    continue

                self.execute_query(statement)

            logger.info("Schema initialized successfully")

        except FileNotFoundError:
            logger.error(f"Schema file not found: {schema_file_path}")
            raise
        except Exception as e:
            logger.error(f"Schema initialization failed: {e}")
            raise RuntimeError(f"Failed to initialize schema: {e}")

    def load_data_from_cypher(self, data_file_path: str) -> None:
        """
        Load sample data from a Cypher file.

        Args:
            data_file_path: Path to .cypher file with data statements

        Raises:
            FileNotFoundError: If data file doesn't exist
            RuntimeError: If data loading fails
        """
        logger.info(f"Loading data from {data_file_path}")

        try:
            with open(data_file_path, 'r') as f:
                data_script = f.read()

            # Execute the entire script (Neo4j handles batching)
            statements = [s.strip() for s in data_script.split(';') if s.strip()]

            for statement in statements:
                # Skip comments and empty lines
                if statement.startswith('//') or not statement:
                    continue

                self.execute_query(statement)

            logger.info("Data loaded successfully")

        except FileNotFoundError:
            logger.error(f"Data file not found: {data_file_path}")
            raise
        except Exception as e:
            logger.error(f"Data loading failed: {e}")
            raise RuntimeError(f"Failed to load data: {e}")

    def health_check(self) -> bool:
        """
        Check if the Neo4j connection is healthy.

        Returns:
            True if connection is healthy, False otherwise
        """
        try:
            result = self.execute_query("RETURN 1 as health")
            return len(result) > 0 and result[0].get('health') == 1
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False

    def get_database_stats(self) -> Dict[str, Any]:
        """
        Get database statistics (node counts, relationship counts, etc.).

        Returns:
            Dictionary with database statistics
        """
        try:
            # Count nodes by label
            node_query = """
            MATCH (n)
            RETURN labels(n)[0] as label, count(n) as count
            ORDER BY count DESC
            """
            node_counts = self.execute_query(node_query)

            # Count relationships by type
            rel_query = """
            MATCH ()-[r]->()
            RETURN type(r) as type, count(r) as count
            ORDER BY count DESC
            """
            rel_counts = self.execute_query(rel_query)

            return {
                'nodes': node_counts,
                'relationships': rel_counts,
                'total_nodes': sum(item['count'] for item in node_counts),
                'total_relationships': sum(item['count'] for item in rel_counts)
            }
        except Exception as e:
            logger.error(f"Failed to get database stats: {e}")
            return {}

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
