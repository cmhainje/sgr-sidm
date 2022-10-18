#!/bin/bash
#SBATCH -J analysis
#SBATCH -p all
#SBATCH -t {{ job_t }}
#SBATCH --mem {{ job_m }}
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=1
#SBATCH --array=0-{{ n_jobs }}
#SBATCH --mail-type=all
#SBATCH --mail-user=chainje@princeton.edu
#SBATCH --output=slurm-%x-%j.out
#SBATCH --error=slurm-%x-%j.out

module purge
module load openmpi/gcc/4.1.0 gsl/2.6 fftw/gcc/openmpi-4.1.0/3.3.9 hdf5/gcc/openmpi-4.1.0/1.10.6 anaconda3/2021.5
conda activate sgr
cd /home/chainje/sgr/
python scripts/analysis.py compute {{ scan_dir }} $(( ${SLURM_ARRAY_TASK_ID} * {{ job_size }} )) $(( ${SLURM_ARRAY_TASK_ID} * {{ job_size }} + {{ job_size }} ))
