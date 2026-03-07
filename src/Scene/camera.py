import glm as GLM


class Camera:
    def __init__(self):
        self.ortho: tuple[float, float, float, float, float, float] = (0, 640, 0, 480, -1, 1000)
        self.eye: tuple[float, float, float] = (0, 0, 0)
        self.center: tuple[float, float, float] = (1, 0, 0)
        self.up: tuple[float, float, float] = (0, 0, 1)

    def orthoMatrix(self) -> GLM.fmat4x4:
        return GLM.ortho(self.ortho[0], self.ortho[1], self.ortho[2], self.ortho[3], self.ortho[4], self.ortho[5])

    def viewMatrix(self) -> GLM.fmat4x4:
        return GLM.lookAt(self.eye, self.center, self.up)