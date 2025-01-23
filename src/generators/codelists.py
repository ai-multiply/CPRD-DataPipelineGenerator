import os
from typing import Dict, Any, List, Optional
import logging

from src.generators.base import BaseGenerator
from src.generators.exceptions import InputValidationError, FileNotFoundError, ConfigurationError

class CodelistGenerator(BaseGenerator):
    """Generator for preparing reference codelists by combining sources."""

    def __init__(self, logger: logging.Logger = None):
        super().__init__(
            template_name='prepare_codelists',
            logger=logger or logging.getLogger(__name__)
        )

    def validate_inputs(self, config: Dict[str, Any]):
        """
        Validate all required inputs are present and valid.
        
        Args:
            config: Dictionary containing configuration
            
        Raises:
            InputValidationError: If validation fails
        """
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

        # Validate codelist configuration
        codelists = config['codelists']
        if not isinstance(codelists, dict):
            raise InputValidationError("Codelists configuration must be a dictionary")

        for codelist_id, codelist_config in codelists.items():
            if 'original' not in codelist_config:
                raise InputValidationError(
                    f"Codelist '{codelist_id}' missing required field: original"
                )

    def validate_codelist_files(
        self,
        codelists_folder: str,
        codelists: Dict[str, Dict[str, str]]
    ):
        """
        Validate required codelist files exist and have correct format.
        
        Args:
            codelists_folder: Directory containing codelist files
            codelists: Dictionary of codelist configurations
            
        Raises:
            FileNotFoundError: If required files don't exist
            ConfigurationError: If file format is invalid
        """
        missing_files = []
        invalid_files = []
        
        for codelist_id, config in codelists.items():
            # Original codelist is required
            original_path = os.path.join(codelists_folder, config['original'])
            if not os.path.isfile(original_path):
                missing_files.append(
                    f"- {config['original']} (original codelist for {codelist_id})"
                )
                continue
                
            try:
                # Validate original codelist format
                with open(original_path, 'r') as f:
                    header = f.readline().strip().split('\t')
                    if len(header) < 2:  # At minimum need code and description
                        invalid_files.append(
                            f"- {config['original']} (insufficient columns: {len(header)})"
                        )
            except Exception as e:
                invalid_files.append(
                    f"- {config['original']} (error: {str(e)})"
                )
            
            # User codelist is optional but if specified must exist
            if config.get('user'):
                user_path = os.path.join(codelists_folder, config['user'])
                if not os.path.isfile(user_path):
                    missing_files.append(
                        f"- {config['user']} (user codelist for {codelist_id})"
                    )
                    continue
                    
                try:
                    # Validate user codelist format
                    with open(user_path, 'r') as f:
                        header = f.readline().strip().split('\t')
                        if len(header) < 3:  # Need code, description, and count
                            invalid_files.append(
                                f"- {config['user']} (insufficient columns: {len(header)})"
                            )
                except Exception as e:
                    invalid_files.append(
                        f"- {config['user']} (error: {str(e)})"
                    )
        
        if missing_files:
            raise FileNotFoundError(
                "Required codelist files not found:\n" + "\n".join(missing_files)
            )
            
        if invalid_files:
            raise ConfigurationError(
                "Invalid codelist file formats:\n" + "\n".join(invalid_files) +
                "\nOriginal codelists need at least: code\\tdescription\n" +
                "User codelists need: code\\tdescription\\tcount"
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
      self.validate_codelist_files(
          config['codelists_folder'],
          config['codelists']
      )
      
      # Initialize grid engine config
      grid_engine = config['grid_engine']
      if not isinstance(grid_engine, dict):
          raise ConfigurationError("Invalid grid engine configuration")
      
      # Generate script using template - the template will handle path construction
      return self._render_template(
          codelists=config['codelists'],
          codelists_folder=config['codelists_folder'],
          script_output_dir=config['script_output_dir'],
          grid_engine=grid_engine
      )
