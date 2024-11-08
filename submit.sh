#!/bin/bash
#$ -cwd
#$ -j y
#$ -o logs/

module load miniconda
conda activate cprdpipeline

python new_run.py -c new.yaml -o $PWD/generated_scripts -s annotate_tables