import os
import yaml
import logging
from typing import Dict, List, Optional
from pathlib import Path

from src.generators.concatenate import ConcatenateGenerator
from src.generators.dates import DateConversionGenerator
from src.generators.lookups import LookupGenerator
from src.generators.codelists import CodelistGenerator
from src.generators.annotations import CodelistAnnotationGenerator
from src.generators.database import DatabaseGenerator
from src.pipeline.steps import PipelineStep
from src.utils.logging import setup_logging

class PipelineGenerator:
    def __init__(self, config_path: str):
        """Initialize pipeline generator with configuration file path."""
        self.config = self._load_config(config_path)
        self.logger = setup_logging()
        
        # Initialize generators
        self.generators = {
            PipelineStep.CONCATENATE.value: ConcatenateGenerator(self.logger),
            PipelineStep.CONVERT_DATES.value: DateConversionGenerator(self.logger),
            PipelineStep.APPLY_LOOKUPS.value: LookupGenerator(self.logger),
            PipelineStep.PREPARE_CODELISTS.value: CodelistGenerator(self.logger),
            PipelineStep.ANNOTATE_TABLES.value: CodelistAnnotationGenerator(self.logger),
            PipelineStep.CREATE_DATABASE.value: DatabaseGenerator(self.logger),
            # Add other generators here as they're implemented
        }

    def _load_config(self, config_path: str) -> dict:
        """Load and validate configuration file."""
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        required_fields = ['raw_data', 'processed_data_folder', 'tables', 'grid_engine']
        for field in required_fields:
            if field not in config:
                raise ValueError(f"Missing required field '{field}' in config")
        
        return config

    def write_scripts(self, output_dir: str, steps: List[str] = None):
        """Write specified scripts to output directory."""
        if steps is None:
            steps = PipelineStep.get_all_steps()
        
        # Validate steps
        invalid_steps = [step for step in steps if not PipelineStep.validate_step(step)]
        if invalid_steps:
            raise ValueError(f"Invalid steps specified: {invalid_steps}")
        
        os.makedirs(output_dir, exist_ok=True)
        
        working_config = self.config.copy()
        working_config['script_output_dir'] = output_dir
        
        # Generate scripts for requested steps
        for step in steps:
            if step not in self.generators:
                self.logger.warning(f"Generator not implemented for step: {step}")
                continue
                
            try:
                script_content = self.generators[step].generate(working_config)
                
                # Use fixed step number based on full pipeline order
                step_num = PipelineStep.get_step_number(step)
                filename = f's{step_num:02d}_{step}.sh'
                filepath = os.path.join(output_dir, filename)
                
                with open(filepath, 'w') as f:
                    f.write(script_content)
                os.chmod(filepath, 0o755)
                
                self.logger.info(f"Generated script: {filepath}")
                
            except Exception as e:
                raise
