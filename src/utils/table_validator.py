import os
import glob
from typing import Dict, List, Optional
import logging

class TableValidator:
    """Utility class to validate table columns and track positions."""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)

    def get_header_columns(self, file_path: str) -> List[str]:
        """Get column names from file header."""
        try:
            with open(file_path, 'r') as f:
                header = f.readline().strip().split('\t')
            return header
        except IOError as e:
            raise ValueError(f"Error reading header from {file_path}: {str(e)}")

    def validate_columns(
        self,
        file_path: str,
        required_columns: List[str],
        table_name: str
    ) -> Dict[str, int]:
        """
        Validate required columns exist in file and get their positions.
        
        Args:
            file_path: Path to the file to validate
            required_columns: List of required column names
            table_name: Name of the table being validated
            
        Returns:
            Dict mapping column names to their 1-based positions (for awk)
            
        Raises:
            ValueError: If required columns are missing
        """
        header = self.get_header_columns(file_path)
        positions = {col: idx + 1 for idx, col in enumerate(header)}
        
        missing_cols = [col for col in required_columns if col not in positions]
        if missing_cols:
            raise ValueError(
                f"Required columns missing in {table_name}:\n"
                f"Missing: {missing_cols}\n"
                f"Available columns: {header}"
            )
            
        return positions

    def find_input_file(
        self,
        table_name: str,
        output_dir: str,
        prefix: str = "s01"
    ) -> str:
        """
        Find input file for a table with given prefix.
        
        Args:
            table_name: Name of the table
            output_dir: Output directory path
            prefix: Expected file prefix (e.g., "s01" for step 1 output)
            
        Returns:
            Path to the input file
            
        Raises:
            FileNotFoundError: If input file doesn't exist
        """
        file_path = os.path.join(
            os.path.expandvars(output_dir),
            table_name,
            f"{prefix}_{table_name}.txt"
        )
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(
                f"Required input file not found: {file_path}"
            )
            
        return file_path
