from typing import Dict, Any, List, Optional, Set
import os
import logging
import shutil
from pathlib import Path

from src.generators.base import BaseGenerator
from src.generators.exceptions import InputValidationError, FileNotFoundError, ConfigurationError
from src.config.table_config import TableConfig
from src.config.grid_engine import GridEngineConfig
from src.utils.table_validator import TableValidator

class CodelistAnnotationGenerator(BaseGenerator):
    """Generator for annotating tables with codelist descriptions and handling multiple values."""

    def __init__(self, logger=None):
        super().__init__(
            template_name='annotate_tables',
            logger=logger or logging.getLogger(__name__)
        )
        self.validator = TableValidator(self.logger)
        self.tables_to_process = []
        self.table_configs = {}
        self.scripts_dir = None

    def get_declared_codelists(self, config: Dict[str, Any]) -> Set[str]:
        """Get set of codelist IDs declared in the configuration."""
        if 'codelists' not in config:
            raise ConfigurationError(
                "No codelists section found in configuration.\n"
                "Please ensure you have declared your codelists under a 'codelists' key."
            )
        return set(config['codelists'].keys())

    def validate_codelist_references(
        self,
        tables: Dict[str, TableConfig],
        config: Dict[str, Any]
    ) -> None:
        """
        Validate that all referenced codelists are properly declared in configuration.
        
        Args:
            tables: Dictionary of table configurations
            config: Full configuration dictionary containing codelists section
            
        Raises:
            ConfigurationError: If invalid references are found
        """
        # Get declared codelists from config
        declared_codelists = self.get_declared_codelists(config)
        
        missing_refs = []
        invalid_tables = []
        
        for table_name, table in tables.items():
            if not hasattr(table, 'codelist_annotations'):
                invalid_tables.append(
                    f"Table '{table_name}' is missing codelist_annotations configuration"
                )
                continue
                
            for col, codelist_ref in table.codelist_annotations.items():
                # Remove .txt extension if present
                codelist_name = codelist_ref.replace('.txt', '')
                
                if codelist_name not in declared_codelists:
                    missing_refs.append(
                        f"Table '{table_name}' column '{col}' references "
                        f"undeclared codelist '{codelist_name}'"
                    )
        
        errors = []
        if invalid_tables:
            errors.extend(invalid_tables)
        if missing_refs:
            errors.extend(missing_refs)
            errors.append("\nDeclared codelists are:")
            errors.extend(f"- {codelist}" for codelist in sorted(declared_codelists))
            
        if errors:
            raise ConfigurationError("\n".join(errors))

    def validate_codelist_files(
        self,
        tables: Dict[str, TableConfig],
        processed_data_folder: str,
        scripts_dir: str,
        config: Dict[str, Any]
    ) -> Dict[str, Dict[str, Dict[str, Any]]]:
        """
        Validate codelist files exist and get their configurations.

        Args:
            tables: Dictionary of table configurations
            processed_data_folder: Output directory path
            config: Full configuration dictionary

        Returns:
            Dictionary mapping table names to their codelist configurations

        Raises:
            FileNotFoundError: If required files don't exist
        """
        table_configs = {}

        for table_name, table in tables.items():
            if not hasattr(table, 'codelist_annotations') or not table.codelist_annotations:
                continue

            try:
                # Find input file from previous step
                input_file = self.validator.find_input_file(
                    table_name,
                    processed_data_folder,
                    prefix="s03"  # Expected output from lookup step
                )

                # Get and validate column positions
                positions = self.validator.validate_columns(
                    input_file,
                    list(table.codelist_annotations.keys()),
                    table_name
                )

                # Create mapping of column to codelist file paths
                codelist_files = {}
                for col, codelist_name in table.codelist_annotations.items():
                    # Get original codelist config
                    if codelist_name not in config['codelists']:
                        continue  # Already validated in validate_codelist_references

                    codelist_path = os.path.join(
                        scripts_dir,
                        "lists",
                        f"{codelist_name}_terms.txt"
                    )

                    if not os.path.exists(codelist_path):
                        raise FileNotFoundError(
                            f"Codelist file not found: {codelist_path}\n"
                            f"Has the prepare_codelists step been run?"
                        )

                    codelist_files[col] = codelist_path

                table_configs[table_name] = {
                    'positions': positions,
                    'codelists': codelist_files
                }

            except (FileNotFoundError, ValueError) as e:
                raise InputValidationError(f"Error validating {table_name}: {str(e)}")

        return table_configs

    def validate_inputs(self, config: Dict[str, Any]):
        """Validate all required inputs are present and valid."""
        required_keys = ['tables', 'processed_data_folder', 'grid_engine', 'codelists']
        missing_keys = [key for key in required_keys if key not in config]
        if missing_keys:
            raise InputValidationError(f"Missing required configuration keys: {missing_keys}")

        # Validate output directory exists
        processed_data_folder = os.path.expandvars(config['processed_data_folder'])
        if not os.path.isdir(processed_data_folder):
            raise InputValidationError(f"Output directory does not exist: {processed_data_folder}")

        # Initialize tables
        tables = {
            name: TableConfig.from_dict(name, table_config)
            for name, table_config in config['tables'].items()
        }
        
        # Validate codelist references against configuration
        self.validate_codelist_references(tables, config)

        # Validate codelist files and get configurations
        scripts_dir = os.path.expandvars(config['script_output_dir'])
        table_configs = self.validate_codelist_files(tables, processed_data_folder, scripts_dir,  config)
        
        if not table_configs:
            raise InputValidationError(
                "No valid tables found for codelist annotation. "
                "Each table requiring annotations should have:\n"
                "1. A 'codelist_annotations' section in its configuration\n"
                "2. Valid input file from previous pipeline step\n"
                "3. All referenced codelist files present in output directory"
            )

        # Store validated configurations
        self.table_configs = table_configs
        self.tables_to_process = list(table_configs.keys())

    def create_filelist(self, scripts_dir: str) -> str:
        """
        Create filelist for array job processing in the scripts directory.
        
        Args:
            scripts_dir: Directory where generated scripts are saved
            
        Returns:
            Path to created filelist
        """
        filelist_path = os.path.join(scripts_dir, "s05_annotation_filelist.txt")
        with open(filelist_path, 'w') as f:
            for table in self.tables_to_process:
                f.write(f"{table}\n")
        return filelist_path

    def generate(self, config: Dict[str, Any]) -> str:
        """
        Generate codelist annotation script.
        
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
        
        # Get output and scripts directories
        processed_data_folder = os.path.expandvars(config['processed_data_folder'])
        scripts_dir = os.path.expandvars(config['script_output_dir'])
        
        # Ensure directories exist
        os.makedirs(processed_data_folder, exist_ok=True)
        os.makedirs(scripts_dir, exist_ok=True)
        
        # Create filelist in scripts directory
        filelist_path = self.create_filelist(scripts_dir)
        
        # Copy split_rows.py script to scripts directory
        script_source = Path(__file__).parent.parent.parent / 'scripts' / 'split_rows.py'
        
        if not script_source.exists():
            raise FileNotFoundError(
                f"Required script not found: {script_source}\n"
                "Please ensure split_rows.py is present in the scripts directory."
            )
            
        script_dest = os.path.join(scripts_dir, 'split_rows.py')
        shutil.copy2(script_source, script_dest)
        os.chmod(script_dest, 0o755)

        # Process codelist annotations for each table
        # processed_configs = {}
        # for table_name, table in tables.items():
        #     if not hasattr(table, 'codelist_annotations') or not table.codelist_annotations:
        #         continue
        # 
        #     if table_name in self.table_configs:
        #         processed_configs[table_name] = {
        #             'positions': self.table_configs[table_name]['positions'],
        #             'codelist_annotations': table.codelist_annotations
        #         }
        # 
        
        # Generate script using template
        return self._render_template(
            tables=tables,
            processed_data_folder=processed_data_folder,
            scripts_dir=os.path.expandvars(scripts_dir),
            grid_engine=grid_engine,
            table_configs=self.table_configs,
            tables_to_process=self.tables_to_process,
            filelist_path=filelist_path
        )
