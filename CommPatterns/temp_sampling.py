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
        
        if curr_k > k:
            continue # Started with too many (e.g. parallel edges), discard
        
        if curr_k == k:
            samples.append(frozenset(curr_nodes))
            continue
            
        # Expand
        valid_sample = False
        # Limit expansion attempts to avoid infinite loops
        max_attempts = k * 5 
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
            # Optimization: Prioritize neighbors that add interactions?
            # For now, uniform random walk.
            next_node = random.choice(list(neighbors))
            curr_nodes.add(next_node)
            
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
