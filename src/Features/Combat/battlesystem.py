from __future__ import annotations
from enum import Enum, auto as EnumAuto
import OpenGL.GL as GL
import glm as GLM
import sdl2 as SDL
import numpy as np
import pymunk
import random
import logging

import Systems, Events, Components, Resources

class Battle(Systems.System):
    class Constants (int, Enum):
        COLOR = 0
        WORLD = 1
        DEPTH = 2
        NORMALS = 3
        OUTPUT = 4

        IMAGE_UNIT = 32  # size of an individual image unit (for subdivision of compute shader)
        NUM_WHISKERS = 32
        MAX_DISTANCE_CONSIDERED = 1000
        MAX_STRAFE_DISTANCE = 500

    class State(int, Enum):
        READY = EnumAuto()
        AWAIT_GUI = EnumAuto()
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.world: pymunk.space = None
        self.world_bound: pymunk.Body = None
        self.randomizer: random.Random = random.Random()
        self.state: Battle.State = None
        self.camera_target = None
        self.last_projection = None
        self.last_resolution = None

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
        self.last_projection = GLM.ortho(-event.framebuffer.resolution[0]/2, event.framebuffer.resolution[0]/2, -event.framebuffer.resolution[1]/2, event.framebuffer.resolution[1]/2, 0, 10000)
        self.last_resolution = event.framebuffer.resolution

        GL.glEnable(GL.GL_DEPTH_TEST)
        with Resources.Framebuffer.Binding(event.framebuffer, event.resolution):
            GL.glClearColor(0.05,0.05,0.05,1)
            GL.glClear(GL.GL_COLOR_BUFFER_BIT|GL.GL_DEPTH_BUFFER_BIT)
            with Resources.Shader.Binding(self.render_shader) as render_prog:
                GL.glUniformMatrix4fv(Resources.Renderable.Bindings.VIEW, 1, False, GLM.value_ptr(event.view))
                GL.glUniformMatrix4fv(Resources.Renderable.Bindings.PROJ, 1, False, GLM.value_ptr(self.last_projection))
                for eid, combatant in Components.Combatant.getAll():
                    Resources.Renderable[combatant.mannequin].draw(render_prog, combatant.model, combatant.active_meshes, [Resources.Renderable.BlendFactor(**anim) for anim in combatant.animations])

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

        return event.result

    @Systems.on(Events.Logic, Systems.Priority.DEFAULT)
    async def onLogicStep(self, event: Events.Logic) -> Events.Result:
        match self.state:
            case Battle.State.READY:
                tick_result = (await Systems.immediateEvent(Events.CombatTick(dt=event.time_step, last_projection=self.last_projection, last_resolution=self.last_resolution))).result# Update stats, trigger damage, effects, etc
                if tick_result == Events.Result.FINISHED:
                    await Systems.immediateEvent(Events.CombatManueverPhase(event.time_step)) # Move actors (if possible)
            case Battle.State.AWAIT_GUI:
                await Systems.immediateEvent(Events.CombatGUITick(dt=event.time_step, projection=self.last_projection, resolution=self.last_resolution))
        

        if not self.camera_target:
            centroid = np.zeros(3, dtype=np.float32)
            combatants = Components.Combatant.getAll()
            combatant_count = len(combatants)
            if combatant_count > 0:
                for _, combatant in combatants:
                    centroid += combatant.pos
                centroid /= combatant_count
            await Systems.immediateEvent(Events.CameraUpdate(target_center=centroid, sharpness=300))
        else:
            await Systems.immediateEvent(Events.CameraUpdate(target_center=Components.Combatant[self.camera_target].pos, sharpness=100))
        return event.result

    @Systems.on(Events.CombatTick, Systems.Priority.LOWEST)
    async def onCombatTick(self, event: Events.CombatTick) -> Events.Result:
        combatants = Components.Combatant.getAll()
        player_party = None
        players = Components.find([Components.Player, Components.Combatant])
        if players:
            player = Components.Combatant[players[0]]
            player_party = player.party_id

        for eid, combatant in combatants:
            # Respond to stagger
            if combatant.stagger > 100:
                await Systems.immediateEvent(Events.BeginStagger(eid=eid))

            #advance animation?

            # Advance progress
            match combatant.status:
                case Components.Combatant.Status.MANUEVER:
                    combatant.progress += combatant.progress_speed * event.dilation * event.dt
                    if combatant.progress > 100:
                        combatant.progress = 0
                        combatant.status = Components.Combatant.Status.ACT
                        print(f"{eid} READY!")
                        if combatant.party_id == player_party: #STOP and await GUI
                            self.camera_target = eid
                            event.setResult(Events.Result.TERMINATE)
                            self.state = Battle.State.AWAIT_GUI
                            await Systems.immediateEvent(Events.PlayerCombatantReady(eid))
                            break
                        else:
                            await Systems.immediateEvent(Events.AICombatantReady(eid))
                case Components.Combatant.Status.ACT:
                    action = Resources.CombatAction[combatant.action]
                    if action:
                        target = combatant.target
                        target_combatant = Components.Combatant[combatant.target]
                        distance = np.linalg.norm(target_combatant.pos - combatant.pos)
                        if distance < float(combatant.size+target_combatant.size)+action.range:
                            x = action.onHook("damage")
                            for evt, fields in action.onHook("damage"):
                                child_evt = Events.get(evt)
                                if child_evt is not None:
                                    Systems.raiseEvent(child_evt(eid=eid, target=combatant.target, **fields))
                                else:
                                    print(f"BAD EVENT {evt}")
                                    pass # ANOTHER script error warning needed
                    else:
                        pass # TODO: major warning needed
        return event.result

    @Systems.on(Events.CombatManueverPhase, Systems.Priority.LOWEST)
    async def onManueverPhase(self, event: Events.CombatManueverPhase) -> Events.Result:
        combatants = Components.Combatant.getAll()
        combatant_count = len(combatants)

        # Map combat space
        angles = np.linspace(0, 2*np.pi, Battle.Constants.NUM_WHISKERS, endpoint=False)
        vectors = np.empty((combatant_count, Battle.Constants.NUM_WHISKERS, 2), dtype=np.float32)
        vectors[:, :, 0] = np.cos(angles)
        vectors[:, :, 1] = np.sin(angles)

        pos = np.array([combatant.pos[:2] for _, combatant in combatants])
        delta_pos = pos[:, np.newaxis, :] - pos[np.newaxis, :, :]
        distances = np.linalg.norm(delta_pos, axis=2)
        with np.errstate(divide="ignore", invalid="ignore"):
            delta_dir = np.nan_to_num(delta_pos / distances[:, :, np.newaxis])
        dots = np.einsum("aik,ajk->aij", vectors, delta_dir)

        # Setup interests array
        eid_lookup = {
            eid: i for i, (eid, _) in enumerate(combatants)
        }
        relationships = np.zeros((combatant_count, combatant_count), dtype=np.int32)
        postures = np.zeros((combatant_count, 4), dtype=np.float32)
        directions = np.zeros((combatant_count, 2), dtype=np.float32)
        turn_speeds = np.zeros(combatant_count, dtype=np.float32)
        has_target = np.zeros(combatant_count, dtype=np.int32)
        target_directions = np.zeros((combatant_count, 2), dtype=np.float32)
        for i, (source, source_combatant) in enumerate(combatants):
            relationships[i] = [
                Components.Combatant.Relationship.SELF if other == source
                else Components.Combatant.Relationship.TARGET if other == source_combatant.target
                else Components.Combatant.Relationship.PARTY if other_combatant.party_id == source_combatant.party_id
                else Components.Combatant.Relationship.NONPARTY
                for other, other_combatant in combatants
            ]
            postures[i] = np.array(source_combatant.posture, dtype=np.float32)
            directions[i] = source_combatant.forward[:2]
            turn_speeds[i] = np.radians(source_combatant.turn_speed)
            has_target[i] = 0
            if source_combatant.target is not None and source_combatant.target in eid_lookup:
                has_target[i] = 1
                target_directions[i] = (Components.Combatant[source_combatant.target].pos - source_combatant.pos)[:2]

        relations_map = postures[np.arange(combatant_count)[:, np.newaxis], relationships]
        interests_map = np.full((combatant_count, Battle.Constants.NUM_WHISKERS), 0, dtype=np.float32)
        cross_interests = dots * relations_map[:, np.newaxis, :]
        #tangent_interests = 1.0-np.abs(dots)
        #tangent_distances = 1.0 - np.clip(effective_distances, 0.0, float(Battle.Constants.MAX_DISTANCE_CONSIDERED))/float(Battle.Constants.MAX_DISTANCE_CONSIDERED)
        effective_distances = np.where(relationships == Components.Combatant.Relationship.TARGET, 0.0, distances)
        scaled_distances = 1.0 - np.clip(effective_distances, 0.0, float(Battle.Constants.MAX_DISTANCE_CONSIDERED))/float(Battle.Constants.MAX_DISTANCE_CONSIDERED)
        scaled_cross = cross_interests * scaled_distances[:, np.newaxis, :]
        interests_map += np.sum(scaled_cross, axis=2)
        #interests_map += np.min(cross_interests, axis=2)
        #interests_map += np.einsum("aij,aj->ai", dots, relations_map)
        #interests_map += np.einsum("aik,ak->ai", vectors, directions) * 0.2#0.05


        is_moving = np.sum(np.abs(postures), axis=1) > 0

        #Raycast and -inf out collision directions
        blocked = np.zeros((combatant_count, Battle.Constants.NUM_WHISKERS), dtype=np.float32)
        for i, (eid, combatant) in enumerate(combatants):
            filter = pymunk.ShapeFilter(group=eid)
            for j in range(Battle.Constants.NUM_WHISKERS):
                offset_pos = tuple(np.array(combatant.body.position, dtype=np.float32)+vectors[i][j]*combatant.size*3)
                collision = self.world.segment_query_first(combatant.body.position, offset_pos, combatant.size, filter)
                blocked[i][j] = 1 if collision else 0
        #decollided_interests = np.where(blocked.astype(bool), -float('inf'), interests_map)
        decollided_interests = np.where(blocked.astype(bool), -1, interests_map)

        # Choose best option
        '''preferred_indices = np.argmax(decollided_interests, axis=1)
        chosen_vectors = vectors[np.arange(combatant_count), preferred_indices]
        chosen_norms = np.linalg.norm(chosen_vectors, axis=1, keepdims=1)
        with np.errstate(divide='ignore', invalid='ignore'):
            chosen_normalized = chosen_vectors / chosen_norms
        chosen_final  = chosen_normalized * is_moving[:, np.newaxis]'''
        chosen_vectors = np.sum(vectors * decollided_interests[:, :, np.newaxis], axis=1)
        chosen_norms = np.linalg.norm(chosen_vectors, axis=1, keepdims=True)
        with np.errstate(divide='ignore', invalid='ignore'):
            #chosen_normalized = chosen_vectors / chosen_norms
            chosen_normalized = np.divide(chosen_vectors, chosen_norms, out=np.zeros_like(chosen_vectors), where=chosen_norms > 1e-5)

        chosen_final  = chosen_normalized * is_moving[:, np.newaxis]



        # Rotate forward towards final
        target_norms = np.linalg.norm(target_directions, axis=1, keepdims=1)
        with np.errstate(divide='ignore', invalid='ignore'):
            target_directions = target_directions / target_norms
        angle_forward = np.arctan2(directions[:, 1], directions[:, 0])
        desired_forward = np.where(
            has_target[:, np.newaxis] == 1,
            target_directions,
            np.where(is_moving[:, np.newaxis], chosen_final, directions)
        )

        angle_chosen = np.arctan2(desired_forward[:, 1], desired_forward[:, 0])
        angle_diffs = (angle_chosen-angle_forward+np.pi) % (2*np.pi) - np.pi
        clipped_diffs = np.clip(angle_diffs, -turn_speeds*event.dt, turn_speeds*event.dt)
        angle_final = angle_forward + clipped_diffs
        forward_final = np.zeros_like(directions)
        forward_final[:, 0] = np.cos(angle_final)
        forward_final[:, 1] = np.sin(angle_final)


        for i,(eid, combatant) in enumerate(combatants):
            match combatant.status:
                case Components.Combatant.Status.LOCKED:
                    pass
                case Components.Combatant.Status.MANUEVER | Components.Combatant.Status.ACT | Components.Combatant.Status.STANDBY:
                    in_range = False
                    if combatant.action and combatant.target in eid_lookup:
                        target = Components.Combatant[combatant.target]
                        distance = distances[i][eid_lookup[combatant.target]]
                        action = Resources.CombatAction[combatant.action]
                        if action:
                            in_range = distance.item() < action.range + (combatant.size + target.size)/2.0
                    if not in_range:
                        velocity = chosen_final[i][:2]*combatant.move_speed
                        combatant.body.velocity = tuple(velocity)
                    else:
                        combatant.body.velocity =(0,0)
                    combatant.forward = forward_final[i]

        self.world.step(event.dt)
        for i,(eid, combatant) in enumerate(combatants):
            combatant.pos = np.append(combatant.body.position, 0)

        return event.result

    @Systems.on(Events.SpawnCombatant, Systems.Priority.HIGHEST)
    async def onSpawnCombatant(self, event: Events.SpawnCombatant) -> Events.Result:
        theta = 2*np.pi*self.randomizer.random()
        distance = 500
        pos = np.array([
            (np.cos(theta)*distance).item()+500,
            (np.sin(theta)*distance).item()+500,
            0.
        ], dtype=np.float32)
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
            mannequin=event.mannequin,
            active_meshes=event.active_meshes
        )
        return event.result

    @Systems.on(Events.BattleBegin, Systems.Priority.DEFAULT)
    async def onBattleBegin(self, event: Events.BattleBegin) -> Event.Result:
        self.world = pymunk.Space()
        self.world_bound = pymunk.Body(mass=float('inf'), moment=float('inf'), body_type=pymunk.Body.STATIC)
        if event.seed is not None:
            self.randomizer.seed(event.seed)
        self.state = Battle.State.READY
        radius = 200.
        offset = radius/np.sqrt(2.).item()
        points = [
            (-offset, event.arena_size[1]+offset),
            (event.arena_size[0]+offset, event.arena_size[1]+offset),
            (event.arena_size[0]+offset, -offset),
            (-offset, -offset)
        ]
        shapes = []
        for i in range(4):
            shapes.append(pymunk.Segment(self.world_bound, points[i], points[(i+1)%4], radius=radius))
        self.world.add(self.world_bound, *shapes)


        return event.result

    @Systems.on(Events.BattleEnd, Systems.Priority.LOWEST)
    async def onBattleEnd(self, event: Events.BattleEnd) -> Event.Result:
        for eid, combatant in Components.Combatant.getAll():
            Components.Combatant.remove(eid)
        self.world = None
        return event.result

    @Systems.on(Events.CombatantReady, Systems.Priority.HIGHEST)
    async def onCombatantReady(self, event: Events.CombatantReady) -> Event.Result:

        return event.result

    @Systems.on(Events.PlayerCombatantCommand, Systems.Priority.LOWEST)
    async def onPlayerCombatantCommand(self, event: Events.PlayerCombatantCommand) -> Events.Result:
        combatant = Components.Combatant[event.eid]
        player_party = None
        players = Components.find([Components.Player, Components.Combatant])
        if players:
            player = Components.Combatant[players[0]]
            player_party = player.party_id

        if player_party == combatant.party_id:
            combatant.action = event.action
            combatant.target = event.target
            action = Resources.CombatAction[event.action]
            if action:
                combatant.posture = tuple(action.posture)
            self.state = Battle.State.READY
            self.camera_target = None
        else:
            pass #TODO: This is pretty serious. How is a non-party member getting player commands?
        return event.result

    @Systems.on(Events.CombatDamage, Systems.Priority.LOWEST)
    async def onCombatDamage(self, event: Events.CombatDamage) -> Events.Result:
        print(f"{event.eid} THWACKS {event.target} with GUSTO!")
        return event.result

    @Systems.on(Events.CombatActionComplete, Systems.Priority.LOWEST)
    async def onCombatActionComplete(self, event: Events.CombatActionComplete) -> Events.Result:
        combatant = Components.Combatant[event.eid]
        combatant.status = Components.Combatant.Status.MANUEVER
        combatant.progress = 0
        combatant.posture = combatant.default_posture
        combatant.action = None
        combatant.target = None
        return event.result

    @Systems.on(Events.AICombatantReady, Systems.Priority.LOWEST)
    async def onAICombatantReady(self, event: Events.AICombatantReady) -> Events.Result:
        combatant = Components.Combatant[event.eid]
        players = Components.find([Components.Player, Components.Combatant])
        player_party = 0
        player_id = 0
        if players:
            player = Components.Combatant[players[0]]
            player_party = player.party_id
            player_id = player.eid

        if player_party != combatant.party_id:
            combatant.action = "Strike"
            combatant.target = player_id
            combatant.status = Components.Combatant.Status.ACT
            action = Resources.CombatAction[combatant.action]
            if action:
                combatant.posture = tuple(action.posture)
        return event.result
