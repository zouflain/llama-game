from __future__ import annotations
from .system import System
from cffi import FFI
from enum import Enum, auto as EnumAuto
import OpenGL.GL as GL
import sdl2 as SDL
import platform
import os
import ctypes

import Events, Resources, Components

class UserInterface(System):

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
        self.screen_dimensions: tuple[int, int] = screen_dimensions
        self.gl_texture: int = 0

        if not self._ffi:
            self._ffi = FFI()
            self._ffi.cdef("""
                // Strings
                typedef void* ULString;
                ULString ulCreateString(const char* str);

                void ulDestroyString(ULString* string);
                char* ulStringGetData(ULString str);

                // Config
                typedef void* ULConfig;

                ULConfig ulCreateConfig();

                // File System
                typedef struct {
                    bool (*file_exists) (ULString path);
                    void* (*get_file_mime_type) (ULString path);
                    void* (*get_file_charset) (ULString path);
                    void* (*open_file) (ULString path);
                }ULFileSystem;
                void ulPlatformSetFileSystem(ULFileSystem file_system);

                // Renderer
                typedef void* ULRenderer;

                ULRenderer ulCreateRenderer(ULConfig config);
                void ulUpdate(ULRenderer renderer);
                void ulRender(ULRenderer renderer);

                //Buffer
                typedef void* ULBuffer;

                ULBuffer ulCreateBuffer(void* data, size_t size, void* user_data, void* destruction_callback);

                //Fonts
                typedef struct {
                    void* (*get_fallback_font)();
                    void* (*get_fallback_font_for_characters)(ULString characters, int weight, bool italic);
                    void* (*load)(ULString family, int weight, bool italic);
                }ULFontLoader;
                typedef void* ULFontFile;

                ULFontFile ulFontFileCreateFromBuffer(ULBuffer buffer);
                void ulPlatformSetFontLoader(ULFontLoader font_loader);

                //view
                typedef void* ULViewConfig;
                typedef void* ULSession;
                typedef void* ULView;

                ULViewConfig ulCreateViewConfig();
                void ulDestroyViewConfig(ULViewConfig config);
                ULView ulCreateView(ULRenderer renderer, unsigned int width, unsigned int height, ULViewConfig view_config, ULSession session);
                void ulViewConfigSetIsTransparent(ULViewConfig config, bool is_transparent);

                //Surfaces
                typedef void* ULSurface;
                typedef struct {
                    int left;
                    int top;
                    int right;
                    int bottom;
                } ULIntRect;

                ULSurface ulViewGetSurface(ULView view);
                ULIntRect ulSurfaceGetDirtyBounds(ULSurface surface);
                void ulSurfaceClearDirtyBounds(ULSurface surface);

                //Bitmaps
                typedef void* ULBitmap;

                unsigned int ulBitmapGetWidth(ULBitmap bitmap);
                unsigned int ulBitmapGetHeight(ULBitmap bitmap);
                unsigned int ulBitmapGetRowBytes(ULBitmap bitmap);
                ULBitmap ulBitmapSurfaceGetBitmap(ULSurface surface);
                void* ulBitmapLockPixels(ULBitmap bitmap);
                void ulBitmapUnlockPixels(ULBitmap bitmap);
                size_t ulBitmapGetSize(ULBitmap bitmap);
                
                //HTML
                void ulViewLoadHTML(ULView view, ULString html_string);

                //Events
                typedef enum {
                    kKeyEventType_KeyDown,
                    kKeyEventType_KeyUp,
                    kKeyEventType_RawKeyDown,
                    kKeyEventType_Char,
                } ULKeyEventType;
                typedef enum {
                    kMouseEventType_MouseMoved,
                    kMouseEventType_MouseDown,
                    kMouseEventType_MouseUp,
                } ULMouseEventType;
                typedef enum {
                    kMouseButton_None = 0,
                    kMouseButton_Left,
                    kMouseButton_Middle,
                    kMouseButton_Right,
                } ULMouseButton;
                typedef enum {
                    kScrollEventType_ScrollByPixel,
                    kScrollEventType_ScrollByPage,
                } ULScrollEventType;
                typedef void* ULMouseEvent;

                ULMouseEvent ulCreateMouseEvent(ULMouseEventType type, int x, int y, ULMouseButton button);
                void ulMouseEventSetType(ULMouseEvent evt, ULMouseEventType type);
                void ulMouseEventSetX(ULMouseEvent evt, int x);
                void ulMouseEventSetY(ULMouseEvent evt, int y);
                void ulMouseEventSetButton(ULMouseEvent evt, ULMouseButton button);
                void ulViewFireMouseEvent(ULView view, ULMouseEvent evt);
                void ulDestroyMouseEvent(ULMouseEvent evt);
            """)
            match platform.system():
                case "Linux":
                    self._lib = self._ffi.dlopen("libUltralight.so")
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

        '''
        self.event_prefabs = {
            "mouse": self._lib.ulCreateMouseEvent(self._lib.kMouseEventType_MouseMoved, 0, 0, self._lib.kMouseButton_None)
        }
        '''


        #self.framebuffer = await Resources.Framebuffer.allocate("battle_buffer", False, render_size, 5)

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

    @System.on(Events.Logic, System.Priority.LOWEST)
    async def onLogicStep(self, event: Events.Logic) -> bool:
        self._lib.ulUpdate(self.renderer)
        return False

    @System.on(Events.Render, System.Priority.LOWEST)
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

    @System.on(Events.FromSDL, System.Priority.HIGHEST)
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
                ul_event = None
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