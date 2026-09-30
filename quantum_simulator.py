from collections import deque

import numpy as np


class QuantumHardware:

    # Create a hardware model using the physical qubit connections.
    def __init__(self, connections):
        # Store the qubit connectivity graph for later validation.
        self.connections = connections

    # Check whether two physical qubits can directly interact.
    def is_connected(self, q1, q2):
        # Return True if the qubits are connected, otherwise return False.
        return (q1, q2) in self.connections or (q2, q1) in self.connections 

    def shortest_path(self, start, target):
        # Create a queue for BFS and enqueue the starting qubit with an empty path.
        queue = deque([[start]])

        # Keep track of visited qubits to avoid cycles.
        visited = {start}

        while queue:
            # Dequeue the next qubit and the path taken to reach it.
            path = queue.popleft()

            # The fiaml qubit in the path is the current qubit we are exploring.
            current = path[-1]

            # If we reached the target, return the path including the target.
            if current == target:
                return path 

            # Mark the current qubit as visited.
            visited.add(current)

            # Explore all connected neighbors of the current qubit.
            for q1, q2 in self.connections:
                # Determine whcih qubit is the neighbor of the current qubit.
                if q1 == current:
                    neighbor = q2
                elif q2 == current:
                    neighbor = q1
                else:
                    # Ignore connections that do not involve the current qubit.
                    continue

                # Only explore this neighbor if we have not visited it before.
                if neighbor not in visited:
                    # Mark the neighbor as visited.
                    visited.add(neighbor)

                    # Create a new path by adding the neighbor
                    new_path = path + [neighbor]

                    # Add the new path to the BFS queue
                    queue.append(new_path)

        # Return None if no path is found.
        return None
    
    def physical_distance(self, q1, q2):
        # On a Linear device, the distance is simply the differnce
        # between the two physical qubit positions
        return abs(q1 - q2)

    def interaction_cost(self, gates, mapping):
        #Start with zero because we have not evaluated any interactions yet.
        total_cost = 0

        # Examine every two-qubit gate in the Look-ahead window.
        for control, target in gates:
            # Convert the Logical controal qubit to its physical location.
            physical_control = mapping[control]

            # Convert the logical target qubit to its physical location.
            physical_target = mapping[target]

            # Add the physical distance to the total cost.
            total_cost += self.physical_distance(
                physical_control,
                physical_target
            )

        # Return the total interaction cost.
        return total_cost
    

