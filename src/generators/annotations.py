from dataclasses import dataclass
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
    """Generator for annotating tables with codelist descriptions and flags."""

    def __init__(self, logger=None):
        super().__init__(
            template_name='annotate_tables',
            logger=logger or logging.getLogger(__name__)
        )
        self.validator = TableValidator(self.logger)
        self.tables_to_process = []
        self.table_configs = {}
        self.scripts_dir = None
        # Add dictionary to track input files for each table
        self.table_input_files = {}

    def get_codelist_format(self, file_path: str) -> Dict[str, Any]:
        """
        Determine the format of a codelist file by reading its header.
        
        Args:
            file_path: Path to the codelist file
            
        Returns:
            Dictionary containing:
                - column_count: Number of columns
                - has_count: Whether file has count column
                - has_flag: Whether file has flag column
                - headers: List of column headers
        """
        try:
            with open(file_path, 'r') as f:
                header = f.readline().strip().split('\t')
                
            return {
                'column_count': len(header),
                'has_count': len(header) == 4,  # Only true for 4-column format
                'has_flag': len(header) == 4,   # Only true for 4-column format
                'headers': header
            }
        except Exception as e:
            raise ConfigurationError(f"Error reading codelist {file_path}: {str(e)}")

    def find_latest_input_file(
        self,
        table_name: str,
        processed_data_folder: str
    ) -> str:
        """
        Find the most recent available input file for a table.
        
        Args:
            table_name: Name of the table
            processed_data_folder: Output directory path
            
        Returns:
            Path to the most recent input file
            
        Raises:
            FileNotFoundError: If no input file is found
        """
        expanded_folder = os.path.expandvars(processed_data_folder)
        table_dir = os.path.join(expanded_folder, table_name)
        
        # Check files in order of preference: s03 -> s02 -> s01
        for step in ['s03', 's02', 's01']:
            file_path = os.path.join(
                table_dir,
                f"{step}_{table_name}.txt"
            )
            if os.path.exists(file_path):
                # Store just the filename part, not the full path
                self.table_input_files[table_name] = f"{step}_{table_name}.txt"
                return file_path
        
        raise FileNotFoundError(
            f"No input file found for table {table_name}.\n"
            f"Checked in {table_dir}:\n"
            f"- s03_{table_name}.txt (from lookups)\n"
            f"- s02_{table_name}.txt (from date conversion)\n"
            f"- s01_{table_name}.txt (from concatenation)"
        )

    def validate_codelist_references(
        self,
        tables: Dict[str, TableConfig],
        config: Dict[str, Any]
    ) -> None:
        """Validate that all referenced codelists are properly declared."""
        if 'codelists' not in config:
            raise ConfigurationError(
                "No codelists section found in configuration.\n"
                "Please ensure you have declared your codelists under a 'codelists' key."
            )
        
        declared_codelists = set(config['codelists'].keys())
        missing_refs = []
        
        # Only check tables that have codelist annotations
        tables_with_codelists = {
            name: table for name, table in tables.items() 
            if table.codelist_annotations
        }
        
        for table_name, table in tables_with_codelists.items():
            for codelist_name in table.codelist_annotations.keys():
                if codelist_name not in declared_codelists:
                    column = table.codelist_annotations[codelist_name]
                    missing_refs.append(
                        f"Table '{table_name}' uses undeclared codelist '{codelist_name}' "
                        f"for column '{column}'"
                    )
        
        if missing_refs:
            error_msg = ["Missing codelist references:"]
            error_msg.extend(missing_refs)
            error_msg.extend([
                "\nDeclared codelists are:",
                *[f"- {codelist}" for codelist in sorted(declared_codelists)]
            ])
            raise ConfigurationError("\n".join(error_msg))

    def validate_codelist_files(
        self,
        tables: Dict[str, TableConfig],
        scripts_dir: str,
        config: Dict[str, Any]
    ) -> Dict[str, Dict[str, Dict[str, Any]]]:
        """Validate codelist files and get their configurations."""
        table_configs = {}

        tables_with_codelists = {
            name: table for name, table in tables.items() 
            if table.codelist_annotations
        }

        for table_name, table in tables_with_codelists.items():
            try:
                input_file = self.find_latest_input_file(
                    table_name,
                    config['processed_data_folder']
                )

                columns_to_codelists = table.get_columns_to_codelists()
                positions = self.validator.validate_columns(
                    input_file,
                    list(columns_to_codelists.keys()),
                    table_name
                )

                column_configs = {}
                for column, codelist_names in columns_to_codelists.items():
                    codelist_files = []
                    for codelist_name in codelist_names:
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

                        # Get format information for this codelist
                        format_info = self.get_codelist_format(codelist_path)
                        
                        if format_info['column_count'] not in [2, 4]:
                            raise ConfigurationError(
                                f"Invalid codelist format in {codelist_path}. "
                                f"Expected 2 columns (code, description) or "
                                f"4 columns (code, description, count, flag). "
                                f"Found {format_info['column_count']} columns."
                            )

                        codelist_files.append({
                            'name': codelist_name,
                            'path': codelist_path,
                            'format': format_info
                        })

                    column_configs[column] = {
                        'position': positions[column],
                        'codelists': codelist_files
                    }

                table_configs[table_name] = column_configs

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
            raise InputValidationError(
                f"Output directory does not exist: {processed_data_folder}"
            )

        # Initialize tables
        tables = {
            name: TableConfig.from_dict(name, table_config)
            for name, table_config in config['tables'].items()
        }
        
        # Validate codelist references against configuration
        self.validate_codelist_references(tables, config)

        # Get scripts directory
        scripts_dir = os.path.expandvars(config['script_output_dir'])
        
        # Validate codelist files and get configurations
        self.table_configs = self.validate_codelist_files(
            tables,
            scripts_dir,
            config
        )
        
        if not self.table_configs:
            raise InputValidationError(
                "No tables found with codelist annotations. "
                "Each table requiring annotations should have:\n"
                "1. A 'codelist_annotations' section in its configuration\n"
                "2. Valid input file from previous pipeline step\n"
                "3. All referenced codelist files present in output directory"
            )

        # Only process tables that have codelist configurations
        self.tables_to_process = list(self.table_configs.keys())
        self.scripts_dir = scripts_dir

    def create_filelist(self) -> str:
        """Create filelist for array job processing."""
        filelist_path = os.path.join(self.scripts_dir, "s05_annotation_filelist.txt")
        with open(filelist_path, 'w') as f:
            for table in self.tables_to_process:
                f.write(f"{table}\n")
        return filelist_path

    def generate(self, config: Dict[str, Any]) -> str:
        """Generate codelist annotation script."""
        self.validate_inputs(config)
        
        # Initialize configurations
        tables = {
            name: TableConfig.from_dict(name, table_config)
            for name, table_config in config['tables'].items()
        }
        
        grid_engine = GridEngineConfig.from_dict(config['grid_engine'])
        grid_engine.validate()
        
        # Get output directories
        processed_data_folder = os.path.expandvars(config['processed_data_folder'])
        
        # Ensure directories exist
        os.makedirs(processed_data_folder, exist_ok=True)
        os.makedirs(self.scripts_dir, exist_ok=True)
        
        # Create filelist
        filelist_path = self.create_filelist()
        
        # Copy split_rows.py script
        script_source = Path(__file__).parent.parent.parent / 'scripts' / 'split_rows.py'
        if not script_source.exists():
            raise FileNotFoundError(
                f"Required script not found: {script_source}\n"
                "Please ensure split_rows.py is present in the scripts directory."
            )
            
        script_dest = os.path.join(self.scripts_dir, 'split_rows.py')
        shutil.copy2(script_source, script_dest)
        os.chmod(script_dest, 0o755)
        
        # Generate script using template
        return self._render_template(
            tables=tables,
            processed_data_folder=processed_data_folder,
            scripts_dir=self.scripts_dir,
            grid_engine=grid_engine,
            table_configs=self.table_configs,
            tables_to_process=self.tables_to_process,
            filelist_path=filelist_path,
            table_input_files=self.table_input_files  # Pass input files to template
        )