from __future__ import annotations
from .system import System
from cffi import FFI
import platform
import os

import Events, Resources, Components

class UserInterface(System):

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
            return self._ffi.string(self._lib.ulStringGetData(path)).decode("utf-8")

        def exists(self, path) -> bool:
            return Resources.file_system().exists(self.getPath(path))

        def mimetype(self, path) -> str:
            return self._ffi.NULL  # TODO: deduce mimetype

        def charset(self, path):
            return self._ffi.NULL # TODO: extract charset

        def open(self, path) -> bytes:
            if path not in self._open_files:
                with Resources.file_system().open(self.getPath(path), "rb") as file:
                    data = file.read()
                    buffer = self._ffi.new("char[]", data) # TODO: plug memory leak!
                    self._open_files[path] = {
                        "buffer": buffer,
                        "ulBuffer": self._lib.ulCreateBuffer(buffer, len(buffer), self._ffi.NULL, self._ffi.NULL)
                    }
            return self._open_files[path]["ulBuffer"]


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
        
        @property
        def struct(self):
            return self._struct

        def getFallback(self):
            return self._ffi.NULL

        def getFallbackForChars(self, characters, weight, italic):
            return self._ffi.NULL

        def load(self, family, weight, italic):
            return self._ffi.NULL


    def __init__(self, screen_dimensions: tuple[int, int], **kwargs):
        super().__init__(**kwargs)
        self._ffi = None
        self._lib = None

        if not self._ffi:
            self._ffi = FFI()
            self._ffi.cdef("""
                typedef void* ULString;

                const char* ulStringGetData(ULString str);

                typedef void* ULConfig;
                ULConfig ulCreateConfig();


                typedef struct {
                    bool (*file_exists) (ULString path);
                    void* (*get_file_mime_type) (ULString path);
                    void* (*get_file_charset) (ULString path);
                    void* (*open_file) (ULString path);
                }ULFileSystem;
                void ulPlatformSetFileSystem(ULFileSystem file_system);


                typedef struct {
                    void* (*get_fallback_font)();
                    void* (*get_fallback_font_for_characters)(ULString characters, int weight, bool italic);
                    void* (*load)(ULString family, int weight, bool italic);
                }ULFontLoader;
                void ulPlatformSetFontLoader(ULFontLoader font_loader);

                typedef void* ULRenderer;
                ULRenderer ulCreateRenderer(ULConfig config);

                //Buffer
                typedef void* ULBuffer;
                ULBuffer ulCreateBuffer(void* data, size_t size, void* destruction_callback, void* user_data);

                //view
                typedef void* ULViewConfig;
                typedef void* ULSession;
                typedef void* ULView;

                ULViewConfig ulCreateViewConfig();
                void ulDestroyViewConfig(ULViewConfig config);
                ULView ulCreateView(ULRenderer renderer, unsigned int width, unsigned int height, ULViewConfig view_config, ULSession session);

                //not yet used
                void ulViewLoadHTML(ULView view, ULString html_string);
                void ulUpdate(ULRenderer renderer);
                void ulRender(ULRenderer renderer);
            """)
            match platform.system():
                case "Linux":
                    self._lib = self._ffi.dlopen("libUltralight.so")
                case _:
                    raise Exception("Unrecognized operating system")

            self._font_wrapper = UserInterface.FontWrapper(self._ffi, self._lib)
            self._fs_wrapper = UserInterface.FSWrapper(self._ffi, self._lib)
            self._lib.ulPlatformSetFileSystem(self._fs_wrapper.struct[0])
            self._lib.ulPlatformSetFontLoader(self._font_wrapper.struct[0])

            self._config = self._lib.ulCreateConfig()
            self.renderer = self._lib.ulCreateRenderer(self._config)

            view_config = self._lib.ulCreateViewConfig()
            self.view = self._lib.ulCreateView(self.renderer, screen_dimensions[0], screen_dimensions[1], view_config, self._ffi.NULL)
            self._lib.ulDestroyViewConfig(view_config)
    
    async def boot(self) -> bool:
        return True

    @System.on(Events.Render, System.Priority.LOWEST)
    async def onRenderStep(self, event: Events.Render) -> bool:
        return False

    @System.on(Events.Render, System.Priority.LOWEST)
    async def onRenderStep(self, event: Events.Render) -> bool:
        return False

