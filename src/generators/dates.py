import os
from typing import Dict, Any, List
import logging

from src.generators.base import BaseGenerator
from src.generators.exceptions import InputValidationError, FileNotFoundError
from src.config.table_config import TableConfig
from src.config.grid_engine import GridEngineConfig
from src.utils.table_validator import TableValidator

class DateConversionGenerator(BaseGenerator):
    """Generator for date format conversion scripts."""

    def __init__(self, logger: logging.Logger = None):
        super().__init__(
            template_name='convert_dates',
            logger=logger or logging.getLogger(__name__)
        )
        self.validator = TableValidator(self.logger)

    def validate_inputs(self, config: Dict[str, Any]):
        """
        Validate all required inputs are present and valid.
        
        Args:
            config: Dictionary containing configuration
            
        Raises:
            InputValidationError: If validation fails
        """
        required_keys = ['tables', 'processed_data_folder', 'grid_engine']
        missing_keys = [key for key in required_keys if key not in config]
        if missing_keys:
            raise InputValidationError(f"Missing required configuration keys: {missing_keys}")

        # Validate output directory exists
        processed_data_folder = os.path.expandvars(config['processed_data_folder'])
        if not os.path.isdir(processed_data_folder):
            raise InputValidationError(
                f"Output directory does not exist: {processed_data_folder}"
            )

    def validate_table_columns(
        self,
        tables: Dict[str, TableConfig],
        processed_data_folder: str
    ) -> Dict[str, Dict[str, int]]:
        """
        Validate and get positions of date columns for all tables.

        Args:
            tables: Dictionary of table configurations
            processed_data_folder: Processed data directory path

        Returns:
            Dict mapping table names to their column position mappings

        Raises:
            InputValidationError: If validation fails
        """
        table_columns = {}

        for table_name, table in tables.items():
            if not hasattr(table, 'date_columns') or not table.date_columns:
                continue

            try:
                # Find input file from previous step
                input_file = self.validator.find_input_file(
                    table_name,
                    processed_data_folder,
                    prefix="s01"
                )

                # Get required columns list
                required_cols = table.date_columns.copy()
                if table_name == 'patient':
                    required_cols.append('yob')  # Special case for patient table

                # Validate columns and get positions
                positions = self.validator.validate_columns(
                    input_file,
                    required_cols,
                    table_name
                )

                table_columns[table_name] = positions

            except (FileNotFoundError, ValueError) as e:
                raise InputValidationError(f"Error validating {table_name}: {str(e)}")

        return table_columns

    def generate(self, config: Dict[str, Any]) -> str:
        """
        Generate date conversion script.
        
        Args:
            config: Configuration dictionary
            
        Returns:
            Generated script content
            
        Raises:
            GeneratorError: If script generation fails
        """
        self.validate_inputs(config)
        
        # Initialize configurations
        tables = {
            name: TableConfig.from_dict(name, table_config)
            for name, table_config in config['tables'].items()
        }
        
        grid_engine = GridEngineConfig.from_dict(config['grid_engine'])
        grid_engine.validate()
        
        # Validate columns and get their positions
        table_columns = self.validate_table_columns(
            tables,
            config['processed_data_folder']
        )

        if not table_columns:
            self.logger.warning(
                "No tables with date columns found. "
                "Script will be generated but won't perform any conversions."
            )
        
        # Generate script using template
        return self._render_template(
            tables=tables,
            processed_data_folder=config['processed_data_folder'],
            grid_engine=grid_engine,
            table_columns=table_columns
        )
