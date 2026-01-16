import networkx as nx
from qiskit import QuantumCircuit
from qiskit.dagcircuit import DAGCircuit
from qiskit.converters import circuit_to_dag

def flatten_circuit(circuit: QuantumCircuit) -> QuantumCircuit:
    """
    Flattens the circuit by repeatedly decomposing custom gates and functions.
    Ensures that only standard basis gates remain.
    SWAP and CSWAP are excluded from standard gates to force decomposition into CX/CCX.
    """
    # Standard gates we want to keep. 
    # Note: SWAP and CSWAP are REMOVED to force decomposition into CXs.
    standard_gates = {'u1', 'u2', 'u3', 'u', 'p', 'i', 'id', 'x', 'y', 'z', 'h', 's', 'sdg', 't', 'tdg', 
                      'rx', 'ry', 'rz', 'cx', 'cy', 'cz', 'ch', 'ccx', 
                      'measure', 'barrier', 'reset', 'snapshot', 'delay'}
    
    max_passes = 10
    current_circuit = circuit
    
    for _ in range(max_passes):
        has_custom = False
        for inst in current_circuit.data:
            if inst.operation.name not in standard_gates:
                has_custom = True
                break
        
        if has_custom:
            try:
                current_circuit = current_circuit.decompose()
            except Exception:
                break
        else:
            break
            
    return current_circuit

def build_graph_from_circuit(circuit: QuantumCircuit) -> nx.MultiDiGraph:
    """
    Constructs a NetworkX MultiDiGraph from a Qiskit QuantumCircuit.
    Nodes are operations. Edges represent qubit dependencies (dataflow).
    """
    circuit = flatten_circuit(circuit)
    dag = circuit_to_dag(circuit)
    G = nx.MultiDiGraph()
    
    last_node_on_qubit = {q: -1 for q in circuit.qubits} 
    current_id = 0
    qubit_depths = {q: 0 for q in circuit.qubits}

    for node in dag.topological_op_nodes():
        # Determine layer
        current_layer = 1
        if node.qargs:
            current_layer = max(qubit_depths[q] for q in node.qargs) + 1
        
        # Determine average qubit index
        if node.qargs:
            avg_qubit = sum(q._index for q in node.qargs) / len(node.qargs)
        else:
            avg_qubit = 0 

        # Add node
        G.add_node(current_id, 
                   name=node.op.name, 
                   qubits=[q._index for q in node.qargs],
                   layer=current_layer,
                   avg_qubit=avg_qubit)
        
        # Add edges
        for q in node.qargs:
            prev_id = last_node_on_qubit[q]
            if prev_id != -1:
                G.add_edge(prev_id, current_id, qubit=q._index)
            
            last_node_on_qubit[q] = current_id
            qubit_depths[q] = current_layer
        
        current_id += 1
        
    return G

def build_interaction_graph(circuit: QuantumCircuit) -> nx.MultiDiGraph:
    """
    Constructs an "Interaction Flow Graph".
    - Nodes: Represent a qubit at a specific interaction point.
             Label: "Q{index}"
             Attributes: qubit_index, op_name, layer
    - Edges:
        1. Interaction Edges: Control -> Target (within the same gate).
        2. Flow Edges: PrevInstance -> CurrInstance (temporal flow along wire).
    """
    circuit = flatten_circuit(circuit)
    dag = circuit_to_dag(circuit)
    
    G = nx.MultiDiGraph()
    
    # Map each qubit object to a unique global integer index
    # Note: q._index is relative to the register, so it collides across registers (e.g. a[0] and b[0] both have _index=0)
    # circuit.qubits list defines the global order.
    q_map = {q: i for i, q in enumerate(circuit.qubits)}
    
    # Track the last node ID for each qubit to add Flow Edges
    last_node_on_qubit = {q_map[q]: -1 for q in circuit.qubits}
    
    # Track depth for layout
    qubit_depths = {q_map[q]: 0 for q in circuit.qubits}
    
    current_node_id = 0
    
    for node in dag.topological_op_nodes():
        qargs = node.qargs
        # Skip single qubit gates (no interaction)
        if len(qargs) <= 1:
            continue
            
        op_name = node.op.name
        if op_name in ['barrier', 'snapshot', 'delay']:
            continue
            
        # Global indices for current operation qubits
        current_qubit_indices = [q_map[q] for q in qargs]
            
        # Determine layer for this interaction
        # It must be after the max layer of input qubits
        input_layer = max(qubit_depths[q_idx] for q_idx in current_qubit_indices)
        current_layer = input_layer + 1
        
        # Create a node for EACH qubit in this interaction
        current_interaction_nodes = {} # qubit_global_idx -> node_id
        
        for q in qargs:
            q_idx = q_map[q]
            G.add_node(current_node_id, 
                       label=f"Q{q_idx}", 
                       qubit_index=q_idx,
                       op_name=op_name,
                       layer=current_layer,
                       type='qubit_instance')
            
            current_interaction_nodes[q_idx] = current_node_id
            
            # Add Flow Edge (Time)
            prev_id = last_node_on_qubit[q_idx]
            if prev_id != -1:
                G.add_edge(prev_id, current_node_id, type='flow', weight=1)
            
            # Update trackers
            last_node_on_qubit[q_idx] = current_node_id
            qubit_depths[q_idx] = current_layer
            
            current_node_id += 1
            
        # Add Interaction Edges (Control -> Target)
        # Assumption: Last qubit is target, others are controls.
        target_q = qargs[-1]
        target_idx = q_map[target_q]
        
        control_qs = qargs[:-1]
        control_indices = [q_map[q] for q in control_qs]
        
        target_node_id = current_interaction_nodes[target_idx]
        
        for c_idx in control_indices:
            control_node_id = current_interaction_nodes[c_idx]
            G.add_edge(control_node_id, target_node_id, type='interaction', weight=2, label=op_name)

    return G
