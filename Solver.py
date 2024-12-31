import casadi
import json


class Solver:
    def __init__(self):
        self._solution = None

    def solve(self, problem):
        """
        Solve the optimization problem using CasADi.

        Parameters:
            problem (dict): The problem formulated with CasADi MX variables.

        Returns:
            dict: Solution of the optimization problem.
        """
        # Create the solver instance
        nlp = {
            "x": problem["x"],
            "p": problem["p"],
            "f": problem["f"],
            "g": problem["g"],
        }

        solver = casadi.nlpsol("solver", "ipopt", nlp)

        # Define bounds and parameter values
        p_values = problem["p_values"]
        lbx = problem["lbx"]
        ubx = problem["ubx"]
        lbg = problem["lbg"]
        ubg = problem["ubg"]

        # Solve the problem
        self._solution = solver(x0=0, p=p_values, lbx=lbx, ubx=ubx, lbg=lbg, ubg=ubg)
        return {
            "x": self._solution["x"].full(),
            "f": self._solution["f"].full(),
        }

    def create_problem(self, json_data):
        """
        Formulate the optimization problem based on the JSON input.

        Parameters:
            json_data (dict): Input JSON representing the network.

        Returns:
            dict: Formulated optimization problem with CasADi MX variables.
        """
        network = json_data["network"]

        # Extract network details
        nodes = network["nodes"]
        branches = network["branches"]
        parameters = network["parameters"]

        time_steps = parameters["time_steps"]
        voltage_limits = parameters["voltage_limits"]
        u_min = voltage_limits["min"] ** 2
        u_max = voltage_limits["max"] ** 2

        # Variables
        num_nodes = len(nodes)
        num_branches = len(branches)

        # Decision variables
        u = casadi.MX.sym("u", num_nodes, time_steps)  # Squared voltage
        active_power = casadi.MX.sym("active_power", num_nodes, time_steps)
        reactive_power = casadi.MX.sym("reactive_power", num_nodes, time_steps)
        power_flow = casadi.MX.sym("power_flow", num_branches, time_steps)
        status = casadi.MX.sym("status", num_nodes, time_steps)

        # Parameters
        load_forecast = [casadi.MX([0] * time_steps) for _ in nodes]
        guaranteed_active_power = [0] * len(nodes)
        guaranteed_reactive_power = [0] * len(nodes)

        for node in nodes:
            idx = int(node["id"]) - 1
            if "load" in node:
                load_forecast[idx] = casadi.MX([node["load"]["P"]] * time_steps)
                guaranteed_active_power[idx] = node["load"].get("P_guaranteed", 0)
                guaranteed_reactive_power[idx] = node["load"].get("Q_guaranteed", 0)

        # Constraints
        constraints = []

        # Voltage limits (squared voltage)
        for i in range(num_nodes):
            for t in range(time_steps):
                constraints.append(u[i, t] >= u_min)
                constraints.append(u[i, t] <= u_max)

        # Power flow thermal limits
        for b, branch in enumerate(branches):
            thermal_limit = branch["thermal_limit"]
            for t in range(time_steps):
                constraints.append(power_flow[b, t] <= thermal_limit)

        # User demand constraints
        for i in range(num_nodes):
            if guaranteed_active_power[i] > 0:
                for t in range(time_steps):
                    constraints.append(
                        active_power[i, t]
                        == status[i, t] * guaranteed_active_power[i]
                        + (1 - status[i, t]) * load_forecast[i][t]
                    )
                    constraints.append(
                        reactive_power[i, t]
                        == status[i, t] * guaranteed_reactive_power[i]
                        + (1 - status[i, t]) * load_forecast[i][t]
                    )

        # Power flow equations (simplified linear DistFlow with squared voltage)
        for b, branch in enumerate(branches):
            from_node = int(branch["from"]) - 1
            to_node = int(branch["to"]) - 1
            R = branch["impedance"]["R"]
            X = branch["impedance"]["X"]
            for t in range(time_steps):
                constraints.append(
                    u[to_node, t]
                    == u[from_node, t]
                    - 2 * (R * active_power[to_node, t] + X * reactive_power[to_node, t])
                )

        # Objective: Minimize user discomfort (sum of active status variables)
        objective = casadi.sum1(casadi.sum2(status))

        # Problem formulation
        problem = {
            "x": casadi.vertcat(
                casadi.vec(u),
                casadi.vec(power_flow),
                casadi.vec(active_power),
                casadi.vec(reactive_power),
                casadi.vec(status),
            ),
            "p": casadi.vertcat(),
            "g": casadi.vertcat(*constraints),
            "f": objective,
            "p_values": [],
            "lbx": [-casadi.inf]
            * (num_nodes * time_steps * 4 + num_branches * time_steps),
            "ubx": [casadi.inf]
            * (num_nodes * time_steps * 4 + num_branches * time_steps),
            "lbg": [0] * len(constraints),
            "ubg": [0] * len(constraints),
        }
        return problem


# Load JSON file
json_file = "network.json"
with open(json_file, "r") as file:
    network_data = json.load(file)

# Example usage
solver = Solver()
problem = solver.create_problem(network_data)
solution = solver.solve(problem)
print("Solution:", solution)
