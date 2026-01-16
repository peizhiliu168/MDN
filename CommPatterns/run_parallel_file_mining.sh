#!/bin/bash

# Usage: ./run_parallel_file_mining.sh <benchmark_name> <k_min> <k_max> [samples]
# Example: ./run_parallel_file_mining.sh qft 2 3 2000

if [ "$#" -lt 3 ]; then
    echo "Usage: $0 <benchmark_name> <k_min> <k_max> [samples]"
    exit 1
fi

BENCHMARK_NAME=$1
K_MIN=$2
K_MAX=$3
SAMPLES=${4:-2000}

BENCHMARK_ROOT="../FTCircuitBench/qasm"
TARGET_DIR="$BENCHMARK_ROOT/$BENCHMARK_NAME"
MINER_SCRIPT="pattern_miner.py"
PYTHON_EXEC="../.venv/bin/python"

if [ ! -d "$TARGET_DIR" ]; then
    echo "Error: Benchmark directory $TARGET_DIR not found."
    exit 1
fi

echo "Starting Parallel File Mining for '$BENCHMARK_NAME'"
echo "Mode: Comm, K_MIN: $K_MIN, K_MAX: $K_MAX, SAMPLES: $SAMPLES"
echo "--------------------------------------------------------"

# Find all .qasm files and launch miner in background
count=0
for qasm_file in "$TARGET_DIR"/*.qasm; do
    if [ -f "$qasm_file" ]; then
        echo "Launching mining for: $(basename "$qasm_file")"
        
        # Run mining in background
        "$PYTHON_EXEC" "$MINER_SCRIPT" "$qasm_file" "$K_MAX" --k-min "$K_MIN" --mode comm --samples "$SAMPLES" &
        
        ((count++))
    fi
done

echo "--------------------------------------------------------"
echo "Launched $count analysis jobs in parallel."
echo "Waiting for all jobs to complete..."

wait

echo "All jobs finished. Results saved in 'results/' folders (by filename)."
