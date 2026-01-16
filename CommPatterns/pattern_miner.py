import os
import networkx as nx
from qiskit import QuantumCircuit
from networkx.algorithms import isomorphism
import collections
import matplotlib.pyplot as plt
from graph_builder import build_graph_from_circuit, build_interaction_graph
from visualizer import visualize_graph, visualize_interaction_graph
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

def get_canon_label(g, mode='dataflow'):
    """
    Computes canonical label (hash) for the graph.
    - mode='dataflow': Matches by Node Type (Operation Name). Edges just purely connectivity (plus count).
    - mode='comm': Matches by Edge Type (Interaction/Flow). Nodes are generic.
    """
    # weisfeiler_lehman_graph_hash does not support MultiDiGraph directly.
    # consistently convert to DiGraph.
    
    dg = nx.DiGraph()
    for n, d in g.nodes(data=True):
        # Allow Generic Node matching for 'comm' mode
        if mode == 'comm':
            dg.add_node(n, generic_label='node', **d)
        else:
            dg.add_node(n, **d)
    
    # Process edges
    edge_attrs = collections.defaultdict(list)
    for u, v, data in g.edges(data=True):
        # We need to aggregate edge attributes for parallel edges
        if mode == 'comm':
             # Combine type + label (if exists) e.g. "interaction_cx", "flow_None"
             etype = data.get('type', 'unknown')
             elabel = data.get('label', '')
             full_tag = f"{etype}_{elabel}"
             edge_attrs[(u, v)].append(full_tag)
        else:
             # Dataflow mode: just count edges
             edge_attrs[(u, v)].append('edge') # Placeholder, we count length later
             
    for (u, v), attrs in edge_attrs.items():
        if mode == 'comm':
            # Sort attributes to ensure canonical representation of parallel edges
            sorted_attrs = sorted(attrs)
            # Join into a single string
            combined_attr = "|".join(sorted_attrs)
            dg.add_edge(u, v, hash_label=combined_attr)
        else:
            # Dataflow mode: replicate original logic (count as edge attribute)
            count = len(attrs)
            dg.add_edge(u, v, count=str(count)) 

    if mode == 'comm':
        # Match by edge type, ignore node name
        return nx.weisfeiler_lehman_graph_hash(dg, node_attr='generic_label', edge_attr='hash_label')
    else:
        # Match by node name, edge counts
        return nx.weisfeiler_lehman_graph_hash(dg, node_attr='name', edge_attr='count')

def build_graph_safe(args):
    """
    Worker function to build a graph from a QASM file.
    Returns (file_path, G) or (file_path, None) if failed.
    args: (file_path, mode)
    """
    file_path, mode = args
    try:
        qc = QuantumCircuit.from_qasm_file(file_path)
        if mode == 'comm':
            G = build_interaction_graph(qc)
        else:
            G = build_graph_from_circuit(qc)
        return (file_path, G)
    except Exception as e:
        # print(f"Error building {file_path}: {e}")
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

def count_interaction_edges(G_sub):
    count = 0
    for u, v, data in G_sub.edges(data=True):
        if data.get('type') == 'interaction':
            count += 1
    return count

def sample_subgraphs_by_interaction_k(G, k, num_samples=2000):
    """
    Samples connected subgraphs that contain exactly k interaction edges.
    Used for 'comm' mode.
    """
    samples = []
    
    # 1. Identify all interaction edges to start from
    interaction_edges = []
    for u, v, data in G.edges(data=True):
         if data.get('type') == 'interaction':
             interaction_edges.append((u, v))
             
    if not interaction_edges:
        return []
        
    for _ in range(num_samples):
        # Start with a random interaction edge
        start_u, start_v = random.choice(interaction_edges)
        curr_nodes = {start_u, start_v}
        
        # Check current count (should be >= 1)
        sub = G.subgraph(curr_nodes)
        curr_k = count_interaction_edges(sub)
        
        # If we start with > k, we can't do anything (unless we shrink, but ignoring for now)
        if curr_k > k:
            continue 
        
        if curr_k == k:
            samples.append(frozenset(curr_nodes))
            continue
            
        # Expand
        valid_sample = False
        # Limit expansion attempts
        # Limit expansion attempts
        max_attempts = k * 10 
        for _ in range(max_attempts):
            # Find neighbors
            neighbors = set()
            for n in curr_nodes:
                neighbors.update(G.successors(n))
                neighbors.update(G.predecessors(n))
            
            neighbors.difference_update(curr_nodes)
            
            if not neighbors:
                break 
                
            # Pick random neighbor
            next_node = random.choice(list(neighbors))
            
            # Identify "Atomic Unit": next_node + all its interaction partners
            nodes_to_add = {next_node}
            
            # Check outgoing interaction edges from next_node
            for succ in G.successors(next_node):
                # G is MultiDiGraph, check edge data
                # We need all edges between next_node and succ
                for key in G[next_node][succ]:
                     if G[next_node][succ][key].get('type') == 'interaction':
                         nodes_to_add.add(succ)
                         
            # Check outgoing interaction edges TO next_node (incoming)
            for pred in G.predecessors(next_node):
                for key in G[pred][next_node]:
                     if G[pred][next_node][key].get('type') == 'interaction':
                         nodes_to_add.add(pred)

            curr_nodes.update(nodes_to_add)
            
            sub = G.subgraph(curr_nodes)
            curr_k = count_interaction_edges(sub)
            
            if curr_k == k:
                valid_sample = True
                break
            elif curr_k > k:
                # Overshot
                break
        
        if valid_sample:
            samples.append(frozenset(curr_nodes))
            
    return samples

