from __future__ import annotations
from enum import Enum
import OpenGL.GL as GL
import glm as GLM
import sdl2 as SDL
import numpy as np
import pymunk
import random
from scipy.spatial.transform import Rotation

import Systems, Events, Components, Resources


class Battle(Systems.System):
    class Constants (int, Enum):
        COLOR = 0
        WORLD = 1
        DEPTH = 2
        NORMALS = 3
        OUTPUT = 4

        IMAGE_UNIT = 32  # size of an individual image unit (for subdivision of compute shader)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.world: pymunk.space = None
        self.randomizer: random.Random = random.Random()

    async def boot(self, render_size: tuple[int, int]) -> bool:
        self.render_shader = await Resources.Shader.generate(name="renderable", permanent=True, fname="renderable.vert")
        self.sobel_shader = await Resources.Shader.generate(name="outlines", permanent=True, fname="outlines.comp")
        self.glyph_shader = await Resources.Shader.generate(name="glyphs", permanent=True, fname="text.comp")
        self.world = pymunk.Space()

        return True

    @Systems.on(Events.Render, Systems.Priority.HIGHEST)
    async def onRenderStep(self, event: Events.Render) -> Events.Result:
        GL.glClearColor(0,0,0,0)
        GL.glClear(GL.GL_COLOR_BUFFER_BIT|GL.GL_DEPTH_BUFFER_BIT)

        #### TEST CODE ####
        view = GLM.lookAt((1000, -1000, 1000), (0, 0, 0), (0, 0, 1))
        projection = GLM.ortho(-event.framebuffer.resolution[0]/2, event.framebuffer.resolution[0]/2, -event.framebuffer.resolution[1]/2, event.framebuffer.resolution[1]/2, 0, 10000)
        #### END TEST CODE ####

        GL.glEnable(GL.GL_DEPTH_TEST)
        with Resources.Framebuffer.Binding(event.framebuffer, event.resolution):
            GL.glClearColor(0.05,0.05,0.05,1)
            GL.glClear(GL.GL_COLOR_BUFFER_BIT|GL.GL_DEPTH_BUFFER_BIT)
            with Resources.Shader.Binding(self.render_shader) as render_prog:
                GL.glUniformMatrix4fv(Resources.Renderable.Bindings.VIEW, 1, False, GLM.value_ptr(view))
                GL.glUniformMatrix4fv(Resources.Renderable.Bindings.PROJ, 1, False, GLM.value_ptr(projection))
                for eid, combatant in Components.Combatant.getAll():
                    model = np.eye(4)
                    model[:3, :3] = Rotation.from_euler('z', combatant.facing, degrees=True).as_matrix() * np.array([combatant.scale]*3)[np.newaxis, :]#TODO add scale here
                    model[3, :3] = combatant.pos
                    model[3, 3] = 1.0
                    Resources.Renderable[combatant.mannequin].draw(render_prog, model, combatant.active_meshes, [Resources.Renderable.BlendFactor(**anim) for anim in combatant.animations])

            with Resources.Shader.Binding(self.sobel_shader):
                GL.glMemoryBarrier(GL.GL_SHADER_IMAGE_ACCESS_BARRIER_BIT)
                GL.glBindImageTexture(Battle.Constants.COLOR, event.framebuffer.textures[GL.GL_COLOR_ATTACHMENT0], 0, GL.GL_FALSE, 0, GL.GL_READ_ONLY, GL.GL_RGBA32F)
                GL.glBindImageTexture(Battle.Constants.WORLD, event.framebuffer.textures[GL.GL_COLOR_ATTACHMENT1], 0, GL.GL_FALSE, 0, GL.GL_READ_ONLY, GL.GL_RGBA32F)
                GL.glBindImageTexture(Battle.Constants.DEPTH, event.framebuffer.textures[GL.GL_COLOR_ATTACHMENT2], 0, GL.GL_FALSE, 0, GL.GL_READ_ONLY, GL.GL_RGBA32F)
                GL.glBindImageTexture(Battle.Constants.NORMALS, event.framebuffer.textures[GL.GL_COLOR_ATTACHMENT3], 0, GL.GL_FALSE, 0, GL.GL_READ_ONLY, GL.GL_RGBA32F)

                GL.glBindImageTexture(Battle.Constants.OUTPUT, event.framebuffer.textures[GL.GL_COLOR_ATTACHMENT4], 0, GL.GL_FALSE, 0, GL.GL_WRITE_ONLY, GL.GL_RGBA32F)
                GL.glDispatchCompute(int(event.framebuffer.resolution[0]/32)+1, int(event.framebuffer.resolution[1]/32)+1, 1, 0)
                GL.glMemoryBarrier(GL.GL_SHADER_IMAGE_ACCESS_BARRIER_BIT)

            '''
            with Resources.Shader.Binding(self.glyph_shader) as glyph_program:
                Resources.GlyphSet["font"].draw(
                    #glyph_program, event.resolution, event.framebuffer.textures[GL.GL_COLOR_ATTACHMENT4], "Hello world!\n#ff0000TEST!", (0, 0), 32, (1184,96), (0,1,1)
                    glyph_program, event.resolution, event.framebuffer.textures[GL.GL_COLOR_ATTACHMENT4],
                    #"ABCDEFGHIJKLMNOPQRSTUVWXYZ\nabcdefghijklmnopqrstuvwxyz\n0123456789'\"+_)(&^%$@!`?.><\\/)",
                    "You there! Out of the WAY!\nKeep standin' there and you'll\nget knocked into the ocean!",
                    (0, 0), 32, (1184,96), (0,1,1)
                )
            '''

        return Events.Result.CONTINUE

    @Systems.on(Events.Logic, Systems.Priority.DEFAULT)
    async def onLogicStep(self, event: Events.Logic) -> Events.Result:
        await Systems.immediateEvent(Events.CombatTick(0))# Update stats, trigger damage, effects, etc
        await Systems.immediateEvent(Events.CombatManueverPhase(event.dt)) # Move actors (if possible)
        return Events.Result.CONTINUE

    @Systems.on(Events.CombatManueverPhase, Systems.Priority.LOWEST)
    async def onCombatTick(self, event: Events.CombatManueverPhase) -> Events.Result:
        combatants = Components.Combatant.getAll()
        combatant_count = len(combatants)

        # Map combat space
        angles = np.linspace(0, 2*np.pi, 16, endpoint=False)
        vectors = np.empty((combatant_count, 16, 2), dtype=np.float32)
        vectors[:, :, 0] = np.cos(angles)
        vectors[:, :, 1] = np.sin(angles)

        pos = np.array([combatant.pos[:2] for eid, combatant in combatants])
        delta_pos = pos[:, np.newaxis, :] - pos[np.newaxis, :, :]
        delta_norms = np.linalg.norm(delta_pos, axis=2)
        with np.errstate(divide="ignore", invalid="ignore"):
            delta_dir = np.nan_to_num(delta_pos / delta_norms[:, :, np.newaxis])
        dots = np.einsum("aik,ajk->aij", vectors, delta_dir)

        # Setup interests array
        eid_lookup = {
            eid: i for i, (eid, _) in enumerate(combatants)
        }
        relationships = np.zeros((combatant_count, combatant_count), dtype=np.int32)
        postures = np.zeros(combatant_count, dtype=np.int32)
        for i, (source, source_combatant) in enumerate(combatants):
            relationships[i] = [
                0 if other == source
                else 1 if other == source_combatant.target
                else 2 if other_combatant.party_id == source_combatant.party_id
                else 3
                for other, other_combatant in combatants
            ]
            postures[i] = source_combatant.posture

        posture_matrix = np.array(
            ( # SELF, TARGET, FRIENDLY, HOSTILE
                [0, 0, 0, 1], #EVASIVE
                [0, -1, 0, -0.5], #AGGRESSIVE
                [0, -1, -0.1, -0.35], #DEFENSIVE
                [0, 0, 0, 0], #PASSIVE/flat footed
            ),
            dtype=np.float32
        )
        interests = posture_matrix[postures[:, np.newaxis], relationships]
        interests_map = np.einsum("aij,aj->ai", dots, interests)

        #Raycast and zero out collision directions
        blocked = np.zeros((combatant_count, 16), dtype=np.float32)
        for i, (eid, combatant) in enumerate(combatants):
            filter = pymunk.ShapeFilter(group=eid)
            for j in range(16):
                offset_pos = tuple(np.array(combatant.body.position, dtype=np.float32)+vectors[i][j]*combatant.speed)
                collision = self.world.segment_query_first(combatant.body.position, offset_pos, combatant.size, filter)
                blocked[i][j] = 0 if collision else 1

        # Choose best option
        decollided_interests = interests_map*blocked
        preferred_indices = np.argmax(decollided_interests, axis=1)
        chosen_vectors = vectors[np.arange(combatant_count), preferred_indices]
        chosen_norms = np.linalg.norm(chosen_vectors, axis=1, keepdims=1)
        with np.errstate(divide='ignore', invalid='ignore'):
            chosen_normalized = chosen_vectors / chosen_norms
        nonzero = np.max(decollided_interests, axis=1) > 1e-5
        eliminators = (nonzero & ~np.all(blocked==0, axis=1))[:, np.newaxis]
        chosen_final  = chosen_normalized * eliminators

        for i,(eid, combatant) in enumerate(combatants):
            match combatant.status:
                case Components.Combatant.Status.MANUEVER | Components.Combatant.Status.ACT:
                    velocity = chosen_final[i][:2]*combatant.speed
                    combatant.body.velocity = tuple(velocity)

        self.world.step(event.dt)
        for i,(eid, combatant) in enumerate(combatants):
            combatant.pos = np.append(combatant.body.position, 0)

        return Events.Result.CONTINUE

    @Systems.on(Events.SpawnCombatant, Systems.Priority.HIGHEST)
    async def onSpawnCombatant(self, event: Events.SpawnCombatant) -> Events.Result:
        Components.Character(event.eid)
        theta = 2*np.pi*self.randomizer.random()
        distance = 300
        pos = [
            (np.cos(theta)*distance).item(),
            (np.sin(theta)*distance).item(),
            0.
        ]
        body = pymunk.Body(mass=100, moment=float('inf'), body_type=pymunk.Body.DYNAMIC)
        body.position = tuple(pos[:2])
        shape = pymunk.Circle(body, 100)
        shape.filter = pymunk.ShapeFilter(group=event.eid)
        self.world.add(body, shape)
        event.combatant = Components.Combatant(
            party_id=event.party_id,
            eid=event.eid,
            pos=pos,
            body=body,
            mannequin="mage",
            active_meshes=[
                mesh for mesh in Resources.Renderable["mage"].meshes.keys() if mesh not in [
                    "Icosphere", "Spellbook", "Spellbook_open",# "Mage_Hat",
                    "Mage_Cape", "2H_Staff", "1H_Wand"
                ]
            ]
        )
        return Events.Result.CONTINUE

    @Systems.on(Events.BattleBegin, Systems.Priority.LOWEST)
    async def onBattleBegin(self, event: Events.BattleBegin) -> Event.Result:
        self.world = pymunk.world()

        return Events.Result.CONTINUE

    @Systems.on(Events.BattleEnd, Systems.Priority.LOWEST)
    async def onBattleEnd(self, event: Events.BattleEnd) -> Event.Result:
        for eid, combatant in Components.Combatant.getAll():
            Components.Combatant.remove(eid)
        self.world = None
        return Events.Result.CONTINUE
