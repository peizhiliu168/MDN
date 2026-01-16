import os
import networkx as nx
from qiskit import QuantumCircuit
from networkx.algorithms import isomorphism
import collections
import matplotlib.pyplot as plt
from graph_builder import build_graph_from_circuit
from visualizer import visualize_graph
import sys
import concurrent.futures
import random
import argparse

def get_qasm_files(root_dir):
    qasm_files = []
    for root, dirs, files in os.walk(root_dir):
        for file in files:
            if file.endswith(".qasm"):
                qasm_files.append(os.path.join(root, file))
    return qasm_files

def get_canon_label(g):
    # weisfeiler_lehman_graph_hash does not support MultiDiGraph.
    # We convert to DiGraph with edge weights representing multiplicity.
    if isinstance(g, nx.MultiDiGraph):
        dg = nx.DiGraph()
        for n, d in g.nodes(data=True):
            dg.add_node(n, **d)
        
        edge_counts = collections.defaultdict(int)
        for u, v in g.edges():
            edge_counts[(u, v)] += 1
            
        for (u, v), count in edge_counts.items():
            dg.add_edge(u, v, count=str(count)) # Use string for categorical hash
            
        return nx.weisfeiler_lehman_graph_hash(dg, node_attr='name', edge_attr='count')
    else:
        return nx.weisfeiler_lehman_graph_hash(g, node_attr='name')

def build_graph_safe(file_path):
    """
    Worker function to build a graph from a QASM file.
    Returns (file_path, G) or (file_path, None) if failed.
    """
    try:
        qc = QuantumCircuit.from_qasm_file(file_path)
        G = build_graph_from_circuit(qc)
        return (file_path, G)
    except Exception as e:
        return (file_path, None)

def find_subgraphs_of_size_k(G, k):
    """
    Finds all connected induced subgraphs of size k in G (Exhaustive).
    Returns a set of frozenset(nodes).
    """
    if k < 1:
        return set()
    
    current_subgraphs = {frozenset([n]) for n in G.nodes()}
    
    for size in range(2, k + 1):
        next_subgraphs = set()
        for nodes in current_subgraphs:
            neighborhood = set()
            for n in nodes:
                neighborhood.update(G.successors(n))
                neighborhood.update(G.predecessors(n))
            
            neighborhood.difference_update(nodes)
            
            for neighbor in neighborhood:
                new_subgraph = set(nodes)
                new_subgraph.add(neighbor)
                next_subgraphs.add(frozenset(new_subgraph))
                
        current_subgraphs = next_subgraphs
        if not current_subgraphs:
            break
            
    return current_subgraphs

def sample_subgraphs_of_size_k(G, k, num_samples=2000):
    """
    Samples connected induced subgraphs of size k in G.
    Returns a list of frozenset(nodes).
    """
    samples = []
    nodes = list(G.nodes())
    if not nodes:
        return []

    for _ in range(num_samples):
        # 1. Pick random start node
        curr_nodes = {random.choice(nodes)}
        
        # 2. Iteratively expand
        valid_sample = True
        for _ in range(k - 1):
            # Find neighbors of current set
            neighbors = set()
            for n in curr_nodes:
                neighbors.update(G.successors(n))
                neighbors.update(G.predecessors(n))
            
            neighbors.difference_update(curr_nodes)
            
            if not neighbors:
                valid_sample = False
                break
                
            # Pick random neighbor
            next_node = random.choice(list(neighbors))
            curr_nodes.add(next_node)
            
        if valid_sample:
            samples.append(frozenset(curr_nodes))
            
    return samples

