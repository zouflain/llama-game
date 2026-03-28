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
typedef enum {
  kMessageLevel_Log = 0,
  kMessageLevel_Warning,
  kMessageLevel_Error,
  kMessageLevel_Debug,
  kMessageLevel_Info,
} ULMessageLevel;
typedef enum {
  kMessageSource_XML = 0,
  kMessageSource_JS,
  kMessageSource_Network,
  kMessageSource_ConsoleAPI,
  kMessageSource_Storage,
  kMessageSource_AppCache,
  kMessageSource_Rendering,
  kMessageSource_CSS,
  kMessageSource_Security,
  kMessageSource_ContentBlocker,
  kMessageSource_Media,
  kMessageSource_MediaSource,
  kMessageSource_WebRTC,
  kMessageSource_ITPDebug,
  kMessageSource_PrivateClickMeasurement,
  kMessageSource_PaymentRequest,
  kMessageSource_Other,
} ULMessageSource;
typedef void* ULViewConfig;
typedef void* ULSession;
typedef void* ULView;
typedef void (*ULAddConsoleMessageCallback)(void* user_data, ULView caller, ULMessageSource source, ULMessageLevel level, ULString message, unsigned int line_number, unsigned int column_number, ULString source_id);

ULViewConfig ulCreateViewConfig();
void ulDestroyViewConfig(ULViewConfig config);
ULView ulCreateView(ULRenderer renderer, unsigned int width, unsigned int height, ULViewConfig view_config, ULSession session);
void ulViewConfigSetIsTransparent(ULViewConfig config, bool is_transparent);
void ulViewSetAddConsoleMessageCallback(ULView view, ULAddConsoleMessageCallback callback, void* user_data);

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
void ulViewLoadURL(ULView view, ULString url_string);

//Events
typedef enum {
    kKeyEventType_KeyDown,
    kKeyEventType_KeyUp,
    kKeyEventType_RawKeyDown,
    kKeyEventType_Char,
} ULKeyEventType;
typedef enum {
    kMod_AltKey = 1 << 0,
    kMod_CtrlKey = 1 << 1,
    kMod_MetaKey = 1 << 2,
    kMod_ShiftKey = 1 << 3,
} Modifiers;
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
typedef void* ULKeyEvent;

ULMouseEvent ulCreateMouseEvent(ULMouseEventType type, int x, int y, ULMouseButton button);
/*void ulMouseEventSetType(ULMouseEvent evt, ULMouseEventType type);
void ulMouseEventSetX(ULMouseEvent evt, int x);
void ulMouseEventSetY(ULMouseEvent evt, int y);
void ulMouseEventSetButton(ULMouseEvent evt, ULMouseButton button);*/
void ulViewFireMouseEvent(ULView view, ULMouseEvent evt);
void ulDestroyMouseEvent(ULMouseEvent evt);
ULKeyEvent ulCreateKeyEvent(ULKeyEventType type, unsigned int modifiers, int virtual_key_code, int native_key_code, ULString text, ULString unmodified_text, bool is_keypad, bool is_auto_repeat, bool is_system_key);
void ulViewFireKeyEvent(ULView view, ULKeyEvent key_event);
void ulDestroyKeyEvent(ULKeyEvent evt);

//keycodes
const int GK_TAB = 0x09;
const int GK_RETURN = 0x0D;
const int GK_SPACE = 0x20;
const int GK_ESCAPE = 0x1B;
const int GK_LEFT = 0x25;
const int GK_UP = 0x26;
const int GK_RIGHT = 0x27;
const int GK_DOWN = 0x28;

//Callbacks
typedef enum {
    kCursor_Pointer = 0,
    kCursor_Cross,
    kCursor_Hand,
    kCursor_IBeam,
    kCursor_Wait,
    kCursor_Help,
    kCursor_EastResize,
    kCursor_NorthResize,
    kCursor_NorthEastResize,
    kCursor_NorthWestResize,
    kCursor_SouthResize,
    kCursor_SouthEastResize,
    kCursor_SouthWestResize,
    kCursor_WestResize,
    kCursor_NorthSouthResize,
    kCursor_EastWestResize,
    kCursor_NorthEastSouthWestResize,
    kCursor_NorthWestSouthEastResize,
    kCursor_ColumnResize,
    kCursor_RowResize,
    kCursor_MiddlePanning,
    kCursor_EastPanning,
    kCursor_NorthPanning,
    kCursor_NorthEastPanning,
    kCursor_NorthWestPanning,
    kCursor_SouthPanning,
    kCursor_SouthEastPanning,
    kCursor_SouthWestPanning,
    kCursor_WestPanning,
    kCursor_Move,
    kCursor_VerticalText,
    kCursor_Cell,
    kCursor_ContextMenu,
    kCursor_Alias,
    kCursor_Progress,
    kCursor_NoDrop,
    kCursor_Copy,
    kCursor_None,
    kCursor_NotAllowed,
    kCursor_ZoomIn,
    kCursor_ZoomOut,
    kCursor_Grab,
    kCursor_Grabbing,
    kCursor_Custom
} ULCursor;
typedef void (*ULChangeCursorCallback)(void* user_data, ULView caller, ULCursor cursor);

void ulViewSetChangeCursorCallback(ULView view, ULChangeCursorCallback callback, void* user_data);

//Javascript
typedef void (*ULWindowObjectReadyCallback)(void* user_data, ULView caller, unsigned long long frame_id, bool is_main_frame, ULString url);
typedef void (*ULDOMReadyCallback)(void* user_data, ULView caller, unsigned long long frame_id, bool is_main_frame, ULString url);
void* ulViewLockJSContext(ULView view);
void ulViewUnlockJSContext(ULView view);
void ulViewSetWindowObjectReadyCallback(ULView view, ULWindowObjectReadyCallback callback, void* user_data);
void ulViewSetDOMReadyCallback(ULView view, ULDOMReadyCallback callback, void* user_data);