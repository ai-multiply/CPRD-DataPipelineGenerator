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
        Find all input files for a given table across all Part folders.
        Enhanced logging for debugging.
        
        Args:
            table: Table configuration
            raw_data_config: Raw data configuration with root_folder and pattern
                
        Returns:
            List of file paths matching the pattern
                
        Raises:
            FileNotFoundError: If no files are found
        """
        root_folder = raw_data_config['root_folder']
        self.logger.info(f"Searching in root folder: {root_folder}")
        
        # Log the table configuration
        self.logger.info(f"Processing table: {table.name}")
        self.logger.info(f"Subfolder pattern: '{getattr(table, 'subfolder_pattern', '')}'")
        self.logger.info(f"File pattern: {table.file_pattern}")
        
        # Check for direct file path
        if hasattr(table, 'file_path') and table.file_path:
            file_path = os.path.join(root_folder, table.file_path)
            self.logger.info(f"Using direct file path: {file_path}")
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"File not found: {file_path}")
            return [file_path]

        # First find all Part folders
        part_search = os.path.join(root_folder, "Part[0-9]*")
        self.logger.info(f"Searching for Part folders with pattern: {part_search}")
        
        part_folders = sorted(glob.glob(part_search))
        self.logger.info(f"Found {len(part_folders)} Part folders:")
        for folder in part_folders:
            self.logger.info(f"  - {folder}")
        
        if not part_folders:
            raise FileNotFoundError(f"No Part folders found in {root_folder}")
        
        all_files = []
        for part_folder in part_folders:
            # Construct search path based on whether subfolder is specified
            if table.subfolder_pattern:
                search_path = os.path.join(part_folder, table.subfolder_pattern, table.file_pattern)
            else:
                search_path = os.path.join(part_folder, table.file_pattern)
                
            self.logger.info(f"Searching in {part_folder} with path: {search_path}")
                
            # Find matching files in this Part folder
            files = sorted(glob.glob(search_path))
            if files:
                all_files.extend(files)
                self.logger.info(
                    f"Found {len(files)} files in {os.path.basename(part_folder)}"
                    f"{f'/{table.subfolder_pattern}' if table.subfolder_pattern else ''}"
                )
                self.logger.debug("Files found:")
                for file in files:
                    self.logger.debug(f"  - {file}")
            else:
                self.logger.warning(f"No files found in {search_path}")
        
        if not all_files:
            search_pattern = os.path.join(
                "Part*",
                table.subfolder_pattern if table.subfolder_pattern else '',
                table.file_pattern
            )
            raise FileNotFoundError(
                f"No files found for table {table.name} with pattern: {search_pattern}"
            )
                
        self.logger.info(
            f"Found total of {len(all_files)} files for table {table.name} "
            f"across {len(part_folders)} part folders"
        )
        
        # Log first and last few files to verify ordering
        self.logger.info("First 3 files:")
        for file in all_files[:3]:
            self.logger.info(f"  - {file}")
        self.logger.info("Last 3 files:")
        for file in all_files[-3:]:
            self.logger.info(f"  - {file}")
            
        return all_files

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