def mine_graph_k(args):
    """
    Worker function to mine patterns of size k from a single graph G.
    args: (G, k, g_idx, num_samples, use_sampling)
    Returns: (g_idx, hash_counts, total_units, dict_of_examples)
    """
    G, k, g_idx, num_samples, use_sampling = args
    if G is None:
        return (g_idx, collections.Counter(), 0, {})
    
    if G.number_of_nodes() < k:
         return (g_idx, collections.Counter(), 0, {})

    if use_sampling:
        subgraphs = sample_subgraphs_of_size_k(G, k, num_samples)
    else:
        # Exhaustive search
        subgraphs = find_subgraphs_of_size_k(G, k)
        # Convert set to list for consistent processing logic
        subgraphs = list(subgraphs)

    total_units = len(subgraphs)
    
    hash_counts = collections.Counter()
    examples = {}
    
    for nodes in subgraphs:
        sub_G = G.subgraph(nodes).copy()
        h = get_canon_label(sub_G)
        
        hash_counts[h] += 1
        
        if h not in examples:
            examples[h] = sub_G
            
    return (g_idx, hash_counts, total_units, examples)

def mine_patterns(root_dir, min_support=0.5, k_max=3, num_samples=2000, use_sampling=True):
    files = get_qasm_files(root_dir)
    print(f"Found {len(files)} QASM files.")
    
    graphs = []
    
    print("Building graphs in parallel...")
    with concurrent.futures.ProcessPoolExecutor() as executor:
        results = executor.map(build_graph_safe, files)
        
        for file_path, G in results:
            if G is not None:
                graphs.append(G)
                
    print(f"Successfully built {len(graphs)} graphs.")
    
    mode_str = f"Sampling {num_samples} per graph" if use_sampling else "Exhaustive Search"
    
    for k in range(2, k_max + 1):
        print(f"Mining size {k} patterns ({mode_str})...")
        global_pattern_counts = collections.Counter()
        global_total_units = 0
        pattern_examples = {} 
        
        worker_args = [(G, k, i, num_samples, use_sampling) for i, G in enumerate(graphs)]
        
        with concurrent.futures.ProcessPoolExecutor() as executor:
            results = executor.map(mine_graph_k, worker_args, chunksize=1)
            
            for g_idx, hash_counts, total_units, examples in results:
                global_total_units += total_units
                global_pattern_counts.update(hash_counts)
                
                for h in hash_counts:
                    if h not in pattern_examples:
                        pattern_examples[h] = examples[h]

        # Filter by support
        print(f"  Found {len(global_pattern_counts)} unique patterns of size {k}")
        print(f"  Total subgraphs/samples analyzed: {global_total_units}")
        
        sorted_patterns = sorted(global_pattern_counts.items(), key=lambda x: x[1], reverse=True)
        
        for i, (h, count) in enumerate(sorted_patterns[:5]):
             if global_total_units > 0:
                 frequency = count / global_total_units
             else:
                 frequency = 0
                 
             print(f"  Pattern {h[:8]}... Freq: {frequency:.2%} ({count}/{global_total_units})")
             # Print structure glimpse
             example = pattern_examples[h]
             names = [example.nodes[n]['name'] for n in example.nodes]
             print(f"    Nodes: {names}")
             print(f"    Edges: {len(example.edges())}")
             
             # Visualize top 3 patterns
             if i < 3:
                 output_filename = f"pattern_k{k}_rank{i+1}.png"
                 title = f"Pattern k={k} Rank {i+1} | Freq: {frequency:.1%} ({count}/{global_total_units})"
                 try:
                     visualize_graph(example, output_filename, title=title)
                     print(f"    Saved visualization to {output_filename}")
                 except Exception as e:
                     print(f"    Failed to visualize: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Mine frequent communication patterns in QASM circuits.")
    parser.add_argument("directory", type=str, help="Directory containing QASM files")
    parser.add_argument("k_max", type=int, nargs="?", default=3, help="Maximum subgraph size (k)")
    parser.add_argument("--samples", type=int, default=2000, help="Number of samples per graph (if sampling)")
    parser.add_argument("--exact", action="store_true", help="Use exhaustive search instead of sampling")
    
    args = parser.parse_args()
    
    use_sampling = not args.exact
    
    mine_patterns(args.directory, k_max=args.k_max, num_samples=args.samples, use_sampling=use_sampling)
