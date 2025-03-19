#!/bin/bash
#$ -cwd
#$ -j y
#$ -o logs/

module load miniconda
conda activate cprdpipeline

python new_run.py -c lizzie.yaml -o $PWD/lizzie_scripts -s concatenate