def mine_graph_k(args):
    """
    Worker function to mine patterns of size k from a single graph G.
    args: (G, k, g_idx, num_samples, use_sampling, mode)
    Returns: (g_idx, hash_counts, total_units, dict_of_examples)
    """
    G, k, g_idx, num_samples, use_sampling, mode = args
    if G is None:
        return (g_idx, collections.Counter(), 0, {})
    
    if G.number_of_nodes() < k:
         return (g_idx, collections.Counter(), 0, {})

    if use_sampling:
        if mode == 'comm':
             subgraphs = sample_subgraphs_by_interaction_k(G, k, num_samples)
        else:
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
        # Compute hash using mode-specific strategy
        h = get_canon_label(sub_G, mode=mode)
        
        hash_counts[h] += 1
        
        if h not in examples:
            examples[h] = sub_G
            
    return (g_idx, hash_counts, total_units, examples)

def collect_files(inputs):
    qasm_files = []
    for inp in inputs:
        if os.path.isfile(inp) and inp.endswith(".qasm"):
             qasm_files.append(inp)
        elif os.path.isdir(inp):
            for root, dirs, files in os.walk(inp):
                for file in files:
                    if file.endswith(".qasm"):
                        qasm_files.append(os.path.join(root, file))
    return qasm_files

def mine_patterns(inputs, min_support=0.5, k_min=2, k_max=3, num_samples=2000, use_sampling=True, mode='dataflow', output_dir='results'):
    files = collect_files(inputs)
    print(f"Found {len(files)} QASM files.")
    
    if not files:
        print("No QASM files found. Exiting.")
        return

    # Determine benchmark name for output directory
    if len(inputs) == 1 and os.path.isdir(inputs[0]):
        # Original behavior: directory name
        benchmark_name = os.path.basename(os.path.normpath(inputs[0]))
    elif len(files) == 1:
        # Single file: use parent dir name or file basename
        benchmark_name = os.path.splitext(os.path.basename(files[0]))[0] 
    else:
        # Multiple files/dirs: try to find common directory or use "custom"
        # Simple heuristic: "custom_selection"
        benchmark_name = "custom_selection"

    # Create base output directory
    base_out_path = os.path.join(output_dir, benchmark_name, mode)
    os.makedirs(base_out_path, exist_ok=True)
    print(f"Output directory: {base_out_path}")
    
    graphs = []
    
    print(f"Building graphs in parallel (Mode: {mode})...")
    # Pack args for build_graph_safe
    build_args = [(f, mode) for f in files]
    
    with concurrent.futures.ProcessPoolExecutor() as executor:
        results = executor.map(build_graph_safe, build_args)
        
        for file_path, G in results:
            if G is not None:
                graphs.append(G)
                
    print(f"Successfully built {len(graphs)} graphs.")
    
    mode_str = f"Sampling {num_samples} per graph" if use_sampling else "Exhaustive Search"
    
    for k in range(k_min, k_max + 1):
        print(f"Mining size {k} patterns ({mode_str})...")
        
        # Create k-specific folder
        k_out_path = os.path.join(base_out_path, f"k{k}")
        os.makedirs(k_out_path, exist_ok=True)
        
        global_pattern_counts = collections.Counter()
        global_total_units = 0
        pattern_examples = {} 
        
        # Add mode to worker args
        worker_args = []
        chunk_size = 500
        
        for i, G in enumerate(graphs):
            if use_sampling:
                # Split num_samples into chunks for better parallelization
                remaining = num_samples
                while remaining > 0:
                     curr = min(remaining, chunk_size)
                     worker_args.append((G, k, i, curr, use_sampling, mode))
                     remaining -= curr
            else:
                # Exhaustive search, one task per graph
                worker_args.append((G, k, i, num_samples, use_sampling, mode))
        
        with concurrent.futures.ProcessPoolExecutor() as executor:
            # Increase chunksize for executor map since we have more tasks now
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
             names = [example.nodes[n].get('op_name' if mode=='comm' else 'name', '') for n in example.nodes]
             print(f"    Nodes: {names}")
             print(f"    Edges: {len(example.edges())}")
             
             # Visualize top 3 patterns
             if i < 3:
                 filename = f"rank{i+1}_freq{int(frequency*100)}pct.png"
                 output_filename = os.path.join(k_out_path, filename)
                 title = f"Pattern k={k} Rank {i+1} | Freq: {frequency:.1%} ({count}/{global_total_units})"
                 try:
                     if mode == 'comm':
                         visualize_interaction_graph(example, output_filename, title=title)
                     else:
                         visualize_graph(example, output_filename, title=title)
                     print(f"    Saved visualization to {output_filename}")
                 except Exception as e:
                     print(f"    Failed to visualize: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Mine frequent communication patterns in QASM circuits.")
    parser.add_argument("inputs", type=str, nargs='+', help="Input QASM files or directories")
    parser.add_argument("k_max", type=int, nargs="?", default=3, help="Maximum subgraph size (k)")
    parser.add_argument("--k-min", type=int, default=2, help="Minimum subgraph size (k)")
    parser.add_argument("--samples", type=int, default=2000, help="Number of samples per graph (if sampling)")
    parser.add_argument("--exact", action="store_true", help="Use exhaustive search instead of sampling")
    parser.add_argument("--mode", choices=['dataflow', 'comm'], default='dataflow', help="Mining mode: 'dataflow' or 'comm' (interaction flow)")
    parser.add_argument("--output-dir", type=str, default='results', help="Directory to save results")
    
    args = parser.parse_args()
    
    use_sampling = not args.exact
    
    mine_patterns(args.inputs, min_support=0.5, k_min=args.k_min, k_max=args.k_max, num_samples=args.samples, use_sampling=use_sampling, mode=args.mode, output_dir=args.output_dir)
