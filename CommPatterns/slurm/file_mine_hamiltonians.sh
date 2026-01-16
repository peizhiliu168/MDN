#!/bin/bash
#SBATCH -A p31538
#SBATCH -t 48:00:00
#SBATCH -p normal
#SBATCH --job-name="file_mine_hamiltonians"
#SBATCH --mail-type=BEGIN,END,NONE,FAIL,REQUEUE
#SBATCH --mail-user=peizhiliu2023@u.northwestern.edu
#SBATCH -N 1
#SBATCH --ntasks-per-node=48
#SBATCH --mem=192G
#SBATCH --output=/home/plh2448/projects/MDN/CommPatterns/slurm/file_mine_hamiltonians.out
#SBATCH --error=/home/plh2448/projects/MDN/CommPatterns/slurm/file_mine_hamiltonians.err

source /home/plh2448/projects/MDN/.venv/bin/activate

cd /home/plh2448/projects/MDN/CommPatterns

./run_parallel_file_mining.sh hamiltonians 2 20 100000
