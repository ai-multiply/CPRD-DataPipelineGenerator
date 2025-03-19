from dataclasses import dataclass
from typing import Dict, List, Optional

@dataclass
class TableConfig:
    name: str
    subfolder_pattern: str
    file_pattern: str
    date_columns: List[str]
    lookup_columns: Dict[str, str]  # column_name: lookup_file
    codelist_annotations: Dict[str, str]  # column_name: codelist_name
    additional_files: Dict[str, str]

    @classmethod
    def from_dict(cls, name: str, config: Dict) -> 'TableConfig':
        """Create TableConfig from dict."""
        return cls(
            name=name,
            file_pattern=config['file_pattern'],
            date_columns=config.get('date_columns', []),
            lookup_columns=config.get('lookup_columns', {}),
            codelist_annotations=config.get('codelist_annotations', {}),
            additional_files=config.get('additional_files', {})
        )

    def validate(self):
        """Validate table configuration."""
        if not self.name:
            raise ValueError("Table name cannot be empty")
        if not self.file_pattern:
            raise ValueError(f"File pattern missing for table {self.name}")
        
        # Validate lookup column references
        for col, lookup_file in self.lookup_columns.items():
            if not lookup_file.endswith('.txt'):
                raise ValueError(f"Invalid lookup file format for {col}: {lookup_file}")
