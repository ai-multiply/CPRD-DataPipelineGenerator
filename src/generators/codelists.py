from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Set
import os
import logging
from pathlib import Path

from src.generators.base import BaseGenerator
from src.generators.exceptions import InputValidationError, FileNotFoundError, ConfigurationError

@dataclass
class CodelistConfig:
    """Configuration for a single codelist."""
    id: str
    original: Optional[str]
    user: Optional[str]
    
    @classmethod
    def from_dict(cls, id: str, config: Dict) -> 'CodelistConfig':
        return cls(
            id=id,
            original=config.get('original'),
            user=config.get('user')
        )
    
    def get_type(self) -> str:
        """Determine which of the three cases this codelist represents."""
        if self.original and not self.user:
            return 'original_only'
        elif self.user and not self.original:
            return 'user_only'
        elif self.original and self.user:
            return 'combined'
        else:
            raise ConfigurationError(f"Invalid codelist configuration for {self.id}: "
                                   "Must specify at least original or user codelist")

class CodelistGenerator(BaseGenerator):
    """Generator for preparing reference codelists with enhanced column handling."""

    def __init__(self, logger: logging.Logger = None):
        super().__init__(
            template_name='prepare_codelists',
            logger=logger or logging.getLogger(__name__)
        )
        
    def validate_inputs(self, config: Dict[str, Any]):
        """Validate all required inputs are present and valid."""
        required_keys = ['codelists', 'codelists_folder', 'script_output_dir', 'grid_engine']
        missing_keys = [key for key in required_keys if key not in config]
        if missing_keys:
            raise InputValidationError(f"Missing required configuration keys: {missing_keys}")

        # Validate directories exist
        codelists_folder = os.path.expandvars(config['codelists_folder'])
        if not os.path.isdir(codelists_folder):
            raise InputValidationError(
                f"Codelists directory does not exist: {codelists_folder}"
            )

        # Parse and validate codelist configurations
        self.codelists = {}
        for codelist_id, codelist_config in config['codelists'].items():
            self.codelists[codelist_id] = CodelistConfig.from_dict(
                codelist_id, 
                codelist_config
            )

    def validate_file_format(self, file_path: str, min_columns: int = 2) -> List[str]:
        """
        Validate file format and return column headers.
        
        Args:
            file_path: Path to codelist file
            min_columns: Minimum required columns
            
        Returns:
            List of column headers
            
        Raises:
            ConfigurationError: If file format is invalid
        """
        try:
            with open(file_path, 'r') as f:
                header = f.readline().strip().split('\t')
                
            if len(header) < min_columns:
                raise ConfigurationError(
                    f"Insufficient columns in {os.path.basename(file_path)}: "
                    f"found {len(header)}, expected at least {min_columns}"
                )
            
            return header
            
        except Exception as e:
            raise ConfigurationError(
                f"Error reading {os.path.basename(file_path)}: {str(e)}"
            )

    def validate_codelist_files(self, codelists_folder: str):
        """
        Validate all codelist files exist and have correct formats.
        
        Args:
            codelists_folder: Directory containing codelist files
            
        Raises:
            FileNotFoundError: If required files don't exist
            ConfigurationError: If file format is invalid
        """
        missing_files = []
        
        for codelist_id, config in self.codelists.items():
            codelist_type = config.get_type()
            
            if codelist_type in ['original_only', 'combined']:
                if not os.path.isfile(os.path.join(codelists_folder, config.original)):
                    missing_files.append(
                        f"- {config.original} (original codelist for {codelist_id})"
                    )
                else:
                    # Validate original codelist has at least code and description
                    self.validate_file_format(
                        os.path.join(codelists_folder, config.original),
                        min_columns=2
                    )
            
            if codelist_type in ['user_only', 'combined']:
                if not os.path.isfile(os.path.join(codelists_folder, config.user)):
                    missing_files.append(
                        f"- {config.user} (user codelist for {codelist_id})"
                    )
                else:
                    # Validate user codelist has 2-3 columns
                    headers = self.validate_file_format(
                        os.path.join(codelists_folder, config.user),
                        min_columns=2
                    )
                    if len(headers) > 3:
                        raise ConfigurationError(
                            f"Too many columns in {config.user}: "
                            f"found {len(headers)}, expected 2-3"
                        )
        
        if missing_files:
            raise FileNotFoundError(
                "Required codelist files not found:\n" + "\n".join(missing_files)
            )

    def generate(self, config: Dict[str, Any]) -> str:
        """
        Generate codelist preparation script.
        
        Args:
            config: Configuration dictionary
            
        Returns:
            Generated script content
            
        Raises:
            GeneratorError: If script generation fails
        """
        self.validate_inputs(config)
        
        # Validate codelist files
        self.validate_codelist_files(config['codelists_folder'])
        
        # Initialize grid engine config
        grid_engine = config['grid_engine']
        if not isinstance(grid_engine, dict):
            raise ConfigurationError("Invalid grid engine configuration")
        
        # Generate script using template
        return self._render_template(
            codelists=self.codelists,
            codelists_folder=config['codelists_folder'],
            script_output_dir=config['script_output_dir'],
            grid_engine=grid_engine
        )