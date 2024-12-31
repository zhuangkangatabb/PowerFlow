# Congestion Mitigation in Unbalanced Residential Networks

This repository contains a Python implementation of the optimization problem discussed in the paper:

Vanin, Marta & Van Acker, Tom & Ergun, Hakan & D’hulst, Reinhilde & Vanthournout, Koen & Hertem, Dirk. (2022). Congestion mitigation in unbalanced residential networks with OPF-based demand management. *Sustainable Energy, Grids and Networks, 32*, 100936. https://doi.org/10.1016/j.segan.2022.100936.

---

## Overview

This implementation models and solves the problem of congestion mitigation in unbalanced residential networks using Pyomo, a Python-based optimization modeling language. The original problem is described in the accompanying PDF file `PowerFlowmodel.pdf`.

### Key Modifications

Since the original problem in the paper is a Mixed-Integer Nonlinear Programming (MINLP) problem that cannot be solved by GLPK, the implementation includes the following adjustment:

- **Thermal Limit Constraint:**
  - Original: Constraints the $$\ell_2$$-norm.
  - Modified: Constraints the $$\ell_1$$-norm to ensure compatibility with GLPK.

---

## Requirements

### Python Packages

- **Pyomo**: Version 6.8.2
- Additional dependencies may include:
  - `numpy`
  - `scipy`

### Solver

- **GLPK**: GLPK LP/MIP Solver, version 4.65

> **Note:** The original MINLP formulation cannot be solved using GLPK. Adjustments have been made to enable compatibility.

---

## Files

1. **`PowerFlowmodel.pdf`**: Detailed description of the optimization problem as stated in the paper.
2. **`Optimization`**: Python implementation using the Pyomo package.

---

## Instructions

1. Install the required Python packages:
   ```bash
   pip install pyomo
   ```

2. Ensure that GLPK is installed and accessible from the command line. You can verify the installation using:
   ```bash
   glpsol --version
   ```

3. Run the optimization script. For example:
   ```bash
   python optimization_script.py
   ```

---

## Attention

- The problem as described in the paper is a MINLP problem. Due to solver limitations (GLPK cannot handle MINLP), adjustments were necessary to solve the problem using GLPK.
- For better performance and to handle the original formulation, consider using commercial solvers like Gurobi or CPLEX if they become available.

---

## Citation

If you use this implementation or derive inspiration for your work, please cite the original paper:

```text
Vanin, Marta & Van Acker, Tom & Ergun, Hakan & D’hulst, Reinhilde & Vanthournout, Koen & Hertem, Dirk. (2022). Congestion mitigation in unbalanced residential networks with OPF-based demand management. Sustainable Energy, Grids and Networks, 32, 100936. https://doi.org/10.1016/j.segan.2022.100936
```

---

## License

This project is distributed under the MIT License. See the `LICENSE` file for details.
