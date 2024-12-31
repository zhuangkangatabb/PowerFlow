This is a python implementation of Paper 

Vanin, Marta & Van Acker, Tom & Ergun, Hakan & D’hulst, Reinhilde & Vanthournout, Koen & Hertem, Dirk. (2022). Congestion mitigation in unbalanced residential networks with OPF-based demand management. Sustainable Energy, Grids and Networks. 32. 100936. 10.1016/j.segan.2022.100936. 

# Pyomo
This is an implementation with python package Pyomo. 

Since Gurobi is not available for me, I modified the the Thermal limit. Instead of contrainting its $$\ell_2$$-norm, I constrainted its $$ell_1$$-norm.