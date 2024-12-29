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

        # Variables
        voltage = casadi.MX.sym("voltage", len(nodes), time_steps)
        power_flow = casadi.MX.sym("power_flow", len(branches), time_steps)
        active_power = casadi.MX.sym("active_power", len(nodes), time_steps)
        reactive_power = casadi.MX.sym("reactive_power", len(nodes), time_steps)
        status = casadi.MX.sym("status", len(nodes), time_steps)

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

        # Voltage limits
        for t in range(time_steps):
            for n, node in enumerate(nodes):
                constraints.append(voltage_limits["min"] - voltage[n, t])
                constraints.append(voltage[n, t] - voltage_limits["max"])

        # Power flow equations
        for b, branch in enumerate(branches):
            from_node = int(branch["from"]) - 1
            to_node = int(branch["to"]) - 1
            R, X = branch["impedance"]["R"], branch["impedance"]["X"]

            for t in range(time_steps):
                # Active and reactive power flow constraints
                constraints.append(
                    active_power[from_node, t]
                    - active_power[to_node, t]
                    - power_flow[b, t]
                )
                constraints.append(
                    reactive_power[from_node, t]
                    - reactive_power[to_node, t]
                    - X / R * power_flow[b, t]
                )

                # Voltage drop constraints
                constraints.append(
                    voltage[from_node, t]
                    - voltage[to_node, t]
                    - (
                        R * active_power[from_node, t]
                        + X * reactive_power[from_node, t]
                    )
                )

        # User response constraints
        for t in range(time_steps):
            for n, node in enumerate(nodes):
                # Active power based on status
                constraints.append(
                    active_power[n, t]
                    - (
                        status[n, t] * guaranteed_active_power[n]
                        + (1 - status[n, t]) * load_forecast[n][t]
                    )
                )
                # Reactive power based on status
                constraints.append(
                    reactive_power[n, t]
                    - (
                        status[n, t] * guaranteed_reactive_power[n]
                        + (1 - status[n, t])
                        * 0  # Assuming no forecasted reactive load if not specified
                    )
                )

        # Objective: Minimize user discomfort (sum of active status variables)
        objective = casadi.sum1(casadi.sum2(status))

        # Problem formulation
        problem = {
            "x": casadi.vertcat(
                casadi.vec(voltage),
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
            * (len(nodes) * time_steps * 4 + len(branches) * time_steps),
            "ubx": [casadi.inf]
            * (len(nodes) * time_steps * 4 + len(branches) * time_steps),
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