'''
                /*typedef struct {
                    uint32_t display_id;
                    bool is_accelerated;
                    double initial_device_scale;
                    bool is_transparent;
                    bool initial_focus;
                    bool enable_images;
                    bool enable_javascript;
                    bool enable_compositor;
                    ULString font_family_standard;
                    ULString font_family_fixed;
                    ULString font_family_serif;
                    ULString font_family_sans_serif;
                    ULString user_agent;
                } ULViewConfig;*/
class FontWrapper:
    def __init__(self, ffi, lib):
        self._ffi = ffi
        self._lib = lib
        self._pins = [
            self._ffi.callback("void*()")(self.getFallback),
            self._ffi.callback("void*(void*, int, bool)")(self.getFallbackForChars),
            self._ffi.callback("void*(void*, int, bool)")(self.getMetadata),
            self._ffi.callback("void*(void*, unsigned int)")(self.renderGlyph)
        ]
        self._struct = self._ffi.new("ULFontLoader*")
        self._struct.get_fallback_font = self._pins[0]
        self._struct.get_fallback_font_for_characters = self._pins[1]
        self._struct.get_font_metadata = self._pins[2]
        self._struct.render_glyph = self._pins[3]
    
    @property
    def struct(self):
        return self._struct

    def getFallback(self):
        return self._ffi.NULL

    def getFallbackForChars(self, characters, weight, italic):
        return self._ffi.NULL

    def getMetadata(self, family, weight, italic):
        return self._ffi.NULL

    def renderGlyph(self, font_handle, glyph_id):
        return self._ffi.NULL

class FSWrapper:
    def __init__(self, ffi, lib):
        self._ffi = ffi
        self._lib = lib
        self._pins = [
            self._ffi.callback("bool(void*)")(self.exists),
            self._ffi.callback("void*(void*)")(self.charset),
            self._ffi.callback("long long(void*)")(self.size),
            self._ffi.callback("void*(void*, bool)")(self.open),
            self._ffi.callback("void(void*)")(self.close),
            self._ffi.callback("long long(void*, char*, long long)")(self.read)
        ]
        self._open_files = {}

        self._struct = self._ffi.new("ULFileSystem*")
        self._struct.file_exists = self._pins[0]
        self._struct.get_file_charset = self._pins[1]
        self._struct.get_file_size = self._pins[2]
        self._struct.open_file = self._pins[3]
        self._struct.close_file = self._pins[4]
        self._struct.read_file = self._pins[5]

    @property
    def struct(self):
        return self._struct

    def getPath(self, path):
        return self._ffi.string(self._lib.ulStringGetData(path)).decode("utf-8")

    def charset(self, path):
        return self._ffi.NULL

    def exists(self, path):
        return Resources.file_system().exists(self.getPath(path))

    def open(self, path, mode):
        file = Resources.file_system().open(self.getPath(path), "rb")
        if file:
            handle = self._ffi.new_handle(file)
            self._open_files[handle] = file
        return handle if file else self._ffi.NULL

    def size(self, handle):
        file = self._ffi.from_handle(handle)
        pos = file.tell()
        file.seek(0, 2)
        size = file.tell()
        file.seek(pos)
        return size

    def read(self, handle, data_ptr, length):
        file = self._ffi.from_handle(handle)
        chunk = file.read(length)
        self._ffi.memmove(data_ptr, chunk, len(chunk))
        return len(chunk)

    def close(self, handle):
        file = self._open_files.pop(handle, None)
        if file:
            file.close()
'''
'''
from enum import Enum
import Events
import ctypes
import platform
import time
import numpy as np

import Resources


class UserInterface(System):
    __sciter_dll = None
    __sciter_api = None
    __sciter_set_callback = None
    __sciter_html = None
    __sciter = None

    class MessageType(int, Enum):
        CREATE = 0
        SIZE = 1
        DESTROY = 2
        PAINT = 3
        MOUSE = 5
        HEARTBIT = 6

    
    class NotificationCode(Enum):
        LOAD_DATA = 0x01
        DATA_LOADED = 0x02
        ATTACH_BEHAVIOR = 0x04
        ENGINE_DESTROYED = 0x05
        POST_REDRAW = 0x06
        CALLBACK_HOST = 0x07


    class Notification(ctypes.Structure):
        _fields_ = [
            ("code", ctypes.c_uint32),
            ("hwnd", ctypes.c_void_p)
        ]


    class MessageCreate(ctypes.Structure):
        _fields_ = [
            ("type", ctypes.c_uint32),
            ("backend", ctypes.c_uint32),
            ("transparent", ctypes.c_bool)
        ]

    
    class MessageDestroy(ctypes.Structure):
        _fields_ = [
            ("types", ctypes.c_uint32)
        ]

    
    class Bitmap(ctypes.Structure):
        _fields_ = [
            ("pixels", ctypes.c_void_p),
            ("width", ctypes.c_uint32),
            ("height", ctypes.c_uint32),
            ("stride", ctypes.c_uint32)
        ]

    class MessageSize(ctypes.Structure): pass
    MessageSize._fields_ = [
        ("type", ctypes.c_uint32),
        ("width", ctypes.c_uint32),
        ("height", ctypes.c_uint32),
        ("padding", ctypes.c_uint32),
        ("bitmap", ctypes.POINTER(Bitmap)) #must use awkward initalization due to referencing UserInterface.Bitmap
    ]
        

    class MessageHeartBit(ctypes.Structure):
        _fields_ = [
            ("type", ctypes.c_uint32),
            ("padding", ctypes.c_uint32),
            ("time", ctypes.c_uint64)
        ]

    class MessagePaint(ctypes.Structure):
        _fields_ = [
            ("type", ctypes.c_uint32),
            ("padding", ctypes.c_uint32),
            ("element", ctypes.c_void_p),
            ("is_foreground", ctypes.c_bool),
            ("reserved", ctypes.c_uint32)
        ]

    class Point(ctypes.Structure):
        _fields_ = [
            ("x", ctypes.c_int32),
            ("y", ctypes.c_int32)
        ]


    # odd, but necessary (see below)
    class MouseData(ctypes.Structure): pass
    MouseData._fields_ = [
        ("type", ctypes.c_uint32),
        ("button", ctypes.c_uint32),
        ("modifiers", ctypes.c_uint32),
        ("pos", Point) # THIS is what's making this complicated
    ]



    def __init__(self, screen_dimensions: tuple[int, int], **kwargs):
        super().__init__(**kwargs)

        # Load DLL if not already
        if not UserInterface.__sciter_dll:
            match platform.system():
                case "Linux":
                    UserInterface.__sciter_dll = ctypes.CDLL("libsciter.so", mode=ctypes.RTLD_GLOBAL)
                case _:
                    raise Exception("Unrecognized operating system")

        self.engine: ctypes.c_void_p = ctypes.c_void_p(0)
        self.callback_ref = (ctypes.CFUNCTYPE(ctypes.c_uint32, ctypes.POINTER(UserInterface.Notification), ctypes.c_void_p))(self.handleSciterNotification)

        # Init api if not already
        if not UserInterface.__sciter_api:
            func = UserInterface.__sciter_dll.SciterAPI
            func.restype = ctypes.POINTER(ctypes.c_void_p)
            UserInterface.__sciter_api = func()

            if not UserInterface.__sciter:
                ptr = UserInterface.__sciter_api[231]
                if ptr is not None:
                    UserInterface.__sciter = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p)(ptr)
                    UserInterface.__sciter.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
                    UserInterface.__sciter.restype = ctypes.c_int32
                else:
                    raise Exception("Cannot find SciterProcX. Library version mismatch likely.")

                ptr = UserInterface.__sciter_api[13]
                if ptr is not None:
                    UserInterface.__sciter_html = ctypes.CFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_char_p, ctypes.c_uint, ctypes.c_wchar_p)(ptr)

                ptr = UserInterface.__sciter_api[7]
                if ptr is not None:
                    UserInterface.__sciter_set_callback = (ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p))(ptr)
                else:
                    raise Exception("Cannot find SciterSetCallback. Library version mismatch likely.")

        self.screen_dimensions: tuple[int, int] = screen_dimensions
        self.buffer = np.zeros((screen_dimensions[1], screen_dimensions[0], 4), dtype=np.uint8) # note (HEIGHT, width, 4)
        self.bitmap = UserInterface.Bitmap(
            pixels=self.buffer.ctypes.data_as(ctypes.c_void_p),
            width=screen_dimensions[0],
            height=screen_dimensions[1],
            stride=screen_dimensions[0]*4
        )
        self.bitmap_ptr = ctypes.pointer(self.bitmap) #pinned for garbage collection
        self.engine_start = time.monotonic()

    def handleSciterNotification(self, p_notify, param):
        print("?") # TODO: investigate why this isn't hooked
        return 0

    async def boot(self) -> bool:
        # Boot the sciter engine
        if not UserInterface.__sciter(ctypes.byref(self.engine), ctypes.byref(UserInterface.MessageCreate(
            type=UserInterface.MessageType.CREATE,
            backend=1,
            transparent=True
        ))):
            raise Exception("Failed to boot Sciter")

        # Hook callbacks
        UserInterface.__sciter_set_callback(self.engine, self.callback_ref, None)

        # Set buffer
        UserInterface.__sciter(self.engine, ctypes.byref(UserInterface.MessageSize(
            type=UserInterface.MessageType.SIZE,
            width=self.screen_dimensions[0],
            height=self.screen_dimensions[1],
            bitmap=self.bitmap_ptr
        )))

        with Resources.file_system().open("interface/main.html", "rb") as html_file:
            html_bytes = html_file.read()
            status = UserInterface.__sciter_html(self.engine, html_bytes, len(html_bytes), None)
        return True

    @System.on(Events.Render, System.Priority.LOWEST)
    async def onRenderStep(self, event: Events.Render) -> bool:
        print("!")
        UserInterface.__sciter(self.engine, ctypes.byref(UserInterface.MessageHeartBit(
            type=UserInterface.MessageType.HEARTBIT,
            padding = 0,
            time=int((time.monotonic() - self.engine_start)*1000)
        )))
        UserInterface.__sciter(self.engine,ctypes.byref(UserInterface.MessagePaint(
            type=UserInterface.MessageType.PAINT,
            element=None,
            is_foreground=False,
            reserved=0
        )))
        print("LE WUT?")
        return False


    #@System.on(Events.FromSDL, System.Priority.HIGHEST)
    async def convertSDLEvent(self, event: Events.FromSDL) -> bool:
        #message = 
        return sciter.SciterProcX(self.engine, ctypes.byref(message))
'''