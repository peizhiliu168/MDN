import networkx as nx
import matplotlib.pyplot as plt

def visualize_graph(G: nx.MultiDiGraph, output_file: str = None, title: str = None):
    """
    Visualizes the QASM dataflow graph using Matplotlib.
    
    Nodes are positioned based on:
    - X-axis: 'layer' attribute (topological depth/time)
    - Y-axis: 'avg_qubit' attribute (logical qubit index)
    """
    plt.figure(figsize=(12, 8))
    
    pos = {}
    for node, data in G.nodes(data=True):
        # Invert Y axis so qubit 0 is at the top
        pos[node] = (data.get('layer', 0), -data.get('avg_qubit', 0))
        
    # Draw edges
    # User requested straight edges. Parallel edges will overlap visually.
    nx.draw_networkx_edges(G, pos, edge_color='gray', arrows=True, alpha=0.5)
    
    # Draw nodes
    # Color nodes by type/name if desired, for now uniform
    nx.draw_networkx_nodes(G, pos, node_size=500, node_color='lightblue', alpha=0.9)
    
    # Labels
    labels = {n: G.nodes[n].get('name', '') for n in G.nodes}
    nx.draw_networkx_labels(G, pos, labels=labels, font_size=8)
    
    if title:
        plt.title(title)
    else:
        plt.title("Qubit Dataflow Graph")
    plt.xlabel("Layer (Time)")
    plt.ylabel("Qubit Index (inverted)")
    
    # Remove ticks/spines for cleaner look
    plt.axis('off')
    
    if output_file:
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"Graph visualization saved to {output_file}")
    else:
        plt.show()
    plt.close()

def visualize_interaction_graph(G: nx.MultiDiGraph, output_file: str = None, title: str = None):
    """
    Visualizes the Interaction Flow Graph.
    Layout:
    - X axis: Layer (Time)
    - Y axis: Qubit Index
    """
    plt.figure(figsize=(12, 8))
    
    # Custom Layout based on layer and qubit_index
    pos = {}
    for n, data in G.nodes(data=True):
        # Scale x by layer, y by -qubit_index (so Q0 is at top)
        # Add some jitter or scaling if needed.
        pos[n] = (data.get('layer', 0), -data.get('qubit_index', 0))
        
    # Draw Nodes
    # Color mapping? Maybe by Op Name?
    nx.draw_networkx_nodes(G, pos, node_size=300, node_color='lightblue', alpha=0.9)
    
    # Labels (Q0, Q1...)
    labels = nx.get_node_attributes(G, 'label')
    nx.draw_networkx_labels(G, pos, labels=labels, font_size=8)
    
    # Draw Edges types separately
    flow_edges = []
    interaction_edges = []
    
    for u, v, data in G.edges(data=True):
        edge_type = data.get('type', 'unknown')
        if edge_type == 'flow':
            flow_edges.append((u, v))
        else:
            interaction_edges.append((u, v))
            
    # Draw Flow Edges (Horizontal, lighter)
    nx.draw_networkx_edges(G, pos, edgelist=flow_edges, 
                           edge_color='gray', arrows=True, arrowstyle='->', alpha=0.5)
                           
    # Draw Interaction Edges (Vertical/Diagonal, distinct)
    # Use curvature for these if they are long range?
    # For now, straight or slightly curved.
    nx.draw_networkx_edges(G, pos, edgelist=interaction_edges, 
                           edge_color='red', arrows=True, width=1.5, alpha=0.8)
                           
    # Draw Interaction Edge Labels
    interaction_labels = {}
    for u, v, data in G.edges(data=True):
        if data.get('type') == 'interaction':
            lbl = data.get('label', '')
            if lbl:
                interaction_labels[(u,v)] = lbl
                
    nx.draw_networkx_edge_labels(G, pos, edge_labels=interaction_labels, font_size=8, font_color='darkred',
                                 bbox=dict(facecolor='white', alpha=0.7, edgecolor='none', pad=1))
                                   
    if title:
        plt.title(title)
    else:
        plt.title("Qubit Interaction Flow Graph")
        
    plt.axis('off')
    
    if output_file:
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"Interaction graph saved to {output_file}")
    else:
        plt.show()
    plt.close()
