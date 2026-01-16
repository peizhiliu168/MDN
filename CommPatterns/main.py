import argparse
import sys
import networkx as nx
from qiskit import QuantumCircuit
from graph_builder import build_graph_from_circuit

def main():
    parser = argparse.ArgumentParser(description="Analyze communication patterns in QASM files using a qubit dataflow graph.")
    parser.add_argument("qasm_file", help="Path to the QASM file to analyze")
    parser.add_argument("--output", help="Optional path to save the graph (e.g. .graphml or .gexf)", default=None)
    parser.add_argument("--visualize", action="store_true", help="Visualize the graph")
    parser.add_argument("--vis-output", help="Path to save the visualization image (e.g. .png)", default=None)
    parser.add_argument("--mode", choices=['dataflow', 'comm'], default='dataflow', help="Analysis mode: 'dataflow' (operation dependency) or 'comm' (qubit interaction)")
    
    args = parser.parse_args()
    
    try:
        print(f"Reading QASM file: {args.qasm_file}")
        params = {}
        # Basic qiskit QASM parser
        circuit = QuantumCircuit.from_qasm_file(args.qasm_file)
        
        print(f"Circuit loaded. Qubits: {circuit.num_qubits}, Operations: {len(circuit.data)}")
        
        if args.mode == 'dataflow':
            G = build_graph_from_circuit(circuit)
            print(f"Dataflow Graph constructed.")
        else:
            from graph_builder import build_interaction_graph
            G = build_interaction_graph(circuit)
            print(f"Interaction Graph constructed.")

        print(f"Nodes: {G.number_of_nodes()}")
        print(f"Edges: {G.number_of_edges()}")
        
        if args.output:
            print(f"Saving graph to {args.output}")
            nx.write_graphml(G, args.output)
            
        if args.visualize:
            print("Visualizing graph...")
            if args.mode == 'dataflow':
                from visualizer import visualize_graph
                visualize_graph(G, args.vis_output)
            else:
                from visualizer import visualize_interaction_graph
                visualize_interaction_graph(G, args.vis_output)
            
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
