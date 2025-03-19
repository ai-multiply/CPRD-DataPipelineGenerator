# CPRD Data Processing Pipeline

A pipeline for processing and standardizing Clinical Practice Research Datalink (CPRD) data, designed for high-performance computing environments with Grid Engine.

## Overview

This pipeline processes CPRD data through several steps, with each step requiring:
1. Generation of the step script using Python
2. Submission and completion of the generated job
3. Verification of success before proceeding to the next step

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

## Pipeline Steps and Execution

The pipeline must be run one step at a time, alternating between generating scripts and running jobs. Available steps are:

| Step Code | Description | Script Name |
|-----------|-------------|-------------|
| `concatenate` | Combines split files | s01_concatenate.sh |
| `convert_dates` | Standardizes date formats | s02_convert_dates.sh |
| `apply_lookups` | Applies reference lookups | s03_apply_lookups.sh |
| `prepare_codelists` | Prepares reference codelists | s04_prepare_codelists.sh |
| `annotate_tables` | Annotates with codelists | s05_annotate_tables.sh |
| `create_database` | Creates SQLite database | s06_create_database.sh |

### Step-by-Step Execution

For each step:
1. Generate the step script
2. Submit and wait for the job to complete
3. Verify successful completion
4. Proceed to generating the next step

**Editing submit.sh**

the submit.sh script contains a line like this:

```bash
python run.py -c new.yaml -o $PWD/generated_scripts -s annotate_tables
```

For each step, modify the -s parameter to specify the correct step code:

1. For concatenation:

```bash
python run.py -c new.yaml -o $PWD/generated_scripts -s concatenate
```

2. For date conversion:

```bash
python run.py -c new.yaml -o $PWD/generated_scripts -s convert_dates
```

And so on for each step in the sequence.

### Important Rules

1. Never generate multiple steps at once: the pipeline generator needs to check the output of previous runs to identify columns
2. Never run multiple jobs simultaneously from different steps: same as above
3. Always verify job completion before generating the next step
4. Use specific step codes when generating scripts (e.g., `apply_lookups`, not `s03`)

### Verifying Job Completion

Before generating the next step, always verify the previous job completed successfully:

1. Check job status:
```bash
qstat
```

2. Review job output:
```bash
more logs/s<XX>_<step_name>.o<job_id>
```

3. Verify output files exist:
```bash
cd /path/to/processed_data/
```

### Listing Available Steps

To see all available step codes:
```bash
python run.py --list-steps
```

### Common issues

* Ensure that there is enough disk space (at least double the current size). Each step will duplicate data. If you are happy with the output, you can delete the file(s) from previous steps.



