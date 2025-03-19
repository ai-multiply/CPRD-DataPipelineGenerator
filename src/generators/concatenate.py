import os
import glob
from pathlib import Path
from typing import Dict, Any, List
import logging

from src.generators.base import BaseGenerator
from src.generators.exceptions import InputValidationError, FileNotFoundError
from src.config.table_config import TableConfig
from src.config.grid_engine import GridEngineConfig

class ConcatenateGenerator(BaseGenerator):
    def __init__(self, logger: logging.Logger = None):
        super().__init__(
            template_name='concatenate',
            logger=logger or logging.getLogger(__name__)
        )

    def validate_inputs(self, config: Dict[str, Any]):
        """
        Validate all required inputs are present and valid.
        
        Args:
            config: Dictionary containing:
                - raw_data: Dict with root_folder and pattern
                - tables: Dict of table configurations
                - processed_data_folder: Output directory path
                - grid_engine: Grid engine configuration
        
        Raises:
            InputValidationError: If validation fails
        """
        required_keys = ['raw_data', 'tables', 'processed_data_folder', 'grid_engine']
        missing_keys = [key for key in required_keys if key not in config]
        if missing_keys:
            raise InputValidationError(f"Missing required configuration keys: {missing_keys}")

        # Validate raw data configuration
        raw_data = config['raw_data']
        if not all(key in raw_data for key in ['root_folder', 'pattern']):
            raise InputValidationError(
                "Raw data configuration must contain 'root_folder' and 'pattern'"
            )

        if not os.path.isdir(raw_data['root_folder']):
            raise InputValidationError(
                f"Raw data directory does not exist: {raw_data['root_folder']}"
            )

        # Validate tables configuration
        if not config['tables']:
            raise InputValidationError("No tables configured")

    def find_input_files(self, table: TableConfig, raw_data_config: Dict[str, str]) -> List[str]:
        """
        Find all input files for a given table using glob patterns.
        
        Args:
            table: Table configuration
            raw_data_config: Raw data configuration with root_folder and pattern
            
        Returns:
            List of file paths matching the pattern
            
        Raises:
            FileNotFoundError: If no files are found
        """
        subfolder = table.subfolder_pattern if hasattr(table, 'subfolder_pattern') and table.subfolder_pattern is not None else ''

        pattern = os.path.join(
            raw_data_config['root_folder'],
            raw_data_config['pattern'],
            subfolder,
            table.file_pattern
        )
        
        files = sorted(glob.glob(pattern, recursive=True))
        
        if not files:
            raise FileNotFoundError(
                f"No files found for table {table.name} with pattern: {pattern}"
            )
            
        self.logger.info(f"Found {len(files)} files for table {table.name}")
        return files

    def generate(self, config: Dict[str, Any]) -> str:
        """
        Generate concatenation script.
        
        Args:
            config: Configuration dictionary
            
        Returns:
            Generated script content
            
        Raises:
            GeneratorError: If script generation fails
        """
        self.validate_inputs(config)
        
        # Find input files for each table
        table_files = {}
        tables: Dict[str, TableConfig] = {}
        
        for name, table_config in config['tables'].items():
            table = TableConfig.from_dict(name, table_config)
            tables[name] = table
            
            try:
                table_files[name] = self.find_input_files(
                    table, 
                    config['raw_data']
                )
            except FileNotFoundError as e:
                self.logger.warning(str(e))
                table_files[name] = []

        # Validate grid engine config
        grid_engine = GridEngineConfig.from_dict(config['grid_engine'])
        grid_engine.validate()

        # Generate script using template
        return self._render_template(
            tables=tables,
            table_files=table_files,
            processed_data_folder=config['processed_data_folder'],
            grid_engine=grid_engine
        )
