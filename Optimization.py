import json
from pyomo.environ import *
from cmath import exp, pi
from math import cos, sin, pi

# Load JSON network data
with open("network.json", "r") as file:
    data = json.load(file)

# Extract data
nodes = data["network"]["nodes"]
branches = data["network"]["branches"]
parameters = data["network"]["parameters"]
time_steps = parameters["time_steps"]

# Initialize model
model = ConcreteModel()

# Sets
model.T = RangeSet(1, time_steps)
model.Nodes = Set(initialize=[node["id"] for node in nodes])
model.Branches = Set(initialize=[branch["id"] for branch in branches])
model.Phases = Set(initialize=parameters["phases"])

# Define the rotation matrix gamma
alpha = exp(-1j * 2 * pi / 3)  # Complex number e^(-i * 2π/3)
gamma = [[1, alpha**2, alpha], [alpha, 1, alpha**2], [alpha**2, alpha, 1]]
# Parameters
voltage_min = parameters["voltage_limits"]["min"] ** 2
voltage_max = parameters["voltage_limits"]["max"] ** 2

# Decision Variables
model.s = Var(
    model.Nodes, model.T, domain=Binary, initialize=0
)  # Power reduction status
model.y = Var(
    model.Nodes, model.T, domain=Binary, initialize=0
)  # Activation of reduction actions
model.z = Var(
    model.Nodes, model.T, domain=Binary, initialize=0
)  # Deactivation of reduction actions
model.u = Var(
    model.Nodes, model.Phases, model.T, domain=NonNegativeReals, initialize=0
)  # Voltage magnitude squared
model.P = Var(
    model.Nodes, model.Phases, model.T, initialize=0
)  # Active power, it is positive for generation and negative for consumption
model.Q = Var(
    model.Nodes, model.Phases, model.T, initialize=0
)  # Reactive power, it is positive for generation and negative for consumption
model.P_flow = Var(
    model.Branches, model.Phases, model.T, domain=NonNegativeReals, initialize=0
)  # Active power flow
model.Q_flow = Var(
    model.Branches, model.Phases, model.T, domain=NonNegativeReals, initialize=0
)  # Reactive power flow



# Objective Function: Minimize user discomfort
def objective_rule(model):
    return sum(model.s[n, t] for n in model.Nodes for t in model.T)


model.Objective = Objective(rule=objective_rule, sense=minimize)

# Constraints
model.constraints = ConstraintList()

# 1. User demand constraints
for node in nodes:
    if "load" in node:
        n = node["id"]
        load = node["load"]
        for t in model.T:
            for phase in model.Phases:
                model.constraints.add(
                    -model.P[n, phase, t]
                    == model.s[n, t] * load["P_guaranteed"]
                    + (1 - model.s[n, t]) * load["P_forecasted"][phase]
                )

                model.constraints.add(
                    -model.Q[n, phase, t]
                    == model.s[n, t] * load["Q_guaranteed"]
                    + (1 - model.s[n, t]) * load["Q_forecasted"][phase]
                )

# 2. Voltage limits
for node in nodes:
    n = node["id"]
    for t in model.T:
        for phase in model.Phases:
            model.constraints.add(voltage_min <= model.u[n, phase, t])
            model.constraints.add(model.u[n, phase, t] <= voltage_max)

# 3. Thermal limits
for branch in branches:
    b = branch["id"]
    for t in model.T:
        for phase in model.Phases:
            model.constraints.add(
                model.P_flow[b, phase, t]+ model.Q_flow[b, phase, t]<= branch["thermal_limit"]
            )
# 4. Power flow balance constraints
for node in nodes:
    n = node["id"]
    for t in model.T:
        for phase in model.Phases:
            # Active power balance
            model.constraints.add(
                sum(model.P_flow[b["id"], phase, t] for b in branches if b["to"] == n)
                + model.P[n, phase, t]
                == sum(
                    model.P_flow[b["id"], phase, t] for b in branches if b["from"] == n
                )
            )
            # Reactive power balance
            model.constraints.add(
                sum(model.Q_flow[b["id"], phase, t] for b in branches if b["to"] == n)
                + model.Q[n, phase, t]
                == sum(
                    model.Q_flow[b["id"], phase, t] for b in branches if b["from"] == n
                )
            )

# 5. Voltage approximation using Ohm's Law
for branch in branches:
    from_node = branch["from"]
    to_node = branch["to"]
    impedance = branch["impedance"]
    for t in model.T:
        for phase in model.Phases:
            R = impedance["R"][phase]
            X = impedance["X"][phase]
            model.constraints.add(
                model.u[to_node, phase, t]
                == model.u[from_node, phase, t]
                - 2
                * (
                    R * model.P_flow[branch["id"], phase, t]
                    + X * model.Q_flow[branch["id"], phase, t]
                )
            )

# Solve the model
solver = SolverFactory("glpk")
results = solver.solve(model, tee=True)

# Display Results
print("Optimization Results:")
for n in model.Nodes:
    for t in model.T:
        for phase in model.Phases:
            s_value = value(model.s[n, t])
            P_value = value(model.P[n, phase, t])
            Q_value = value(model.Q[n, phase, t])
            u_value = value(model.u[n, phase, t])
            voltage_value = sqrt(u_value)
            # Check if any variable has a valid value
            if (
                s_value is not None
                or P_value is not None
                or Q_value is not None
                or u_value is not None
            ):
                print(
                    f"Node {n}, Phase {phase}, Time {t}: Status = {s_value}, P = {P_value}, Q = {Q_value}, Voltage = {voltage_value}"
                )
for b in model.Branches:
    for t in model.T:
        for phase in model.Phases:
            Acitve_Power_value = value(model.P_flow[b, phase, t])
            Reactive_Power_value = value(model.Q_flow[b, phase, t])
            if (
                s_value is not None
                or P_value is not None
                or Q_value is not None
                or u_value is not None
            ):
                print(f"Branch {b}, Phase {phase}, Time {t}: Active Power Flow = {Acitve_Power_value}, Reactive Power Flow = {Reactive_Power_value}")
