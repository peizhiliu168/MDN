#!/bin/bash

# Usage: ./run_batch_mining.sh <k_min> <k_max> [samples] [benchmark1 benchmark2 ...]
# Example: ./run_batch_mining.sh 2 3 2000 adder qft

if [ "$#" -lt 2 ]; then
    echo "Usage: $0 <k_min> <k_max> [samples] [benchmark1 benchmark2 ...]"
    exit 1
fi

K_MIN=$1
K_MAX=$2
SAMPLES=2000

# Shift first two args
shift 2

# Check if the next argument is a number (samples) or a benchmark name
if [[ "$#" -gt 0 && "$1" =~ ^[0-9]+$ ]]; then
    SAMPLES=$1
    shift
fi

BENCHMARK_ROOT="../FTCircuitBench/qasm"
MINER_SCRIPT="pattern_miner.py"

if [ ! -d "$BENCHMARK_ROOT" ]; then
    echo "Error: Benchmark directory $BENCHMARK_ROOT not found."
    exit 1
fi

# If no benchmarks specified, use all directories in root
if [ "$#" -eq 0 ]; then
    TARGET_BENCHMARKS=("$BENCHMARK_ROOT"/*/)
else
    # Build list of directories from arguments
    TARGET_BENCHMARKS=()
    for b in "$@"; do
        if [ -d "$BENCHMARK_ROOT/$b" ]; then
            TARGET_BENCHMARKS+=("$BENCHMARK_ROOT/$b")
        else
            echo "Warning: Benchmark '$b' not found in $BENCHMARK_ROOT, skipping."
        fi
    done
fi

if [ "${#TARGET_BENCHMARKS[@]}" -eq 0 ]; then
    echo "Error: No valid benchmarks found to process."
    exit 1
fi

echo "Starting Batch Mining (Mode: Comm, K_MIN: $K_MIN, K_MAX: $K_MAX, SAMPLES: $SAMPLES)"
echo "Target Benchmarks: ${TARGET_BENCHMARKS[*]}"
echo "--------------------------------------------------------"

for dir in "${TARGET_BENCHMARKS[@]}"; do
    # Remove trailing slash for basename if needed
    dir=${dir%/}
    BENCH_NAME=$(basename "$dir")
    echo "Processing Benchmark: $BENCH_NAME"
    
    ../.venv/bin/python "$MINER_SCRIPT" "$dir" --k-max "$K_MAX" --k-min "$K_MIN" --mode comm --samples "$SAMPLES"
    
    echo "Finished $BENCH_NAME"
    echo "--------------------------------------------------------"
done

echo "Batch Mining Complete. Results saved in 'results/'"
