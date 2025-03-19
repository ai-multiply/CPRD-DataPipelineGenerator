from dataclasses import dataclass
from typing import Dict, List, Optional
from collections import defaultdict

@dataclass
class TableConfig:
    name: str
    subfolder_pattern: str
    file_pattern: str
    file_path: Optional[str]
    date_columns: List[str]
    lookup_columns: Dict[str, str]  # column_name: lookup_file
    codelist_annotations: Dict[str, str]  # column_name: codelist_name
    additional_files: Dict[str, str]

    @classmethod
    def from_dict(cls, name: str, config: Dict) -> 'TableConfig':
        """Create TableConfig from dict."""
        return cls(
            name=name,
            subfolder_pattern=config.get('subfolder_pattern', ''),
            file_pattern=config.get('file_pattern', ''),
            file_path=config.get('file_path'),
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

    def get_columns_to_codelists(self) -> Dict[str, List[str]]:
        """
        Get a mapping of columns to their associated codelists.
        
        Returns:
            Dictionary mapping column names to lists of codelist names that annotate them
        """
        column_to_codelists = defaultdict(list)
        for codelist_name, column in self.codelist_annotations.items():
            column_to_codelists[column].append(codelist_name)
        return dict(column_to_codelists)