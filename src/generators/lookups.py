import os
from typing import Dict, Any, List, Set
import logging

from src.generators.base import BaseGenerator
from src.generators.exceptions import InputValidationError, FileNotFoundError, ConfigurationError
from src.config.table_config import TableConfig
from src.config.grid_engine import GridEngineConfig
from src.utils.table_validator import TableValidator

class LookupGenerator(BaseGenerator):
    """Generator for applying lookup tables to convert codes to readable values."""

    def __init__(self, logger: logging.Logger = None):
        super().__init__(
            template_name='apply_lookups',
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
        required_keys = ['tables', 'processed_data_folder', 'lookups_folder', 'grid_engine']
        missing_keys = [key for key in required_keys if key not in config]
        if missing_keys:
            raise InputValidationError(f"Missing required configuration keys: {missing_keys}")

        # Validate directories exist
        for dir_key in ['processed_data_folder', 'lookups_folder']:
            dir_path = os.path.expandvars(config[dir_key])
            if not os.path.isdir(dir_path):
                raise InputValidationError(
                    f"{dir_key} directory does not exist: {dir_path}"
                )

    def validate_lookup_files(
        self,
        lookups_folder: str,
        tables: Dict[str, TableConfig]
    ) -> Set[str]:
        """
        Validate all required lookup files exist.
        
        Args:
            lookups_folder: Directory containing lookup files
            tables: Dictionary of table configurations
            
        Returns:
            Set of validated lookup file paths
            
        Raises:
            FileNotFoundError: If any lookup file is missing
        """
        validated_files = set()
        missing_files = []
        
        for table_name, table in tables.items():
            if not table.lookup_columns:
                continue
                
            for lookup_file in table.lookup_columns.values():
                file_path = os.path.join(lookups_folder, lookup_file)
                if not os.path.isfile(file_path):
                    missing_files.append(f"- {lookup_file} (for {table_name})")
                else:
                    validated_files.add(file_path)
        
        if missing_files:
            raise FileNotFoundError(
                "Missing required lookup files:\n" + "\n".join(missing_files)
            )
            
        return validated_files

    def validate_lookup_formats(self, lookup_files: Set[str]):
        """
        Validate lookup file formats (should be 2-column TSV: code\tdescription).
        
        Args:
            lookup_files: Set of lookup file paths to validate
            
        Raises:
            ConfigurationError: If any lookup file has invalid format
        """
        invalid_files = []
        
        for file_path in lookup_files:
            try:
                with open(file_path, 'r') as f:
                    header = f.readline().strip().split('\t')
                    if len(header) != 2:
                        invalid_files.append(
                            f"- {os.path.basename(file_path)} "
                            f"(found {len(header)} columns, expected 2)"
                        )
            except Exception as e:
                invalid_files.append(
                    f"- {os.path.basename(file_path)} (error: {str(e)})"
                )
        
        if invalid_files:
            raise ConfigurationError(
                "Invalid lookup file formats:\n" + "\n".join(invalid_files) +
                "\nLookup files must be tab-separated with 2 columns: code\\tdescription"
            )

    def get_column_positions(
        self,
        tables: Dict[str, TableConfig],
        processed_data_folder: str
    ) -> Dict[str, Dict[str, int]]:
        """
        Get positions of columns needed for lookups.

        Args:
            tables: Dictionary of table configurations
            processed_data_folder: Processed data directory path

        Returns:
            Dict mapping table names to their column position mappings

        Raises:
            InputValidationError: If validation fails
        """
        col_positions = {}

        for table_name, table in tables.items():
            if not table.lookup_columns:
                continue

            try:
                # Find input file from previous step
                input_file = self.validator.find_input_file(
                    table_name,
                    processed_data_folder,
                    prefix="s02"
                )

                # Validate columns and get positions
                positions = self.validator.validate_columns(
                    input_file,
                    list(table.lookup_columns.keys()),
                    table_name
                )

                col_positions[table_name] = positions

            except (FileNotFoundError, ValueError) as e:
                raise InputValidationError(f"Error validating {table_name}: {str(e)}")

        return col_positions

    def generate(self, config: Dict[str, Any]) -> str:
        """
        Generate lookup application script.
        
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
        
        # Validate lookup files
        lookup_files = self.validate_lookup_files(
            config['lookups_folder'],
            tables
        )
        self.validate_lookup_formats(lookup_files)
        
        # Get column positions
        col_positions = self.get_column_positions(
            tables,
            config['processed_data_folder']
        )

        if not col_positions:
            self.logger.warning(
                "No tables with lookup columns found. "
                "Script will be generated but won't perform any conversions."
        )
        
        # Generate script using template
        return self._render_template(
            tables=tables,
            lookups_folder=config['lookups_folder'],
            processed_data_folder=config['processed_data_folder'],
            grid_engine=grid_engine,
            col_positions=col_positions
        )