class QuantumCompiler:

    # Define the gates supported directly by the hypothetical hardware.
    def __init__(self, hardware, num_qubits):
        # Store the native gate set for later hardware validation.
        self.native_gates = {"Rx", "Rz", "CNOT"}
        
        # Store the hardware model for later use in compilation.
        self.hardware = hardware

        # initially place logical qubits on physical qubits in order
        self.mapping = {
            logical: logical
            for logical in range(num_qubits)
        }

    def physical_location(self, logical_qubit):
        """Return the physical qubit currently assigned to a logical qubit."""
        return self.mapping[logical_qubit]

    def get_qubits(self, gate):
        # A single-qubit gate stores its qubit at position 1.
        if gate[0] in ["H", "X", "Y", "Z"]:
            return {gate[1]}
        
        # A two-qubit gate uses both the control and forget qubits.
        elif gate[0] == "CNOT":
            return {gate[1],gate[2]}

        # Return on empty set for gate types we have not implemented yet.
        return set()

    def schedule_gates(self, gates):
        # Store the circuit's layers.
        # Each Layer will contain gates that can execute simultaneously.
        layers = []

        # Process the gates in their original circuit order.
        for gate in gates:
            # find which qubits this gate uses.
            gate_qubits = QuantumCompiler.get_qubits(gate)

            # Try to place the gate into an existing Layer.
            placed = False

            # Check each existing layer from earliest to latest.
            for layer in layers:
                # Collect all qubits already being used by this layer.
                used_qubits = set()

                # Examine every gate already inside the layer.
                for existing_gate in layer:
                    # Add that gate's quvits to the used-qubit set.
                     used_qubits.update(self.get_qubits(existing_gate))

                # If this gate uses no qubit already used by the layer.
                # it can execute in parallel with the layer's gates.
                if gate_qubits.isdisjoint(used_qubits):
                    # Add the gate to this layer.
                    layer.append(gate)

                    # Mark the gate as successfully placed.
                    placed = True

                    # Stop searching because we found a valid layer.
                    break


            # If the gate could not fit into any existing layer,
            # create a new layer for it.
            if not placed:
                layer.append([gate])


        # Return the complete scheduled circuit.
        return layers

    def get_qubits(self, gate):
        # The first item tells us what type of gate this is.
        gate_name = gate[0]

        # H, X, and Z are single-qubit gates/
        # The second item tells us which qubit they use.
        if gate_name in {"H", "X", "Z"}:
            return {gate[1]}
        
        # CNOT uses two qubits:
        # Gate[1] is the control and gate[2] is the target.
        elif gate_name == "CNOT":
            return {gate[1], gate[2]}

        # Return on empty set if we don't know this gate yet.
        return set()

    def schedule_circuit(self,gates):
        # Store when each qubit becomes available.
        # We assume our circuit has three qubits numbered 0, 1, and 2.
        qubit_available = {
            0: 0,
            1: 0,
            2: 0
        }

        # Store the duration of each gate.
        # These are simplified hypothetical hardware timings.
        gate_duration = {
            "H": 1,
            "X": 1,
            "Z": 1,
            "CNOT": 3
        } 

        # Store the final Schedule.
        # Each item will contain the gate and its start/finish times.
        schedule = []

        # Process gates in their original circuit order.
        for gate in gates:
            #Find which qubits this gate needs.
            required_qubits = self.get_qubits(gate)

            # Find when each required qubit becomes available.
            required_times = {
                qubit_available[qubit]
                for qubit in required_qubits
            }

            # The gate must wait until all required qubits are availavle.
            # Therefore, we choose the latest availability time.
            start_time = max(required_times)

            # Look up how long this gate takes.
            duration = gate_duration[gate[0]]

            # Calculate when the gate finishes.
            finish_time = start_time + duration

            # Save the gate and its timing information
            schedule.append(
                (gate, start_time, finish_time)
            )

            # Every qubit used by this gate is now busy until finish_time.
            for qubit in required_qubits:
                qubit_available[qubit] = finish_time

        # Return the completed schedule.
        return schedule

    def update_mapping_after_swap(self, physical_a, physical_b):
        """Update the logical-to-physical mapping after swapping two qubits."""
        inverse_mapping = {
            physical: logical
            for logical, physical in self.mapping.items()
        }
        
        try:
            logical_a = inverse_mapping[physical_a]
            logical_b = inverse_mapping[physical_b]
        except KeyError as error:
            raise ValueError("Cannot swap an unassigned physical qubit.") from error

        self.mapping[logical_a] = physical_b
        self.mapping[logical_b] = physical_a

    def route_cnot(self, control, target):
        """Route a logical CNOT and return only native physical operations."""
        routed_operations = []
        control_physical = self.physical_location(control)
        target_physical = self.physical_location(target)

        while not self.hardware.is_connected(control_physical, target_physical):
            path = self.hardware.shortest_path(control_physical, target_physical)
            if path is None:
                raise ValueError("CNOT qubits are not connected by the hardware graph.")

            swap_with = path[1]

            # Decompose a physical SWAP into the native CNOT gate.
            routed_operations.extend([
                ("CNOT", control_physical, swap_with),
                ("CNOT", swap_with, control_physical),
                ("CNOT", control_physical, swap_with),
            ])
            self.update_mapping_after_swap(control_physical, swap_with)
            control_physical = self.physical_location(control)
            target_physical = self.physical_location(target)

        routed_operations.append(("CNOT", control_physical, target_physical))
        return routed_operations

    # Convert high-level gates into native gates.
    def decompose(self, operations):
        # Create the output list for decomposed operations.
        compiled = []

        def append_h(qubit):
            # H is equal to Rz(pi/2) Rx(pi/2) Rz(pi/2), up to global phase.
            compiled.extend([
                ("Rz", np.pi / 2, qubit),
                ("Rx", np.pi / 2, qubit),
                ("Rz", np.pi / 2, qubit),
            ])

        # Process every operation in the original circuit.
        for operation in operations:

            # Read the gate name.
            gate = operation[0]

            # Decompose H into native gates.
            if gate == "H":
                # Get the target qubit.
                qubit = operation[1]

                append_h(qubit)

            # X and Z are rotations, up to a global phase.
            elif gate == "X":
                compiled.append(("Rx", np.pi, operation[1]))
            elif gate == "Z":
                compiled.append(("Rz", np.pi, operation[1]))

            # Decompose a y-axis rotation into native x- and z-axis rotations.
            elif gate == "Ry":
                theta, qubit = operation[1:]
                compiled.extend([
                    ("Rz", -np.pi / 2, qubit),
                    ("Rx", theta, qubit),
                    ("Rz", np.pi / 2, qubit),
                ])

            # A controlled-Z is a CNOT conjugated by Hadamards on its target.
            elif gate == "CZ":
                control, target = operation[1:]
                append_h(target)
                compiled.append(("CNOT", control, target))
                append_h(target)

            # Keep native gates unchanged.
            elif gate in self.native_gates:
                # Copy the native operation to the output.
                compiled.append(operation)

            # Stop if the compiler encounters an unsupported gate.
            else:
                # Report which gate could not be compiled.
                raise ValueError(f"Cannot decompose gate: {gate}")

        # Return the decomposed circuit.
        return compiled

    # Optimize consecutive Rz rotations.
    def optimize(self, operations):
        # Create the optimized output list.
        optimized = []

        # Process each operation in order.
        for operation in operations:

            # Check whether the current operation is Rz.
            if operation[0] == "Rz" and optimized:

                # Look at the previous optimized operation.
                previous = optimized[-1]

                # Merge consecutive Rz gates on the same qubit.
                if previous[0] == "Rz" and previous[2] == operation[2]:

                    # Add the rotation angles together.
                    new_angle = previous[1] + operation[1]

                    # Replace the previous operation with the combined Rz.
                    optimized[-1] = ("Rz", new_angle, operation[2])

                    # Do not append the current operation again.
                    continue

            # Keep operations that cannot be merged.
            optimized.append(operation)

        # Return the optimized circuit.
        return optimized

    # Run the complete compilation pipeline.
    def compile(self, operations):
        # First convert high-level gates into native gates.
        decomposed = self.decompose(operations)

        # Then optimize the native circuit.
        optimized = self.optimize(decomposed)

        # Route CNOTs and translate all logical qubits to physical qubits.
        routed = []
        for operation in optimized:
            if operation[0] == "CNOT":
                routed.extend(self.route_cnot(operation[1], operation[2]))
            else:
                gate, angle, logical_qubit = operation
                routed.append((gate, angle, self.physical_location(logical_qubit)))

        # Return the final hardware-compatible circuit.
        return routed


