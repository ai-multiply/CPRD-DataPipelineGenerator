#!/bin/bash
#$ -cwd
#$ -j y
#$ -pe smp 1
#$ -l h_rt=1:0:0
#$ -l h_vmem=4G

# Exit on any error
set -e

echo "Starting pipeline environment setup" $(date)

# Load required module
module load miniconda

# Install mamba if not already installed
if ! command -v mamba &> /dev/null; then
    echo "Installing mamba..."
    conda install -y -c conda-forge mamba
fi

# Remove existing environment if it exists
mamba env remove -n cprd_pipeline --yes || true

# Create new environment from configuration
mamba env create -f environment.yaml

echo "Setup finished" $(date)
echo "To use the environment: module load miniconda; mamba activate cprd_pipeline"