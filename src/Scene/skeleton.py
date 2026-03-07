import numpy as np

class Skeleton:
    def __init__(): pass

    @staticmethod
    def interpolate(count: int, positions, rotations, coef) -> np.array:
        r = Skeleton.vslerp(positions, rotations, t)
        matrices = np.zeros((count, 4, 4), dtype=np.float32)

        #matrices[: :3, 3] = 