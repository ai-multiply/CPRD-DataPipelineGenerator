# CPRD Data Processing Pipeline Generator

A pipeline generator for processing and standardising Clinical Practice Research Datalink (CPRD) data, developed by the **AI MULTIPLY** consortium for high-performance computing environments with Grid Engine. The resulting pipeline concatenates raw CPRD files, standardizes date formats, applies lookup tables for code-to-term conversion, prepares and applies reference codelists, and finally creates a structured SQLite database—transforming raw CPRD extracts into research-ready datasets optimised for analysis. The pipeline is compatible with both CPRD GOLD and CPRD Aurum datasets. Whilst a job-based HPC system is not required, alternative multi-core setups must be used to speed up jobs.

## Overview

This repository contains a **pipeline generator** that creates customised data processing scripts for CPRD data. The key concepts are:

1. The Python code in this repository is not the pipeline itself, but rather a **generator** that creates the actual pipeline scripts
2. The pipeline processes CPRD data through several sequential steps to transform raw data extracts into a standardised research database
3. **Each step must complete before the next can be generated**
4. The system validates outputs at each stage to ensure data integrity and consistent processing

## AI MULTIPLY Consortium

This pipeline generator is part of the AI MULTIPLY consortium's data infrastructure, designed to standardise and prepare clinical data for AI and machine learning applications. The pipeline maintains data provenance and ensures consistent processing across multiple datasets.

## Prerequisites

- Grid Engine environment
- Miniconda/Mamba
- Python 3.8+
- GNU Parallel
- SQLite 3.36.0+

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd cprd-pipeline
```

2. Set up the conda environment:
```bash
qsub setup_pipeline.sh
```

## Configuration

1. Copy the example configuration:
```bash
cp example.yaml my_config.yaml
```

2. Edit `my_config.yaml` to specify:
   - Grid engine parameters
   - Data locations
   - Table configurations
   - Codelist mappings

## Pipeline Generation and Execution Workflow

### ⚠️ IMPORTANT: Sequential Generation Requirement ⚠️

This is a **pipeline generator** with a strict sequential workflow:

1. Generate a step script - verify that the Grid engine parameters as appropriate (i.e. increase or decrease number of cores as required)
2. Run that step to completion
3. **Only then** generate the next step script
4. Continue this pattern for all steps

The generator analyses the output of each step to determine the correct configuration for the next step. **Attempting to generate multiple steps at once will result in errors or incorrect processing.**

### Available Pipeline Steps

| Step Code | Description | Script Name |
|-----------|-------------|-------------|
| `concatenate` | Combines split files | s01_concatenate.sh |
| `convert_dates` | Standardizes date formats | s02_convert_dates.sh |
| `apply_lookups` | Applies reference lookups | s03_apply_lookups.sh |
| `prepare_codelists` | Prepares reference codelists | s04_prepare_codelists.sh |
| `annotate_tables` | Annotates with codelists | s05_annotate_tables.sh |
| `create_database` | Creates SQLite database | s06_create_database.sh |

### Step-by-Step Execution Workflow

For each step in the pipeline:

1. **Generate the script** for the current step:
   ```bash
   python run.py -c my_config.yaml -o $PWD/generated_scripts -s <step_name>
   ```

2. **Submit the job** and wait for it to complete:
   ```bash
   qsub generated_scripts/s<XX>_<step_name>.sh
   ```

3. **Verify successful completion** (check job status, log files, and output files)

4. **Only after verification**, generate the script for the next step

### Using submit.sh

The `submit.sh` script contains a template for generating scripts:

```bash
python run.py -c lizzie.yaml -o $PWD/lizzie_scripts -s annotate_tables
```

Edit this file to specify:
- The correct configuration file (`-c` parameter)
- The output directory (`-o` parameter)
- The current step to generate (`-s` parameter)

**Remember**: Only generate one step at a time, and only after the previous step has successfully completed.

### Verifying Job Completion

Before generating the next step's script, verify the previous job completed successfully:

1. Check job status:
   ```bash
   qstat
   ```

2. Review job output:
   ```bash
   more logs/s<XX>_<step_name>.o<job_id>
   ```

3. Verify output files exist in the processed data directory:
   ```bash
   ls -l /path/to/processed_data/<table_name>/
   ```

### Listing Available Steps

To see all available step codes:
```bash
python run.py --list-steps
```

## Common Issues and Solutions

* **Disk Space**: Ensure sufficient space (at least double the current size). Each step duplicates data. You can delete files from previous steps after verification.

* **Missing Dependencies**: If you encounter module errors, ensure all requirements are installed via the conda environment.

* **Job Failures**: Always check job logs in the logs directory for error messages.

* **File Path Issues**: Verify all paths in your configuration file; expand any environment variables manually to check actual paths.




