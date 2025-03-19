from enum import Enum
from typing import List

class PipelineStep(Enum):
    CONCATENATE = 'concatenate'
    CONVERT_DATES = 'convert_dates'
    APPLY_LOOKUPS = 'apply_lookups'
    PREPARE_CODELISTS = 'prepare_codelists'
    ANNOTATE_TABLES = 'annotate_tables'
    CREATE_DATABASE = 'create_database'
    
    @classmethod
    def get_all_steps(cls) -> List[str]:
        """Get list of all possible steps in correct order."""
        return [step.value for step in cls]
    
    @classmethod
    def validate_step(cls, step: str) -> bool:
        """Validate if a step name is valid."""
        return step in cls.get_all_steps()
    
    @classmethod
    def get_step_number(cls, step: str) -> int:
        """Get the fixed step number regardless of which steps are being run."""
        try:
            return cls.get_all_steps().index(step) + 1
        except ValueError:
            raise ValueError(f"Invalid step: {step}")
    
    @classmethod
    def get_step_dependencies(cls) -> dict:
        """Define dependencies between steps."""
        return {
            cls.CONCATENATE.value: [],
            cls.CONVERT_DATES.value: [cls.CONCATENATE.value],
            cls.APPLY_LOOKUPS.value: [cls.CONVERT_DATES.value],
            cls.PREPARE_CODELISTS.value: [],
            cls.ANNOTATE_TABLES.value: [cls.APPLY_LOOKUPS.value, cls.PREPARE_CODELISTS.value],
            cls.CREATE_DATABASE.value: [cls.ANNOTATE_TABLES.value]
        }
