import numpy as np

mat = np.array([[1, 2, 3], [4, 5, 6], [7, 8, 9]])
mat_sol = np.zeros((mat.shape))
print(mat.shape)
for i in range(mat.shape[0]):
    for j in range(min(i, mat.shape[1])):
        if mat[i, j] > 0:
            mat_sol[i, j] = mat[i, j]

print(mat_sol)