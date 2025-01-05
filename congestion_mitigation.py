import json
from pyomo.environ import *
from cmath import exp, pi


class CongestionMitigation:
    def __init__(self, data_file):
        self.data_file = data_file
        self.data = None
        self.model = None
        self.results = None

    def check_data_sanity(self):
        """Check if the input data file has the required fields and structure."""
        with open(self.data_file, "r") as file:
            self.data = json.load(file)

        required_fields = ["network"]
        if not all(field in self.data for field in required_fields):
            raise ValueError("Input data is missing required fields.")

        network = self.data["network"]
        if (
            "nodes" not in network
            or "branches" not in network
            or "parameters" not in network
        ):
            raise ValueError("Network data is incomplete.")

        # Check guaranteed power vs forecasted power
        for node in network["nodes"]:
            if "load" in node:
                load = node["load"]
                for phase in ["a", "b", "c"]:
                    if load["P_guaranteed"] >= load["P_forecasted"][phase]:
                        raise ValueError(
                            f"Node {node['id']}: P_guaranteed must be smaller than P_forecasted for phase {phase}."
                        )
                    if load["Q_guaranteed"] >= load["Q_forecasted"][phase]:
                        raise ValueError(
                            f"Node {node['id']}: Q_guaranteed must be smaller than Q_forecasted for phase {phase}."
                        )

        # Check impedance values
        for branch in network["branches"]:
            impedance = branch.get("impedance")
            if not impedance:
                raise ValueError(f"Branch {branch['id']} is missing impedance data.")
            for matrix_name in ["R", "X"]:
                matrix = impedance.get(matrix_name)
                if not matrix:
                    raise ValueError(
                        f"Branch {branch['id']} is missing {matrix_name} matrix."
                    )
                for row in matrix:
                    if not all(value >= 0 for value in row):
                        raise ValueError(
                            f"Branch {branch['id']} has non-positive values in {matrix_name} matrix."
                        )

        # Check branches have valid from and to buses
        for branch in network["branches"]:
            if "from" not in branch or "to" not in branch:
                raise ValueError(
                    f"Branch {branch['id']} must have 'from' and 'to' fields defined."
                )

        print("Data sanity check passed.")

    def create_problem(self):
        """Create the optimization problem."""
        data = self.data
        nodes = data["network"]["nodes"]
        branches = data["network"]["branches"]
        parameters = data["network"]["parameters"]
        time_steps = parameters["time_steps"]

        model = ConcreteModel()

        # Sets
        model.T = RangeSet(1, time_steps)
        model.Nodes = Set(initialize=[node["id"] for node in nodes])
        model.Branches = Set(initialize=[branch["id"] for branch in branches])
        model.Phases = RangeSet(1, 3)
        phase_map = {1: "a", 2: "b", 3: "c"}

        # Rotation matrix gamma
        alpha = exp(-1j * 2 * pi / 3)
        gamma = [[1, alpha**2, alpha], [alpha, 1, alpha**2], [alpha**2, alpha, 1]]

        # Parameters
        voltage_min = parameters["voltage_limits"]["min"] ** 2
        voltage_max = parameters["voltage_limits"]["max"] ** 2

        # Decision Variables
        model.s = Var(model.Nodes, model.T, domain=Binary, initialize=0)
        model.P = Var(model.Nodes, model.Phases, model.Phases, model.T, initialize=0)
        model.Q = Var(model.Nodes, model.Phases, model.Phases, model.T, initialize=0)
        model.P_flow = Var(
            model.Branches, model.Phases, model.Phases, model.T, initialize=0
        )
        model.Q_flow = Var(
            model.Branches, model.Phases, model.Phases, model.T, initialize=0
        )
        model.u = Var(
            model.Nodes,
            model.Phases,
            model.Phases,
            model.T,
            domain=NonNegativeReals,
            initialize=0,
        )

        # Objective Function
        def objective_rule(model):
            return sum(model.s[n, t] for n in model.Nodes for t in model.T)

        model.Objective = Objective(rule=objective_rule, sense=minimize)

        # Constraints

        # Constraints
        model.constraints = ConstraintList()

        # 3. Ohm's Law for voltage: u = u[from] - Z * Lambda
        for branch in branches:
            from_node = branch["from"]
            to_node = branch["to"]
            impedance = branch["impedance"]
            for t in model.T:
                for p1 in model.Phases:
                    for p2 in model.Phases:
                        R = impedance["R"][p1 - 1][p2 - 1]
                        X = impedance["X"][p1 - 1][p2 - 1]
                        model.constraints.add(
                            model.u[to_node, p1, p2, t]
                            == model.u[from_node, p1, p2, t]
                            - 2
                            * (
                                R * model.P_flow[branch["id"], p1, p2, t]
                                + X * model.Q_flow[branch["id"], p1, p2, t]
                            )
                        )

        # 4. Voltage Limits (Diagonal of u)
        for node in nodes:
            n = node["id"]
            for t in model.T:
                for p in model.Phases:
                    model.constraints.add(voltage_min <= model.u[n, p, p, t])
                    model.constraints.add(model.u[n, p, p, t] <= voltage_max)

        # 5. Power Flow Balance Constraint
        for node in nodes:
            n = node["id"]
            for t in model.T:
                for p1 in model.Phases:
                    for p2 in model.Phases:
                        if p1 == p2:
                            # Active power balance
                            incoming_active = sum(
                                model.P_flow[branch["id"], p1, p2, t]
                                for branch in branches
                                if branch["to"] == n
                            )
                            outgoing_active = sum(
                                model.P_flow[branch["id"], p1, p2, t]
                                for branch in branches
                                if branch["from"] == n
                            )
                            model.constraints.add(
                                incoming_active + model.P[n, p1, p2, t]
                                == outgoing_active
                            )

                            # Reactive power balance
                            incoming_reactive = sum(
                                model.Q_flow[branch["id"], p1, p2, t]
                                for branch in branches
                                if branch["to"] == n
                            )
                            outgoing_reactive = sum(
                                model.Q_flow[branch["id"], p1, p2, t]
                                for branch in branches
                                if branch["from"] == n
                            )
                            model.constraints.add(
                                incoming_reactive + model.Q[n, p1, p2, t]
                                == outgoing_reactive
                            )
        # Constraint: P + iQ = gamma * diag(P + iQ)
        for branch in branches:
            branch_id = branch["id"]
            for t in model.T:
                for p1 in model.Phases:
                    for p2 in model.Phases:
                        # Extract the gamma values (real and imaginary parts)
                        gamma_real = gamma[p1 - 1][p2 - 1].real
                        gamma_imag = gamma[p1 - 1][p2 - 1].imag

                        # Real part (active power)
                        model.constraints.add(
                            model.P_flow[branch_id, p1, p2, t]
                            == gamma_real * model.P_flow[branch_id, p1, p1, t]
                            - gamma_imag * model.Q_flow[branch_id, p1, p1, t]
                        )

                        # Imaginary part (reactive power)
                        model.constraints.add(
                            model.Q_flow[branch_id, p1, p2, t]
                            == gamma_real * model.Q_flow[branch_id, p1, p1, t]
                            + gamma_imag * model.P_flow[branch_id, p1, p1, t]
                        )

        # 6. User Demand Constraints
        for node in nodes:
            if "load" in node:
                n = node["id"]
                load = node["load"]
                for t in model.T:
                    for phase in model.Phases:
                        phase_key = phase_map[
                            phase
                        ]  # Map integer phase index to JSON key
                        # Active power constraint
                        model.constraints.add(
                            -model.P[n, phase, phase, t]
                            == model.s[n, t] * load["P_guaranteed"]
                            + (1 - model.s[n, t]) * load["P_forecasted"][phase_key]
                        )
                        # Reactive power constraint
                        model.constraints.add(
                            -model.Q[n, phase, phase, t]
                            == model.s[n, t] * load["Q_guaranteed"]
                            + (1 - model.s[n, t]) * load["Q_forecasted"][phase_key]
                        )

        self.model = model
        print("Problem created successfully.")

    def solve_problem(self):
        """Solve the optimization problem."""
        if not self.model:
            raise ValueError("Model not created. Run create_problem() first.")

        solver = SolverFactory("glpk")
        self.results = solver.solve(self.model, tee=True)
        print("Problem solved successfully.")

    def show_result(self):
        """Display the results."""
        model = self.model
        nodes = self.data["network"]["nodes"]
        branches = self.data["network"]["branches"]

        def print_matrix(title, matrix):
            print(f"\n{title}:")
            for row in matrix:
                print(
                    "  "
                    + "  ".join(
                        f"{value:.4f}" if value is not None else "None" for value in row
                    )
                )

        print("Optimization Results:")
        for t in model.T:
            print(f"\nTime Step: {t}")
            for node in nodes:
                n = node["id"]
                s_value = value(model.s[n, t])
                print(f"\nNode: {n}")
                print(f"  Power Reduction Status (s): {s_value}")
                u_matrix = [[None] * 3 for _ in range(3)]
                P_matrix = [[None] * 3 for _ in range(3)]
                Q_matrix = [[None] * 3 for _ in range(3)]

                for p1 in model.Phases:
                    for p2 in model.Phases:
                        u_matrix[p1 - 1][p2 - 1] = value(model.u[n, p1, p2, t])
                        P_matrix[p1 - 1][p2 - 1] = value(model.P[n, p1, p2, t])
                        Q_matrix[p1 - 1][p2 - 1] = value(model.Q[n, p1, p2, t])

                print_matrix("Voltage Squared (u)", u_matrix)
                print_matrix("Active Power (P)", P_matrix)
                print_matrix("Reactive Power (Q)", Q_matrix)

            for branch in branches:
                branch_id = branch["id"]
                from_node = branch["from"]
                to_node = branch["to"]
                print(f"\nBranch: {branch_id} (From: {from_node} -> To: {to_node})")
                P_flow_matrix = [[None] * 3 for _ in range(3)]
                Q_flow_matrix = [[None] * 3 for _ in range(3)]

                for p1 in model.Phases:
                    for p2 in model.Phases:
                        P_flow_matrix[p1 - 1][p2 - 1] = value(
                            model.P_flow[branch_id, p1, p2, t]
                        )
                        Q_flow_matrix[p1 - 1][p2 - 1] = value(
                            model.Q_flow[branch_id, p1, p2, t]
                        )

                print_matrix("Active Power Flow (P_flow)", P_flow_matrix)
                print_matrix("Reactive Power Flow (Q_flow)", Q_flow_matrix)


simple_example = CongestionMitigation("newnetwork.json")
simple_example.check_data_sanity()
simple_example.create_problem()
simple_example.solve_problem()
simple_example.show_result()
