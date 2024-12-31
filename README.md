This is a python implementation of Paper 

Vanin, Marta & Van Acker, Tom & Ergun, Hakan & D’hulst, Reinhilde & Vanthournout, Koen & Hertem, Dirk. (2022). Congestion mitigation in unbalanced residential networks with OPF-based demand management. Sustainable Energy, Grids and Networks. 32. 100936. 10.1016/j.segan.2022.100936. 

# PowerFlowmodel.pdf
This is a PDF file which states the optimization problem clearly. 

# Optimization
This is an implementation with python package Pyomo. 

Since Gurobi is not available for me, I modified the the Thermal limit. Instead of contrainting its $$\ell_2$$-norm, I constrainted its $$ell_1$$-norm.

# Attention

The original problem in the PDF is a MINLP problem which can not be solved by GLPK. 

# Package
Pyomo 6.8.2
GLPSOL: GLPK LP/MIP Solver, v4.65