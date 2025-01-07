import matplotlib.pyplot as plt

# Data
time_points = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
s1_values_1 = [1, 1, 1, 0, 0, 0, 0, 0, 0, 1]
s1_values_2 = [1, 1, 1, 1, 1, 0, 0, 0, 0, 0]

s2_values_1 = [1, 1, 1, 0, 0, 1, 1, 1, 0, 0]
s2_values_2 = [0, 1, 0, 1, 0, 1, 0, 1, 0, 1]
# Create figure and subplots
plt.figure(figsize=(10, 3))

# First plot
plt.subplot(2, 1, 1)  # 2 rows, 1 column, 1st subplot
plt.plot(time_points, s1_values_1, marker='o', linestyle='-', color='b')
plt.plot(time_points, s1_values_2, marker='x', linestyle='-', color='g')
plt.title("Good")
plt.xlabel("Time")
plt.ylabel("S1")
plt.yticks([0, 1])  # Only show 0 and 1 on y-axis
plt.grid(True)

# Second plot
plt.subplot(2, 1, 2)  # 2 rows, 1 column, 2nd subplot
plt.plot(time_points, s2_values_1, marker='o', linestyle='-', color='r')
plt.plot(time_points, s2_values_2, marker='x', linestyle='-', color='y')
plt.title("Bad")
plt.xlabel("Time")
plt.ylabel("S2")
plt.yticks([0, 1])  # Only show 0 and 1 on y-axis
plt.grid(True)

# Adjust layout and save plot
plt.tight_layout()
plt.savefig("PPTFigure/connected_parallel_plots.png")
plt.show()
