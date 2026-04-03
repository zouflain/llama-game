from __future__ import annotations
from cffi import FFI
from enum import Enum, auto as EnumAuto
import numpy as np
import OpenGL.GL as GL
import sdl2 as SDL
import platform
import os
import pathlib
import ctypes
import json

import Systems, Events, Resources, Components

class UISnapMouse(Events.Event):
    def __init__(self, center: dict = None, **kwargs):
        self.center: dict = center if center else {"x": 0, "y": 0}

class UIEvent(Events.Event):
    def __init__(self, name: str, **kwargs):
        super().__init__(**kwargs)
        self.name: str = name
        self.data: dict = kwargs

class UserInterface(Systems.System):

    class ShaderConstants(int, Enum):
        COLOR = 0
        UI = 1
        OUTPUT = 2

    class FSWrapper:
        def __init__(self, ffi, lib):
            self._ffi = ffi
            self._lib = lib
            self._pins = [
                self._ffi.callback("bool(void*)")(self.exists),
                self._ffi.callback("void*(void*)")(self.mimetype),
                self._ffi.callback("void*(void*)")(self.charset),
                self._ffi.callback("void*(void*)")(self.open)
            ]
            self._pinned_str = {
                "mimetype": {},
                "charset": {}
            }

            self._struct = self._ffi.new("ULFileSystem*")
            self._struct.file_exists = self._pins[0]
            self._struct.get_file_mime_type = self._pins[1]
            self._struct.get_file_charset = self._pins[2]
            self._struct.open_file = self._pins[3]

            self._open_files = {}

        @property
        def struct(self):
            return self._struct

        def getPath(self, path) -> str:
            return f"""interface/{self._ffi.string(self._lib.ulStringGetData(path)).decode("utf-8")}"""

        def exists(self, path) -> bool:
            return Resources.file_system().exists(self.getPath(path))

        def mimetype(self, path) -> str:
            py_path = self.getPath(path)
            mime = "application/octet-stream"
            match py_path.split(".")[-1]:
                case "html" | "htm":
                    mime = "text/html"
                case "js":
                    mime = "text/javascript"
                case "css":
                    mime = "text/css"
            if py_path not in self._pinned_str["mimetype"]:
                ul_mimetype = self._lib.ulCreateString(mime.encode("utf-8"))
                self._pinned_str["mimetype"][py_path] = ul_mimetype
            return self._pinned_str["mimetype"][py_path]

        def charset(self, path):
            py_path = self.getPath(path)
            if py_path not in self._pinned_str["charset"]:
                ul_charset = self._lib.ulCreateString("utf-8".encode("utf-8"))
                self._pinned_str["charset"][py_path] = ul_charset
            return self._pinned_str["charset"][py_path]

        def open(self, path) -> bytes:
            py_path = self.getPath(path)
            if py_path not in self._open_files:
                with Resources.file_system().open(py_path, "rb") as file:
                    data = file.read()
                    buffer = self._ffi.from_buffer(data)
                    #buffer = self._ffi.new("char[]", data)
                    handle = self._ffi.new_handle(path)
                    callback = self._ffi.callback("void(void*, void*)")(self.onDestroy)
                    self._open_files[py_path] = {
                        "buffer": buffer,
                        "handle": handle,
                        "callback": callback,
                        "ulBuffer": self._lib.ulCreateBuffer(
                            buffer,
                            len(buffer),
                            handle,
                            callback
                        )
                    }
            return self._open_files[py_path]["ulBuffer"]

        def onDestroy(self, user_data, data):
            if user_data is not self._ffi.NULL:
                path = self._ffi.from_handle(user_data)
                py_path = self.getPath(path)
                if py_path in self._open_files:
                    del self._open_files[py_path]


    class FontWrapper:
        def __init__(self, ffi, lib):
            self._ffi = ffi
            self._lib = lib
            self._pins = [
                self._ffi.callback("void*()")(self.getFallback),
                self._ffi.callback("void*(void*, int, bool)")(self.getFallbackForChars),
                self._ffi.callback("void*(void*, int, bool)")(self.load),
            ]
            self._struct = self._ffi.new("ULFontLoader*")
            self._struct.get_fallback_font = self._pins[0]
            self._struct.get_fallback_font_for_characters = self._pins[1]
            self._struct.load = self._pins[2]
            self._open_files = {}
        
        @property
        def struct(self):
            return self._struct

        def getPath(self, path):
            return f"""interface/fonts/{self._ffi.string(self._lib.ulStringGetData(path)).decode("utf-8")}.ttf"""

        def getFallback(self):
            return self._lib.ulCreateString(self._ffi.new("char[]", b"fallback"))

        def getFallbackForChars(self, characters, weight, italic):
            return self._lib.ulCreateString(self._ffi.new("char[]", b"fallback"))

        def load(self, family, weight, italic):
            path = self.getPath(family)
            try:
                if not path in self._open_files:
                    with Resources.file_system().open(path, "rb") as file:
                        data = file.read()
                        buffer = self._ffi.new("char[]", data)
                        handle = self._ffi.new_handle(path)
                        callback = self._ffi.callback("void(void*, void*)")(self.onDestroy) # TODO: investigate EXACTLY when this will callback. Is it done with the font_file by then?
                        ul_buffer = self._lib.ulCreateBuffer(buffer, len(buffer), handle, callback)
                        font_file = self._lib.ulFontFileCreateFromBuffer(ul_buffer)
                        self._open_files[path] = {
                            "buffer": buffer,
                            "handle": handle,
                            "callback": callback,
                            "ul_buffer": ul_buffer,
                            "font_file": font_file
                        }
                return self._open_files[path]["font_file"]
            except Exception as err:
                # TODO: properly log this
                return self._ffi.NULL

        def onDestroy(self, user_data, data):
            if user_data != self._ffi.NULL:
                handle = self._ffi.from_handle(user_data)
                path = self.getPath(handle)
                if path in self._open_files:
                    del self._open_files[path]


    def __init__(self, screen_dimensions: tuple[int, int], **kwargs):
        super().__init__(**kwargs)
        self._ffi = None
        self._lib = None
        self._lib_wc = None
        self.dom_ready = False
        self.screen_dimensions: tuple[int, int] = screen_dimensions
        self.gl_texture: int = 0
        self._callbacks = {}
        self.cursor_state = 0

        if not self._ffi:
            self._ffi = FFI()
            self._ffi.cdef(pathlib.Path("src/Include/ultralight.h").read_text())
            self._ffi.cdef(pathlib.Path("src/Include/webcore.h").read_text())

            match platform.system():
                case "Linux":
                    self._lib = self._ffi.dlopen("libUltralight.so")
                    self._lib_wc = self._ffi.dlopen("libWebCore.so")
                case _:
                    raise Exception("Unrecognized operating system")
    
    async def boot(self) -> bool:
        self._font_wrapper = UserInterface.FontWrapper(self._ffi, self._lib)
        self._fs_wrapper = UserInterface.FSWrapper(self._ffi, self._lib)
        self._lib.ulPlatformSetFileSystem(self._fs_wrapper.struct[0])
        self._lib.ulPlatformSetFontLoader(self._font_wrapper.struct[0])

        self._config = self._lib.ulCreateConfig()
        self.renderer = self._lib.ulCreateRenderer(self._config)

        view_config = self._lib.ulCreateViewConfig()
        self._lib.ulViewConfigSetIsTransparent(view_config, True)
        self.view = self._lib.ulCreateView(self.renderer, self.screen_dimensions[0], self.screen_dimensions[1], view_config, self._ffi.NULL)
        self._lib.ulDestroyViewConfig(view_config)
        self._lib.ulUpdate(self.renderer)

        # Set and pin UL callbacks
        self._callbacks = self._callbacks | {
            "change_cursor": self._ffi.callback("void(void*,ULView,ULCursor)")(self.callbackChangeCursor),
            "window_ready": self._ffi.callback("void(void*,ULView,unsigned long long, bool, ULString)")(self.callbackWindowReady),
            "console_log": self._ffi.callback("void(void*, ULView, ULMessageSource, ULMessageLevel, ULString, unsigned int, unsigned int, ULString)")(self.callbackConsoleLog),
            "dom_ready": self._ffi.callback("void(void*, ULView, unsigned long long, bool, ULString)")(self.callbackDomReady)
        }
        self._lib.ulViewSetChangeCursorCallback(self.view, self._callbacks["change_cursor"], self._ffi.NULL)
        self._lib.ulViewSetWindowObjectReadyCallback(self.view, self._callbacks["window_ready"], self._ffi.NULL)
        self._lib.ulViewSetAddConsoleMessageCallback(self.view, self._callbacks["console_log"], self._ffi.NULL)
        self._lib.ulViewSetDOMReadyCallback(self.view, self._callbacks["dom_ready"], self._ffi.NULL)
       

        # Regular old opengl
        self.gl_texture = GL.glGenTextures(1)
        GL.glBindTexture(GL.GL_TEXTURE_2D, self.gl_texture)
        GL.glPixelStorei(GL.GL_UNPACK_ALIGNMENT, 1)
        GL.glTexImage2D(GL.GL_TEXTURE_2D, 0, GL.GL_RGBA8, self.screen_dimensions[0], self.screen_dimensions[1], 0, GL.GL_BGRA, GL.GL_UNSIGNED_BYTE, None)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, GL.GL_LINEAR)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, GL.GL_LINEAR)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_S, GL.GL_CLAMP_TO_EDGE)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_T, GL.GL_CLAMP_TO_EDGE)

        self.ui_shader = await Resources.Shader.generate(name="ui_shader", permanent=True, fname="renderui.comp")

        u_str = self._lib.ulCreateString("file://interface/main.html".encode("utf-8"))
        self._lib.ulViewLoadURL(self.view, u_str)
        self._lib.ulDestroyString(u_str) 
        while not self.dom_ready:
            self._lib.ulUpdate(self.renderer) # Ensure this happens at LEAST ONCE before first render
            self._lib.ulRender(self.renderer) # Then render, so javascript can be executed

        return True

    def callJSFunc(self, func_name: str, data: dict = None) -> dict:
        result = None
        if not data:
            data = {}

        context = self._lib.ulViewLockJSContext(self.view)
        #js_string = self._lib_wc.JSStringCreateWithUTF8CString(f"{func_name}(JSON.parse({json.dumps(json.dumps(data))}));".encode("utf-8"))
        js_string = self._lib_wc.JSStringCreateWithUTF8CString(f"{func_name}({json.dumps(data)});".encode("utf-8"))
        js_result = self._lib_wc.JSEvaluateScript(context, js_string, self._ffi.NULL, self._ffi.NULL, 0, self._ffi.NULL)
        result = self.helperJSExtractString(js_result, context)
        self._lib.JSStringRelease(js_string)
        self._lib.ulViewUnlockJSContext(self.view)

        return json.loads(result) if result else None

    def jsTriggerEvent(self, ctx, func, this, argc, args, exception):
        if argc > 1 and self._lib_wc.JSValueIsString(ctx, args[0]) and self._lib_wc.JSValueIsObject(ctx, args[1]):
            event_name = self.helperJSExtractString(args[0], ctx)
            data = self.helperJSExtractJSON(args[1], ctx)
            event_type = Events.get(event_name)
            if event_type:
                Systems.raiseEvent(event_type(**data))
        return self._ffi.NULL

    def helperJSExtractJSON(self, ref, context) -> dict:
        js_data_str = self._lib_wc.JSValueCreateJSONString(context, ref, 0, self._ffi.NULL)
        js_strlen = self._lib_wc.JSStringGetMaximumUTF8CStringSize(js_data_str)
        js_buffer = self._ffi.new("char[]", js_strlen)
        self._lib_wc.JSStringGetUTF8CString(js_data_str, js_buffer, js_strlen)
        data_str = self._ffi.string(js_buffer).decode("utf-8")
        self._lib_wc.JSStringRelease(js_data_str)
        return json.loads(data_str)

    def helperJSExtractString(self, ref, context) -> str:
        result = None
        if self._lib_wc.JSValueIsString(context, ref):
            js_copy = self._lib_wc.JSValueToStringCopy(context, ref, self._ffi.NULL)
            if js_copy:
                js_strlen = self._lib_wc.JSStringGetMaximumUTF8CStringSize(js_copy)
                js_buffer = self._ffi.new("char[]", js_strlen)
                self._lib_wc.JSStringGetUTF8CString(js_copy, js_buffer, js_strlen)
                result = self._ffi.string(js_buffer).decode("utf-8")
                self._lib_wc.JSStringRelease(js_copy)
        return result

    def callbackConsoleLog(self, user_data, caller, source, level, message, line_number, column_number, source_id):
        context = self._lib.ulViewLockJSContext(caller)
        py_source = self._ffi.string(self._lib.ulStringGetData(source_id)).decode("utf-8")
        py_message = self._ffi.string(self._lib.ulStringGetData(message)).decode("utf-8")
        print(f"\033[36m[{py_source} line: {line_number} col: {column_number}: \033[37m{py_message}")
        self._lib.ulViewUnlockJSContext(caller)

    def callbackDomReady(self, user_data, caller, frame_id, is_main_frame, url):
        self.dom_ready = True

    def callbackWindowReady(self, user_data, caller, frame_id, is_main_frame, url):
        context = self._lib.ulViewLockJSContext(self.view)
        def makeJSFunction(js_name, cb_name, cb_func):
            self._callbacks[cb_name] = self._ffi.callback("JSValueRef(JSContextRef, JSObjectRef, JSObjectRef, size_t, JSValueRef[], JSValueRefPtr)", cb_func)
            js_global = self._lib_wc.JSContextGetGlobalObject(context)
            js_func_name = self._lib_wc.JSStringCreateWithUTF8CString(js_name.encode("utf-8"))
            js_func_obj = self._lib_wc.JSObjectMakeFunctionWithCallback(context, js_func_name, self._callbacks[cb_name])
            self._lib_wc.JSObjectSetProperty(context, js_global, js_func_name, js_func_obj, 0, self._ffi.NULL)
            self._lib_wc.JSStringRelease(js_func_name)
        
        makeJSFunction("TriggerGameEvent", "TriggerGameEvent", self.jsTriggerEvent)
        self._lib.ulViewUnlockJSContext(self.view)

    def callbackChangeCursor(self, user_data, caller, cursor): # TODO: actually change cursor, this is test/placeholder
        if self.cursor_state != cursor:
            self.cursor_state = cursor
            match cursor:
                case self._lib.kCursor_Alias:
                    print("!")
                case _:
                    print("?")

    @Systems.on(Events.Logic, Systems.Priority.HIGHEST)
    async def onLogicStep(self, event: Events.Logic) -> Events.Result:
        self._lib.ulUpdate(self.renderer)
        return event.result

    @Systems.on(Events.Render, Systems.Priority.LOWEST)
    async def onRenderStep(self, event: Events.Render) -> Events.Result:
        self._lib.ulRender(self.renderer)
        surface = self._lib.ulViewGetSurface(self.view)
        bounds = self._lib.ulSurfaceGetDirtyBounds(surface)
        if bounds.right > bounds.left and bounds.bottom > bounds.top:
            bitmap = self._lib.ulBitmapSurfaceGetBitmap(surface)
            pixels_ptr = self._lib.ulBitmapLockPixels(bitmap)
            size = self._lib.ulBitmapGetSize(bitmap)
            c_ptr = ctypes.c_void_p(int(self._ffi.cast("uintptr_t", pixels_ptr)))
            GL.glTextureSubImage2D(self.gl_texture, 0, 0, 0, self.screen_dimensions[0], self.screen_dimensions[1], GL.GL_BGRA, GL.GL_UNSIGNED_BYTE, c_ptr)

            self._lib.ulBitmapUnlockPixels(bitmap)
            self._lib.ulSurfaceClearDirtyBounds(surface)

        with Resources.Framebuffer.Binding(event.framebuffer, event.resolution):
            with Resources.Shader.Binding(self.ui_shader) as ui_prog:
                GL.glMemoryBarrier(GL.GL_SHADER_IMAGE_ACCESS_BARRIER_BIT)
                GL.glBindImageTexture(UserInterface.ShaderConstants.COLOR, event.framebuffer.textures[GL.GL_COLOR_ATTACHMENT0], 0, GL.GL_FALSE, 0, GL.GL_READ_ONLY, GL.GL_RGBA32F)
                GL.glBindImageTexture(UserInterface.ShaderConstants.UI, self.gl_texture, 0, GL.GL_FALSE, 0, GL.GL_READ_ONLY, GL.GL_RGBA8)
                GL.glBindImageTexture(UserInterface.ShaderConstants.OUTPUT, event.framebuffer.textures[GL.GL_COLOR_ATTACHMENT4], 0, GL.GL_FALSE, 0, GL.GL_WRITE_ONLY, GL.GL_RGBA32F)

                GL.glDispatchCompute(int(event.framebuffer.resolution[0]/32)+1, int(event.framebuffer.resolution[1]/32)+1, 1, 0)
                GL.glMemoryBarrier(GL.GL_SHADER_IMAGE_ACCESS_BARRIER_BIT)

        GL.glNamedFramebufferReadBuffer(event.framebuffer.fbo, GL.GL_COLOR_ATTACHMENT4)
        GL.glBlitNamedFramebuffer(event.framebuffer.fbo, 0, 0, 0, event.render_size[0], event.render_size[1], 0, 0, event.resolution[0], event.resolution[1], GL.GL_COLOR_BUFFER_BIT, GL.GL_NEAREST)

        SDL.SDL_GL_SwapWindow(event.window)


        return event.result

    @Systems.on(Events.FromSDL, Systems.Priority.HIGHEST)
    async def onSDLEvent(self, event: Events.FromSDL) -> Events.Result:
        events = []
        ul_str_empty = self._lib.ulCreateString("".encode("utf-8"))
        strings = [ul_str_empty]
        match event.sdl_event.type:
            case SDL.SDL_MOUSEMOTION:
                events.append(
                    (
                        "mouse",
                        self._lib.ulCreateMouseEvent(
                            self._lib.kMouseEventType_MouseMoved,
                            event.sdl_event.motion.x,
                            event.sdl_event.motion.y,
                            self._lib.kMouseEventType_MouseMoved
                        )
                    )
                )
            case SDL.SDL_MOUSEBUTTONDOWN | SDL.SDL_MOUSEBUTTONUP:
                evt_type = self._lib.kMouseEventType_MouseDown
                if event.sdl_event.type == SDL.SDL_MOUSEBUTTONUP:
                    evt_type = self._lib.kMouseEventType_MouseUp

                button = self._lib.kMouseButton_None
                match event.sdl_event.button.button:
                    case SDL.SDL_BUTTON_LEFT:
                        button = self._lib.kMouseButton_Left
                    case SDL.SDL_BUTTON_MIDDLE:
                        button = self._lib.kMouseButton_Middle
                    case SDL.SDL_BUTTON_RIGHT:
                        button = self._lib.kMouseButton_Right

                events.append(
                    (
                        "mouse",
                        self._lib.ulCreateMouseEvent(
                            evt_type,
                            event.sdl_event.motion.x,
                            event.sdl_event.motion.y,
                            button
                        )
                    )
                )  
        '''    
            case SDL.SDL_CONTROLLERBUTTONDOWN | SDL.SDL_CONTROLLERBUTTONUP:
                down = event.sdl_event.type == SDL.SDL_CONTROLLERBUTTONDOWN
                match event.sdl_event.cbutton.button:
                    case SDL.SDL_CONTROLLER_BUTTON_RIGHTSHOULDER:
                        events.append(
                            (
                                "key",
                                self._lib.ulCreateKeyEvent(
                                    self._lib.kKeyEventType_RawKeyDown if down else self._lib.kKeyEventType_KeyUp,
                                    0,
                                    self._lib.GK_TAB,
                                    0,
                                    ul_str_empty,
                                    ul_str_empty,
                                    False,
                                    False,
                                    False
                                )
                            )
                        )
                    case SDL.SDL_CONTROLLER_BUTTON_A:
                        if down:
                            ul_key_str = self._lib.ulCreateString("\r".encode("utf-8"))
                            strings.append(ul_key_str)
                            events.append(
                                (
                                    "key",
                                    self._lib.ulCreateKeyEvent(
                                        self._lib.kKeyEventType_RawKeyDown,
                                        0,
                                        self._lib.GK_RETURN,
                                        0,
                                        ul_str_empty,
                                        ul_str_empty,
                                        False,
                                        False,
                                        False
                                    )
                                )
                            )
                            events.append(
                                (
                                    "key",
                                    self._lib.ulCreateKeyEvent(
                                        self._lib.kKeyEventType_Char,
                                        0,
                                        self._lib.GK_RETURN,
                                        0,
                                        ul_key_str,
                                        ul_key_str,
                                        False,
                                        False,
                                        False
                                    )
                                )
                            )
                        else:
                            events.append(
                                (
                                    "key",
                                    self._lib.ulCreateKeyEvent(
                                        self._lib.kKeyEventType_KeyUp,
                                        0,
                                        self._lib.GK_RETURN,
                                        0,
                                        ul_str_empty,
                                        ul_str_empty,
                                        False,
                                        False,
                                        False
                                    )
                                )
                            )
                    case SDL.SDL_CONTROLLER_BUTTON_B:
                        events.append(
                            (
                                "key",
                                self._lib.ulCreateKeyEvent(
                                    self._lib.kKeyEventType_RawKeyDown if down else self._lib.kKeyEventType_KeyUp,
                                    0,
                                    self._lib.GK_ESCAPE,
                                    0,
                                    ul_str_empty,
                                    ul_str_empty,
                                    False,
                                    False,
                                    False
                                )
                            )
                        )
                    case SDL.SDL_CONTROLLER_BUTTON_LEFTSHOULDER:
                        events.append(
                            (
                                "key",
                                self._lib.ulCreateKeyEvent(
                                    self._lib.kKeyEventType_RawKeyDown if down else self._lib.kKeyEventType_KeyUp,
                                    self._lib.kMod_ShiftKey,
                                    self._lib.GK_TAB,
                                    0,
                                    ul_str_empty,
                                    ul_str_empty,
                                    False,
                                    False,
                                    False
                                )
                            )
                        )
        '''
        for ev_type, evt in events:
            match ev_type:
                case "mouse":
                    self._lib.ulViewFireMouseEvent(self.view, evt)
                    self._lib.ulDestroyMouseEvent(evt)
                case "key":
                    self._lib.ulViewFireKeyEvent(self.view, evt)
                    self._lib.ulDestroyKeyEvent(evt)
        for string in strings:
            self._lib.ulDestroyString(string)

        return event.result

    @Systems.on(Events.GamepadChange, Systems.Priority.LOWEST)
    async def onGamepadChange(self, event: Events.GamepadChange) -> Events.Result:
        self.callJSFunc("window.GameEventBus.gamepad", event.changes)
        return event.result

    async def tickHelper(self, view, projection, resolution) -> Events.Result:
        entities = {}
        for eid, combatant in Components.Combatant.getAll():
            clip_space =  np.array(projection, dtype=np.float32).reshape(4,4) @ np.array(view, dtype=np.float32).reshape(4,4) @ np.append(combatant.pos, 1)
            norm_device = clip_space[:3]/clip_space[3]
            screen_pos = (norm_device[:2] + 1.)/2.
            entities[eid] = {
                "status": combatant.status,
                "progress": combatant.progress,
                "pos": {
                    "x": screen_pos[0]*resolution[0],
                    "y": screen_pos[1]*resolution[1]
                },
                "posture": combatant.posture,
                "target": combatant.target,
                "party": combatant.party_id
            }
        return (await Systems.immediateEvent(Events.UIEvent("CombatUpdate", entities=entities))).result

    @Systems.on(Events.CombatGUITick, Systems.Priority.DEFAULT)
    async def onCombatGUITick(self, event: Events.CombatGUITick) -> Events.Result:
        await self.tickHelper(event.view, event.projection, event.resolution)
        return event.result

    @Systems.on(Events.CombatTick, Systems.Priority.DEFAULT)
    async def onCombatTick(self, event: Events.CombatTick) -> Events.Result:
        await self.tickHelper(event.view, event.projection, event.last_resolution)
        return event.result

    @Systems.on(Events.BattleBegin, Systems.Priority.LOWEST)
    async def onBattleBegin(self, event: Events.BattleBegin) -> Events.Result:
        init_data = {
            "postures": {
                str(entry).split(".")[-1]: int(entry) for entry in Components.Combatant.Posture
            }
        }
        await Systems.immediateEvent(Events.UIEvent("CombatInit", **init_data))
        return event.result

    @Systems.on(Events.PlayerCombatantReady, Systems.Priority.LOWEST)
    async def onPlayerReady(self, event: Events.PlayerCombatantReady) -> Events.Result:
        await Systems.immediateEvent(Events.UIEvent("CombatReadyEntity", eid=event.eid))
        return event.result

    @Systems.on(Events.UIEvent, Systems.Priority.LOWEST)
    async def onUIEvent(self, event: Events.UIEvent) -> Events.Result:
        result = None

        context = self._lib.ulViewLockJSContext(self.view)
        js_string = self._lib_wc.JSStringCreateWithUTF8CString(f"window.GameEventBus.emit('{event.name}', {json.dumps(event.data)});".encode("utf-8"))
        js_result = self._lib_wc.JSEvaluateScript(context, js_string, self._ffi.NULL, self._ffi.NULL, 0, self._ffi.NULL)
        if js_result == self._ffi.NULL:
            exception = self._ffi.new("JSValueRefPtr")
            js_error = self.helperJSExtractString(exception[0], context)
            print(f"ERROR: {js_error}")
        result = self.helperJSExtractString(js_result, context)
        self._lib.JSStringRelease(js_string)
        self._lib.ulViewUnlockJSContext(self.view)

        return event.result

    @Systems.on(Events.UISnapMouse, Systems.Priority.LOWEST)
    async def onSnapMouse(self, event: Events.UISnapMouse) -> Events.Result:
        SDL.SDL_WarpMouseInWindow(None, int(event.center.get("x", 0)), int(event.center.get("y", 0)))
        return event.result