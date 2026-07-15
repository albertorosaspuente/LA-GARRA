import numpy as np
import math

#NO hay mucho que explicar aqui JAJAJAJAJ
class MathEngine:
    @staticmethod
    def get_identity():
        return np.identity(3, dtype=float)

    @staticmethod
    def get_translation_matrix(tx, ty):
        return np.array([
            [1, 0, tx],
            [0, 1, ty],
            [0, 0,  1]
        ], dtype=float)

    @staticmethod
    def get_rotation_matrix(angle_degrees):
        rad = math.radians(angle_degrees)
        cos_a = math.cos(rad)
        sin_a = math.sin(rad)
        return np.array([
            [cos_a, -sin_a, 0],
            [sin_a,  cos_a, 0],
            [0,      0,     1]
        ], dtype=float)

    @staticmethod
    def get_scale_matrix(sx, sy):
        return np.array([
            [sx, 0,  0],
            [0,  sy, 0],
            [0,  0,  1]
        ], dtype=float)

    @staticmethod
    def get_shear_matrix(shx, shy):
        return np.array([
            [1,   shx, 0],
            [shy, 1,   0],
            [0,   0,   1]
        ], dtype=float)

    @staticmethod
    def compose_matrices(*matrices):
        result = MathEngine.get_identity()
        for matrix in matrices:
            result = np.dot(result, matrix)
        return result

    @staticmethod
    def get_inverse(matrix):
        return np.linalg.inv(matrix)

    @staticmethod
    def get_euclidean_distance(p1, p2):
        return math.dist(p1, p2)
