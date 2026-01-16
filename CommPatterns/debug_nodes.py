from qiskit import QuantumCircuit
from graph_builder import build_interaction_graph, flatten_circuit

file_path = '../FTCircuitBench/qasm/adder/adder_10q.qasm'
print(f"Loading {file_path}")
qc = QuantumCircuit.from_qasm_file(file_path)
print(f"Original Qubits: {len(qc.qubits)}")

print("Flattening...")
flat_qc = flatten_circuit(qc)
print(f"Flattened Qubits: {len(flat_qc.qubits)}")

print("Building Graph...")
G = build_interaction_graph(qc)
print(f"Graph Nodes: {len(G.nodes())}")
print(f"Graph Node List: {list(G.nodes())}")
