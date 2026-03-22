from Systems import System
class EntityController(System): '''...'''
	def __init__(self, current_entity: int=0, **kwargs): '''...'''

class UserInterface(System): '''...'''
	def __init__(self, screen_dimensions: tuple[int, int], **kwargs): '''...'''

	def callJSFunc(self, func_name: str, data: dict=None): '''...'''

	def jsSnapMouse(self, ctx, func, this, argc, args, exception): '''...'''

	def helperJSExtractString(self, ref, context): '''...'''

	def callbackConsoleLog(self, user_data, caller, source, level, message, line_number, column_number, source_id): '''...'''

	def callbackWindowReady(self, user_data, caller, frame_id, is_main_frame, url): '''...'''

	def callbackChangeCursor(self, user_data, caller, cursor): '''...'''

class Battle(System): '''...'''
	def __init__(self, **kwargs): '''...'''

