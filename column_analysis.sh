#!/bin/bash
#$ -cwd
#$ -j y

# Default values
DEFAULT_INPUT_DIR=$(pwd)
DEFAULT_OUTPUT_FILE="table_schemas.txt"

# Parse command line arguments
while getopts "i:o:" opt; do
    case $opt in
        i) INPUT_DIR="$OPTARG";;
        o) OUTPUT_FILE="$OPTARG";;
        \?) echo "Invalid option -$OPTARG" >&2; exit 1;;
    esac
done

# Set defaults if parameters weren't provided
INPUT_DIR=${INPUT_DIR:-$DEFAULT_INPUT_DIR}
OUTPUT_FILE=${OUTPUT_FILE:-$DEFAULT_OUTPUT_FILE}

# Function to determine SQL type based on column content
get_sql_type() {
    local file=$1
    local col=$2
    
    # Skip header row and use tail -n 100 to sample data
    # Look at first 100 non-empty values in the column
    local sample=$(tail -n +2 "$file" | cut -f "$col" | grep -v '^$' | head -n 100)
    
    # Check if all values match real number pattern (including integers)
    if [[ $(echo "$sample" | grep -v '^[+-]\?[0-9]*\.\?[0-9]\+$' | wc -l) -eq 0 ]]; then
        # If we get here, all values are numeric (either integer or real)
        
        # Check if any values contain decimal points
        if [[ $(echo "$sample" | grep '\.' | wc -l) -gt 0 ]]; then
            echo "REAL"
            return
        else
            echo "INTEGER"
            return
        fi
    fi
    
    # Check if values contain dates in format YYYY-MM-DD
    if [[ $(echo "$sample" | grep -E '^[0-9]{4}-[0-9]{2}-[0-9]{2}$' | wc -l) -gt 0 ]]; then
        echo "TEXT"  # Date stored as TEXT in SQLite
        return
    fi
    
    # Default to TEXT for other cases
    echo "TEXT"
}

echo "Analyzing column names and types..."
echo "Input directory: $INPUT_DIR"
echo "Results will be written to $OUTPUT_FILE"

{
    echo "# Generated $(date)"
    echo "# Note: These are suggestions based on data sampling. Please verify before use."
    echo ""
} > "$OUTPUT_FILE"

# Process each table directory
for table_dir in "$INPUT_DIR"/*/ ; do
    if [ ! -d "$table_dir" ]; then
        continue
    fi
    
    table_name=$(basename "$table_dir")
    
    # Find the latest processed file (s04 preferred, fall back to earlier steps)
    for prefix in "s04" "s03" "s02" "s01" "concat"; do
        data_file=$(find "$table_dir" -name "${prefix}_${table_name}.txt" -o -name "${prefix}_*.txt" | head -n 1)
        if [ ! -z "$data_file" ]; then
            break
        fi
    done
    
    if [ -z "$data_file" ]; then
        echo "No data file found for $table_name, skipping..."
        continue
    fi
    
    echo "Processing $table_name..."
    
    {
        echo "${table_name}:"
        echo "  columns:"
        
        # Get header line and number of columns
        header=$(head -n 1 "$data_file")
        num_cols=$(echo "$header" | awk -F'\t' '{print NF}')
        
        for ((i=1; i<=num_cols; i++)); do
            # Just trim any trailing newline, no need for complex cleaning
            col_name=$(echo "$header" | cut -f $i | tr -d '\n')
            sql_type=$(get_sql_type "$data_file" $i)
            printf "    %s: %s\n" "$col_name" "$sql_type"
        done
        echo ""
    } >> "$OUTPUT_FILE"
done

echo "Analysis complete. Results written to $OUTPUT_FILE"
echo "The output is formatted for direct use in your configuration file."
echo "Please review the suggested types before using them."