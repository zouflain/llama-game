import numpy as np
from scipy.spatial.transform import Rotation
import glm as GLM

import Systems, Events, Components

class CameraSystem(Systems.System):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.target_center: np.array = np.zeros(3, dtype=np.float32)
        self.source_center: np.array = np.zeros(3, dtype=np.float32)
        self.distance: float = 1000
        self.sharpness: float = 300
        self.last_view: GLM.mat4x4 = None

    @Systems.on(Events.Render, Systems.Priority.HIGHEST+100)
    async def appendView(self, event: Events.Render) -> Events.Result:
        # exponentially approach center
        self.source_center += (self.target_center-self.source_center) * np.exp(-self.sharpness*event.time_step)
        yaw = 225
        pitch = 30
        eye = self.source_center + Rotation.from_euler("zy", [yaw, pitch], degrees=True).apply(np.array([self.distance, 0, 0], dtype=np.float32))
        self.last_view = GLM.lookAt(tuple(eye.tolist()), tuple(self.source_center.tolist()), (0, 0, 1))
        event.view = self.last_view
        return event.result

    @Systems.on(Events.CameraUpdate, Systems.Priority.HIGHEST)
    async def updateCamera(self, event: Events.CameraUpdate) -> Events.Result:
        if event.target_center is not None:
          self.target_center = event.target_center

        if event.distance is not None and event.distance > 0:
            self.distance = event.distance

        if event.sharpness is not None and event.sharpness > 0:
            self.sharpness = event.sharpness
        return event.result

    @Systems.on(Events.CombatTick, Systems.Priority.DEFAULT+50)
    async def onCombatTick(self, event: Events.CombatTick) -> Events.Result:
        event.view = self.last_view
        return event.result

    @Systems.on(Events.CombatGUITick, Systems.Priority.DEFAULT+50)
    async def onCombatGUITick(self, event: Events.CombatGUITick) -> Events.Result:
        event.view = self.last_view
        return event.result