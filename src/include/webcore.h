typedef void* JSContextRef;
typedef void* JSObjectRef;
typedef void* JSValueRef;
typedef void* JSStringRef;
typedef void* JSValueRefPtr;
typedef JSValueRef (*JSObjectCallAsFunctionCallback)(JSContextRef ctx, JSObjectRef function, JSObjectRef thisObject, size_t argumentCount, const JSValueRef arguments[], JSValueRefPtr exception);

JSObjectRef JSContextGetGlobalObject(JSContextRef ctx);
JSStringRef JSStringCreateWithUTF8CString(const char* string);
JSObjectRef JSObjectMakeFunctionWithCallback(JSContextRef ctx, JSStringRef name, JSObjectCallAsFunctionCallback callback);
void JSObjectSetProperty(JSContextRef ctx, JSObjectRef object, JSStringRef name, JSValueRef value, int attributes, JSValueRef* exception);
void JSStringRelease(JSStringRef string);

//so far unused
bool JSValueToBoolean(JSContextRef ctx, JSValueRef value);