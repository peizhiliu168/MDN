from qiskit import QuantumCircuit
from graph_builder import build_interaction_graph
import networkx as nx

file_path = '../FTCircuitBench/qasm/adder/adder_10q.qasm'
qc = QuantumCircuit.from_qasm_file(file_path)
G = build_interaction_graph(qc)

print(f"Nodes: {G.number_of_nodes()}")
print(f"Edges: {G.number_of_edges()}")

self_loops = list(nx.selfloop_edges(G))
if self_loops:
    print(f"Found {len(self_loops)} self-loops:")
    for u, v in self_loops:
        print(f"  Node {u}: {G.nodes[u]}")
else:
    print("No self-loops found.")
