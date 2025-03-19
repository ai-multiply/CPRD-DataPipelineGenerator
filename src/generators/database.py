from typing import Dict, Any, List
import os
import logging
from pathlib import Path

from src.generators.base import BaseGenerator
from src.generators.exceptions import InputValidationError, ConfigurationError
from src.config.table_config import TableConfig
from src.config.grid_engine import GridEngineConfig

class DatabaseGenerator(BaseGenerator):
    """Generator for creating SQLite database, loading data, and creating indexes."""

    def __init__(self, logger: logging.Logger = None):
        super().__init__(
            template_name='create_database',
            logger=logger or logging.getLogger(__name__)
        )

    def validate_inputs(self, config: Dict[str, Any]):
        """Validate all required inputs are present and valid."""
        required_keys = ['tables', 'processed_data_folder', 'grid_engine', 'database']
        missing_keys = [key for key in required_keys if key not in config]
        if missing_keys:
            raise InputValidationError(f"Missing required configuration keys: {missing_keys}")

        # Validate each table schema
        for table_name, schema in config['tables'].items():
            if not schema.get('columns'):
                raise ConfigurationError(f"No columns defined for table {table_name}")
            
            # Validate column definitions
            if not isinstance(schema['columns'], dict):
                raise ConfigurationError(
                    f"Columns for table {table_name} must be a dictionary of name: type"
                )

            # Validate indexes if present
            if 'indexes' in schema:
                for idx in schema['indexes']:
                    if not isinstance(idx, list):
                        raise ConfigurationError(
                            f"Invalid index definition in {table_name}. Must be list of columns"
                        )

    def generate_create_table_sql(self, table_name: str, schema: Dict) -> str:
        """Generate CREATE TABLE statement for a table."""
        columns = [
            f"{col_name} {col_type}"
            for col_name, col_type in schema['columns'].items()
        ]
        return f"CREATE TABLE {table_name}(\n    " + ",\n    ".join(columns) + "\n);"

    def generate_index_sql(self, table_name: str, schema: Dict) -> List[str]:
        """Generate CREATE INDEX statements for a table."""
        if 'indexes' not in schema:
            return []

        statements = []
        for columns in schema['indexes']:
            if not isinstance(columns, list):
                columns = [columns]  # Convert single column to list
            idx_name = f"idx_{table_name}_{'_'.join(columns)}"
            columns_str = ', '.join(columns)
            statements.append(
                f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table_name} ({columns_str});"
            )
        return statements

    def generate(self, config: Dict[str, Any]) -> str:
        """Generate database creation and loading script."""
        self.validate_inputs(config)
        
        # Initialize configurations
        grid_engine = GridEngineConfig.from_dict(config['grid_engine'])
        grid_engine.validate()
        
        # Generate SQL statements
        create_statements = []
        index_statements = []
        
        for table_name, schema in config['tables'].items():
            create_statements.append(
                self.generate_create_table_sql(table_name, schema)
            )
            index_statements.extend(
                self.generate_index_sql(table_name, schema)
            )

        # Generate script using template
        return self._render_template(
            processed_data_folder=config['processed_data_folder'],
            database_path=config['database'],
            grid_engine=grid_engine,
            create_statements=create_statements,
            index_statements=index_statements,
            tables=config['tables'].keys()
        )
