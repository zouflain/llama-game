from Systems import System
class GamepadController(System):
    '''...'''
    def __init__(self, deadzone: int=BASE_DEADZONE, **kwargs):
        '''...'''

class EntityController(System):
    '''...'''
    def __init__(self, current_entity: int=0, **kwargs):
        '''...'''

class CameraSystem(System):
    '''...'''
    def __init__(self, **kwargs):
        '''...'''

class AudioController(System):
    '''...'''
    def __init__(self, **kwargs):
        '''...'''

    def fmodEventCallback(self, evt_type, event_ptr, parameters):
        '''...'''

class UserInterface(System):
    '''...'''
    def __init__(self, screen_dimensions: tuple[int, int], **kwargs):
        '''...'''

    def callJSFunc(self, func_name: str, data: dict=None):
        '''...'''

    def jsTriggerEvent(self, ctx, func, this, argc, args, exception):
        '''...'''

    def jsClickMouse(self, ctx, func, this, argc, args, exception):
        '''...'''

    def jsGetMouse(self, ctx, func, this, argc, args, exception):
        '''...'''

    def helperJSExtractJSON(self, ref, context):
        '''...'''

    def helperJSExtractString(self, ref, context):
        '''...'''

    def callbackConsoleLog(self, user_data, caller, source, level, message, line_number, column_number, source_id):
        '''...'''

    def callbackDomReady(self, user_data, caller, frame_id, is_main_frame, url):
        '''...'''

    def callbackWindowReady(self, user_data, caller, frame_id, is_main_frame, url):
        '''...'''

    def callbackChangeCursor(self, user_data, caller, cursor):
        '''...'''

class Battle(System):
    '''...'''
    def __init__(self, **kwargs):
        '''...'''

