from __future__ import annotations
from cffi import FFI
from enum import Enum, auto as EnumAuto
import OpenGL.GL as GL
import sdl2 as SDL
import platform
import os
import pathlib
import ctypes
import json

import Systems, Events, Resources, Components

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
            return self._ffi.NULL  # TODO: deduce mimetype

        def charset(self, path):
            return self._ffi.NULL # TODO: extract charset

        def open(self, path) -> bytes:
            if path not in self._open_files:
                x = self.getPath(path)
                with Resources.file_system().open(self.getPath(path), "rb") as file:
                    data = file.read()
                    buffer = self._ffi.new("char[]", data)
                    handle = self._ffi.new_handle(path)
                    callback = self._ffi.callback("void(void*, void*)")(self.onDestroy)
                    self._open_files[path] = {
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
            return self._open_files[path]["ulBuffer"]

        def onDestroy(self, user_data, data):
            if user_data is not self._ffi.NULL:
                path = self._ffi.from_handle(user_data)
                if path in self._open_files:
                    del self._open_files[path]


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
                if handle in self._open_files:
                    del self._open_files[handle]


    def __init__(self, screen_dimensions: tuple[int, int], **kwargs):
        super().__init__(**kwargs)
        self._ffi = None
        self._lib = None
        self._lib_wc = None
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
        self._lib.ulUpdate(self.renderer) # Ensure this happens at LEAST ONCE before first render

        # Set and pin UL callbacks
        self._callbacks = self._callbacks | {
            "change_cursor": self._ffi.callback("void(void*,ULView,ULCursor)")(self.callbackChangeCursor),
            "window_ready": self._ffi.callback("void(void*,ULView,unsigned long long, bool, ULString)")(self.callbackWindowReady)
        }
        self._lib.ulViewSetChangeCursorCallback(self.view, self._callbacks["change_cursor"], self._ffi.NULL)
        self._lib.ulViewSetWindowObjectReadyCallback(self.view, self._callbacks["window_ready"], self._ffi.NULL)
        


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

        with Resources.file_system().open("interface/main.html") as file:
            buffer = file.read()
            u_str = self._lib.ulCreateString(buffer.encode("utf-8"))
            self._lib.ulViewLoadHTML(self.view, u_str)
            self._lib.ulDestroyString(u_str)

        return True

    def callJSFunc(self, func_name: str, data: dict = None) -> dict:
        result = None
        if not data:
            data = {}

        context = self._lib.ulViewLockJSContext(self.view)
        js_string = self._lib_wc.JSStringCreateWithUTF8CString(f"{func_name}(JSON.parse({json.dumps(json.dumps(data))}));".encode("utf-8"))
        js_result = self._lib_wc.JSEvaluateScript(context, js_string, self._ffi.NULL, self._ffi.NULL, 0, self._ffi.NULL)
        if self._lib_wc.JSValueIsString(context, js_result):
            js_copy = self._lib_wc.JSValueToStringCopy(context, js_result, self._ffi.NULL)
            js_strlen = self._lib_wc.JSStringGetMaximumUTF8CStringSize(js_copy)
            js_buffer = self._ffi.new("char[]", js_strlen)
            self._lib_wc.JSStringGetUTF8CString(js_copy, js_buffer, js_strlen)
            result = self._ffi.string(js_buffer).decode("utf-8")
            self._lib_wc.JSStringRelease(js_copy)
        self._lib.JSStringRelease(js_string)
        self._lib.ulViewUnlockJSContext(self.view)

        return json.loads(result) if result else None

    def jsHelloWorld(self, ctx, func, this, argc, args, exception):
        print("Javascript says Hello World!")
        return self._ffi.NULL

    def callbackWindowReady(self, user_data, caller, frame_id, is_main_frame, url):
        context = self._lib.ulViewLockJSContext(self.view)
        def makeJSFunction(js_name, cb_name, cb_func):
            self._callbacks[cb_name] = self._ffi.callback("JSValueRef(JSContextRef, JSObjectRef, JSObjectRef, size_t, JSValueRef[], JSValueRefPtr)", cb_func)
            js_global = self._lib_wc.JSContextGetGlobalObject(context)
            js_func_name = self._lib_wc.JSStringCreateWithUTF8CString(js_name.encode("utf-8"))
            js_func_obj = self._lib_wc.JSObjectMakeFunctionWithCallback(context, js_func_name, self._callbacks[cb_name])
            self._lib_wc.JSObjectSetProperty(context, js_global, js_func_name, js_func_obj, 0, self._ffi.NULL)
            self._lib_wc.JSStringRelease(js_func_name)
        
        makeJSFunction("hello_world", "hello_world", self.jsHelloWorld)
        self._lib.ulViewUnlockJSContext(self.view)

    def callbackChangeCursor(self, user_data, caller, cursor): # TODO: actually change cursor, this is test/placeholder
        if self.cursor_state != cursor:
            self.cursor_state = cursor
            match cursor:
                case self._lib.kCursor_Alias:
                    print("!")
                case _:
                    print("?")

    @Systems.on(Events.Logic, Systems.Priority.LOWEST)
    async def onLogicStep(self, event: Events.Logic) -> bool:
        self._lib.ulUpdate(self.renderer)
        return False

    @Systems.on(Events.Render, Systems.Priority.LOWEST)
    async def onRenderStep(self, event: Events.Render) -> bool:
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

        #System.immediateEvent(PostRender())
        SDL.SDL_GL_SwapWindow(event.window)


        return False

    @Systems.on(Events.FromSDL, Systems.Priority.HIGHEST)
    async def onSDLEvent(self, event: Events.FromSDL) -> bool:
        ul_event = None
        match event.sdl_event.type:
            case SDL.SDL_MOUSEMOTION:
                ul_event = self._lib.ulCreateMouseEvent(
                    self._lib.kMouseEventType_MouseMoved,
                    event.sdl_event.motion.x,
                    event.sdl_event.motion.y,
                    self._lib.kMouseEventType_MouseMoved
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

                ul_event = self._lib.ulCreateMouseEvent(
                    evt_type,
                    event.sdl_event.motion.x,
                    event.sdl_event.motion.y,
                    button
                )
        if ul_event:
            self._lib.ulViewFireMouseEvent(self.view, ul_event)
            self._lib.ulDestroyMouseEvent(ul_event)
        return False