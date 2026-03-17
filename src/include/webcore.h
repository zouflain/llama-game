typedef void* JSContextRef;
typedef void* JSObjectRef;
typedef void* JSValueRef;
typedef void* JSStringRef;
typedef JSValueRef* JSValueRefPtr;
typedef JSValueRef (*JSObjectCallAsFunctionCallback)(JSContextRef ctx, JSObjectRef function, JSObjectRef thisObject, size_t argumentCount, const JSValueRef arguments[], JSValueRefPtr exception);

JSObjectRef JSContextGetGlobalObject(JSContextRef ctx);
JSStringRef JSStringCreateWithUTF8CString(const char* string);
JSObjectRef JSObjectMakeFunctionWithCallback(JSContextRef ctx, JSStringRef name, JSObjectCallAsFunctionCallback callback);
void JSObjectSetProperty(JSContextRef ctx, JSObjectRef object, JSStringRef name, JSValueRef value, int attributes, JSValueRef* exception);
void JSStringRelease(JSStringRef string);
JSValueRef JSEvaluateScript(JSContextRef ctx, JSStringRef script, JSObjectRef thisObject, JSStringRef sourceURL, int startingLineNumber, JSValueRef* exception);
bool JSValueIsString(JSContextRef ctx, JSValueRef value);

JSStringRef JSValueToStringCopy(JSContextRef ctx, JSValueRef value, JSValueRef* exception);
size_t JSStringGetMaximumUTF8CStringSize(JSStringRef string);
size_t JSStringGetUTF8CString(JSStringRef string, char* buffer, size_t bufferSize);
/*
bool JSValueIsBoolean(JSContextRef ctx, JSValueRef value);
bool JSValueToBoolean(JSContextRef ctx, JSValueRef value);
*/