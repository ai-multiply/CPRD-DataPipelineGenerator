#!/bin/bash
#$ -cwd
#$ -j y

INPUT_DIR=/data/scratch/$USER/ImportData/temp
OUTPUT_FILE="table_schemas.txt"

# Function to determine SQL type based on column content
get_sql_type() {
    local file=$1
    local col=$2
    
    # Skip header row and use tail -n 1000 to sample data
    # Look at first 1000 non-empty values in the column
    local sample=$(tail -n +2 "$file" | cut -f "$col" | grep -v '^$' | head -n 1000)
    
    # Check if all values are numeric
    if [[ $(echo "$sample" | grep -v '^[0-9]*$' | wc -l) -eq 0 ]]; then
        echo "INTEGER"
        return
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
        
        # Process each column
        for ((i=1; i<=num_cols; i++)); do
            col_name=$(echo "$header" | cut -f $i)
            sql_type=$(get_sql_type "$data_file" $i)
            echo "    ${col_name}: ${sql_type}"
        done
        echo ""
    } >> "$OUTPUT_FILE"
    
done

echo "Analysis complete. Results written to $OUTPUT_FILE"
echo "The output is formatted for direct use in your configuration file."
echo "Please review the suggested types before using them."