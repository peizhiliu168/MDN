#!/bin/bash

# Usage: ./run_batch_mining.sh <k_min> <k_max> [samples]
# Example: ./run_batch_mining.sh 2 3 2000

if [ "$#" -lt 2 ]; then
    echo "Usage: $0 <k_min> <k_max> [samples]"
    exit 1
fi

K_MIN=$1
K_MAX=$2
SAMPLES=${3:-2000}

BENCHMARK_ROOT="../FTCircuitBench/qasm"
MINER_SCRIPT="pattern_miner.py"

if [ ! -d "$BENCHMARK_ROOT" ]; then
    echo "Error: Benchmark directory $BENCHMARK_ROOT not found."
    exit 1
fi

echo "Starting Batch Mining (Mode: Comm, K_MIN: $K_MIN, K_MAX: $K_MAX, SAMPLES: $SAMPLES)"
echo "--------------------------------------------------------"

for dir in "$BENCHMARK_ROOT"/*/; do
    if [ -d "$dir" ]; then
        BENCH_NAME=$(basename "$dir")
        echo "Processing Benchmark: $BENCH_NAME"
        
        python3 "$MINER_SCRIPT" "$dir" "$K_MAX" --k-min "$K_MIN" --mode comm --samples "$SAMPLES"
        
        echo "Finished $BENCH_NAME"
        echo "--------------------------------------------------------"
    fi
done

echo "Batch Mining Complete. Results saved in 'results/'"
