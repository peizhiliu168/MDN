from qiskit import QuantumCircuit
import networkx as nx
from graph_builder import build_graph_from_circuit

qc = QuantumCircuit(2)
qc.x(0)
qc.x(1)
qc.cx(0, 1) # Should come from x(0) and x(1) -> 2 incoming edges
qc.cx(0, 1) # Should come from previous cx(0,1) -> 2 incoming edges (both from node 2)

G = build_graph_from_circuit(qc)

print("Nodes:", G.nodes(data=True))
print("Edges:", G.edges(data=True))

for n in G.nodes:
    in_degree = G.in_degree(n)
    op_name = G.nodes[n]['name']
    print(f"Node {n} ({op_name}): in_degree={in_degree}")