class QuantumCircuit:

    def __init__(self, num_qubits):
        # Store how many qubits this circuit contains.
        self.num_qubits = num_qubits

        # Create a state vector with 2^n amplitudes because n qubits have 2^n basis states.
        self.state = np.zeros(2 ** num_qubits, dtype=complex)

        # Set the first amplitude to 1, which initializes the circuit to |000...0>.
        self.state[0] = 1

        # Store every gate applied to the circuit in chronological order.
        self.operations = []


    def apply_single_qubit_gate(self, gate, qubit):
        # Start with a 1x1 identity-like matrix so we can build the full operator using tensor products.
        full_gate = np.array([[1]], dtype=complex)

        # Go through every qubit and decide whether to place the requested gate or an identity matrix.
        for i in range(self.num_qubits):

            # Put the actual gate on the qubit we want to operate on.
            if i == qubit:
                full_gate = np.kron(full_gate, gate)

            # Put an identity on all the other qubits so they remain unchanged.
            else:
                full_gate = np.kron(full_gate, np.eye(2, dtype=complex))

        # Multiply the full operator by the current state to obtain the new quantum state.
        self.state = full_gate @ self.state
    
    def controlled_gate(self, control, target, gate):
        # Make sure the control and target are different qubits.
        if control == target:
            raise ValueError("Control and target must be different qubits.")

        # Make sure the supplied gate is a 2x2 matrix.
        if gate.shape != (2, 2):
            raise ValueError("Gate must be a 2x2 matrix.")

        # Find the binary bit position corresponding to the control qubit.
        control_bit_position = self.num_qubits - 1 - control

        # Find the binary bit position corresponding to the target qubit.
        target_bit_position = self.num_qubits - 1 - target

        # Create a bit mask for checking the control qubit.
        control_mask = 1 << control_bit_position

        # Create a bit mask for finding the target qubit.
        target_mask = 1 << target_bit_position

        # Create a new state vector to store the result.
        new_state = np.zeros_like(self.state)

        for index in range(len(self.state)):
            # Check whether the control qubit is 1.
            control_is_one = (index & control_mask) != 0

            # If the control qubit is 0, the gate does nothing.
            if not control_is_one:
                new_state[index] += self.state[index]

            # If the control qubit is 1, we need to apply the gate.
            else:
                # Check whether the target bit is 0.
                target_is_one = (index & target_mask) != 0

                # Only process each target pair once.
                if not target_is_one:
                    # Find the corresponding state where the target bit is 1.
                    partner_index = index ^ target_mask

                    # Get the two amplitudes associated with target |0> and |1>.
                    amplitude_0 = self.state[index]
                    amplitude_1 = self.state[partner_index]

                    # Apply the 2x2 gate to those two amplitudes.
                    new_state[index] = (
                        gate[0, 0] * amplitude_0 +
                        gate[0, 1] * amplitude_1
                    )

                    # Calculate the new amplitude of the target |1> state.
                    new_state[partner_index] = (
                        gate[1, 0] * amplitude_0 +
                        gate[1, 1] * amplitude_1
                    )
        # save the newly calculated state vector back to the circuit's state.
        self.state = new_state

    def Rx(self, theta, qubit):
        # Calculate cos(theta/2) because this is the diagonal part of the x-axis rotation.
        c = np.cos(theta / 2)

        # Calculate sin(theta/2) because this determines the off-diagonal rotation terms.
        s = np.sin(theta / 2)

        # Return the 2x2 matrix for rotation around the x-axis.
        Rx = np.array([
            [c, -1j * s],
            [-1j * s, c]
        ], dtype=complex)

        # Apply the Rx gate to the requested qubit while leaving all other qubits unchanged.
        self.apply_single_qubit_gate(Rx, qubit)

        # Record the operation so the circuit remembers what was done.
        self.operations.append(("Rx", theta, qubit))


    def Ry(self, theta, qubit):
        # Calculate cos(theta/2) for the diagonal elements.
        c = np.cos(theta / 2)

        # Calculate sin(theta/2) for the off-diagonal elements.
        s = np.sin(theta / 2)

        # Return the 2x2 matrix for rotation around the y-axis.
        Ry = np.array([
            [c, -s],
            [s, c]
        ], dtype=complex)

        # Apply the Ry gate to the requested qubit while leaving all other qubits unchanged.
        self.apply_single_qubit_gate(Ry, qubit)

        # Record the operation so the circuit remembers what was done.
        self.operations.append(("Ry", theta, qubit))


    def Rz(self, theta, qubit):
        # Calculate the phase factor for the |0> component.
        phase_0 = np.exp(-1j * theta / 2)

        # Calculate the phase factor for the |1> component.
        phase_1 = np.exp(1j * theta / 2)

        # Return the 2x2 matrix for rotation around the z-axis.
        Rz = np.array([
            [phase_0, 0],
            [0, phase_1]
        ], dtype=complex)

        # Apply the Rz gate to the requested qubit while leaving all other qubits unchanged.
        self.apply_single_qubit_gate(Rz, qubit)

        # Record the operation so the circuit remembers what was done.
        self.operations.append(("Rz", theta, qubit))

    def probabilities(self):
        # The probability of each basis state is the absolute value squared of its amplitude.
        return np.abs(self.state) ** 2
    
    def Z(self,qubit):
        # Define the Pauli-Z gate, which flips the phase of |1> but leaves |0> unchanged.
        Z = np.array([
            [1, 0],
            [0, -1]
        ], dtype=complex)

        # Apply Z to the requested qubit while leaving all other qubits unchanged.
        self.apply_single_qubit_gate(Z, qubit)

        # Record the operation so the compiler receives it.
        self.operations.append(("Z", qubit))


    def X(self, qubit):
        # Define the Pauli-X gate, which changes |0> to |1> and |1> to |0>.
        X = np.array([
            [0, 1],
            [1, 0]
        ], dtype=complex)

        # Apply X to the requested qubit while leaving all other qubits unchanged.
        self.apply_single_qubit_gate(X, qubit)

        # Record the operation so the compiler receives it.
        self.operations.append(("X", qubit))


    def H(self, qubit):
        # Define the Hadamard gate, which creates a superposition from |0> or |1>.
        H = np.array([
            [1, 1],
            [1, -1]
        ], dtype=complex) / np.sqrt(2)

        # Apply H to the requested qubit while leaving all other qubits unchanged.
        self.apply_single_qubit_gate(H, qubit)
        # Record the operation so the circuit remembers what was done.
        self.operations.append(("H", qubit))

    def CNOT(self, control, target):
        # CNOT is a controlled-X gate.
        X = np.array([
            [0, 1],
            [1, 0]
        ], dtype=complex)

        # Apply X to the target only when the control qubit is |1>.
        self.controlled_gate(control, target, X)
    
        # Record the CNOT operation and its control/target qubits.
        self.operations.append(("CNOT", control, target))
    
    def CZ(self, control, target):
        # CZ is a controlled-Z gate.
        Z = np.array([
            [1, 0],
            [0, -1]
        ], dtype=complex)

        self.controlled_gate(control, target, Z)

        # Record the CZ operation and its control/target qubits.
        self.operations.append(("CZ", control, target))

    def CH(self, control, target):
        # CH is a controlled-Hadamard gate.
        H = np.array([
            [1, 1],
            [1, -1]
        ], dtype=complex) / np.sqrt(2)
        
        self.controlled_gate(control, target, H)
        
        # Record the CH operation and its control/target qubits.
        self.operations.append(("CH", control, target))

    def show(self):
        # Print the circuit's current state vector so we can inspect its amplitudes.
        print(self.state)
        print(self.operations)

# Create a small example circuit.
# The tuples describe the gate name and the qubits it uses.
circuit = [
    ("H", 0),
    ("CNOT", 0, 1),
    ("X", 2),
    ("H", 1)
]

# Create a compiler for the three-qubit example circuit and send it to the
# scheduler.  ``schedule_circuit`` is an instance method, so it needs a
# compiler object rather than the ``QuantumCompiler`` class itself.
compiler = QuantumCompiler(QuantumHardware([]), num_qubits=3)
schedule = compiler.schedule_circuit(circuit)

# Print each gate's scheduled start and finish time.
for gate, start, finish in schedule:
    print(gate, start, finish)
