#!/bin/bash
#$ -cwd
#$ -j y
#$ -o logs/

module load miniconda
conda activate cprdpipeline

# python run.py -c lizzie.yaml -o $PWD/lizzie_scripts -s concatenate

# python run.py -c lizzie.yaml -o $PWD/lizzie_scripts -s convert_dates

# python run.py -c lizzie.yaml -o $PWD/lizzie_scripts -s apply_lookups

# python run.py -c lizzie.yaml -o $PWD/lizzie_scripts -s prepare_codelists

python run.py -c lizzie.yaml -o $PWD/lizzie_scripts -s annotate_tables