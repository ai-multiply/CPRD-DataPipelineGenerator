#!/usr/bin/env python3
"""
Split rows in a tab-delimited file where a specified column contains pipe-separated values.
Treats all data as text to avoid any type conversions.
"""
import sys
import os

def process_file(input_file: str, split_col: int) -> None:
    """
    Split rows where specified column contains pipe-separated values.
    
    Args:
        input_file: Path to input file
        split_col: 1-based column number to split (converting to 0-based internally)
    """
    if not os.path.exists(input_file):
        raise FileNotFoundError(f"Input file not found: {input_file}")
        
    # Convert to 0-based indexing for internal use
    split_col = split_col - 1
    output_file = f"{input_file}.split"
    
    try:
        with open(input_file, 'r') as infile, open(output_file, 'w') as outfile:
            for line in infile:
                fields = line.strip('\n').split('\t')
                
                # If column doesn't exist, write original line
                if len(fields) <= split_col:
                    outfile.write(line)
                    continue
                    
                # Split the target column on pipes
                values = fields[split_col].split('|')
                
                # If no split needed, write original line
                if len(values) <= 1:
                    outfile.write(line)
                    continue
                    
                # Create new row for each split value
                for value in values:
                    new_row = fields.copy()
                    new_row[split_col] = value.strip()
                    outfile.write('\t'.join(new_row) + '\n')
                    
    except Exception as e:
        # Clean up partial output file on error
        if os.path.exists(output_file):
            os.remove(output_file)
        raise RuntimeError(f"Error processing {input_file}: {str(e)}")

def main():
    """Main entry point with argument parsing."""
    if len(sys.argv) != 4:
        print("Usage: split_rows.py <username> <input_file> <column_to_split>", 
              file=sys.stderr)
        sys.exit(1)
    
    _, username, input_file, col_num = sys.argv
    
    try:
        col_num = int(col_num)
        if col_num < 1:
            raise ValueError("Column number must be positive")
    except ValueError as e:
        print(f"Invalid column number '{col_num}': {str(e)}", file=sys.stderr)
        sys.exit(1)
    
    try:
        process_file(input_file, col_num)
    except Exception as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()
