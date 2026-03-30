from __future__ import annotations
from cffi import FFI
from enum import Enum, auto as EnumAuto
from queue import Queue
import sys
import os
import platform
import ctypes

import Systems, Events, Resources, Components

class AudioTrigger(Events.Event):
    __reverse_counter = -1

    class PlaybackType(int, Enum):
        FIRE_AND_FORGET = EnumAuto()
        RETAIN = EnumAuto()

    def __init__(self, fmod_event: str, eid: int = 0, playback: PlaybackType = PlaybackType.FIRE_AND_FORGET, parameters: dict = None, **kwargs):
        super().__init__(**kwargs)
        self.fmod_event: str = fmod_event
        self.eid: int = eid
        if self.eid == 0:
            AudioTrigger.__reverse_counter -= 1
            self.eid = AudioTrigger.__reverse_counter
        self.playback: AudioTrigger.PlaybackType = playback
        self.parameters: dict = parameters or {}

class AudioParameters(Events.Event):
    def __init__(self, fmod_event: str, eid: int, parameters: dict):
        self.fmod_event: str = fmod_event
        self.eid: int = eid
        self.parameters: dict = parameters or {}

class AudioController(Systems.System):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._ffi = None
        self._core = None
        self._studio = None
        self._system = None
        self._event_callback = None
        self._pinned_banks = {}
        self._pinned_events = {}
        self.remove_queue:Queue = Queue()

        if not self._ffi:
            include_path = os.path.join(getattr(sys, '_MEIPASS', os.getcwd()), "src", "Include", "fmod.h")
            lib_path = getattr(sys, '_MEIPASS', os.getcwd())
            self._ffi = FFI()
            with open(include_path, "r") as file:
                self._ffi.cdef(file.read())

            match platform.system():
                case "Linux":
                    self._core = self._ffi.dlopen(os.path.join(lib_path, "libfmod.so.14.12"))
                    self._studio = self._ffi.dlopen(os.path.join(lib_path, "libfmodstudio.so.14.12"))
                case _:
                    raise Exception("Unrecognized operating system")

    async def boot(self) -> bool:
        result = True
        system_ptr = self._ffi.new("FMOD_STUDIO_SYSTEM**")
        try:
            assert self._studio.FMOD_Studio_System_Create(system_ptr, 0x00020312) == 0, "System_Create Failed!"
            self._system = system_ptr[0]
            assert self._studio.FMOD_Studio_System_Initialize(self._system, 1024, self._studio.FMOD_STUDIO_INIT_SYNCHRONOUS_UPDATE, 0, self._ffi.NULL) == 0, "System_Initialize Failed!"

            fmod_path = "fmod/"
            file_system = Resources.file_system()
            for file in file_system.listdir(fmod_path):
                full_path = f"{fmod_path}/{file}"
                if file_system.isfile(full_path) and file.endswith(".bank"):
                    with file_system.open(full_path, "rb") as bank_bin:
                        bank_bytes = bank_bin.read()
                        bank_buffer = self._ffi.new("char[]", bank_bytes)
                        bank_ptr = self._ffi.new("FMOD_STUDIO_BANK**")
                        try:
                            assert self._studio.FMOD_Studio_System_LoadBankMemory(self._system, bank_buffer, len(bank_bytes) , 0, 0, bank_ptr) == 0, "System_LoadBankMemory Failed!"
                            self._pinned_banks[full_path] = {
                                "pointer": bank_ptr,
                                "buffer": bank_buffer,
                                "bank": bank_ptr[0]
                            }
                            count_ptr = self._ffi.new("int*")
                            assert self._studio.FMOD_Studio_Bank_GetEventCount(bank_ptr[0], count_ptr) == 0, "Bank_GetEventCount Failed!"
                            event_list = self._ffi.new("FMOD_STUDIO_EVENTDESCRIPTION*[]", count_ptr[0])
                            assert self._studio.FMOD_Studio_Bank_GetEventList(bank_ptr[0], event_list, count_ptr[0], count_ptr) == 0, "Bank_GetEventList"
                            is_stream_ptr = self._ffi.new("FMOD_BOOL*")
                            for desc in event_list:
                                self._studio.FMOD_Studio_EventDescription_IsStream(desc, is_stream_ptr)
                                if not is_stream_ptr[0]:
                                    self._studio.FMOD_Studio_EventDescription_LoadSampleData(desc)
                        except AssertionError as err:
                            print(f"Failed to load `{full_path}`: {err}")
            self._event_callback = self._ffi.callback("FMOD_RESULT(FMOD_STUDIO_EVENT_CALLBACK_TYPE, FMOD_STUDIO_EVENTINSTANCE*, void*)")(self.fmodEventCallback)
        except AssertionError as err:
            print(f"Failed to boot: {err}") #TODO: another place to properly log
            result = False
        return result

    async def unboot(self) -> None:
        #TODO: Must clear out all the pinned stuff
        self._studio.FMOD_Studio_System_Release(self._system)

    def fmodEventCallback(self, evt_type, event_ptr, parameters):
        try:
            match evt_type:
                case self._studio.FMOD_STUDIO_EVENT_CALLBACK_STOPPED:
                    self.remove_queue.put(event_ptr)
        except AssertionError:
            print(f"Error in event callback: {err}") #TODO: propper logging!
        return 0

    @Systems.on(Events.Logic, Systems.Priority.LOWEST)
    async def onUpdate(self, event: Events.Logic) -> Events.Result:
        self._studio.FMOD_Studio_System_Update(self._system)
        while not self.remove_queue.empty():
            event_ptr = self.remove_queue.get()
            try:
                assert self._studio.FMOD_Studio_EventInstance_Release(event_ptr) == 0, "EventInstance_Release failed!"
            except AssertionError as err:
                print(f"Error cleaning event: {err}")

            self._pinned_events = {
                (fmod_event, eid): pins
                for (fmod_event, eid), pins in self._pinned_events.items()
                if pins.get("event_inst_ptr") != event_ptr
            }
        return event.result

    @Systems.on(Events.AudioTrigger, Systems.Priority.DEFAULT)
    async def onAudioTrigger(self, event: Events.AudioTrigger) -> Events.Result:
        event_desc_ptr = self._ffi.new("FMOD_STUDIO_EVENTDESCRIPTION**")
        #event_desc_buffer = self._ffi.new("char[]", event.fmod_event.encode("ascii"))
        event_inst_ptr = self._ffi.new("FMOD_STUDIO_EVENTINSTANCE**")
        try:
            #assert self._studio.FMOD_Studio_System_GetEvent(self._system, event_desc_buffer, event_desc_ptr) == 0, "System_GetEvent failed!"
            assert self._studio.FMOD_Studio_System_GetEvent(self._system, event.fmod_event.encode("ascii"), event_desc_ptr) == 0, "System_GetEvent failed!"
            assert self._studio.FMOD_Studio_EventDescription_CreateInstance(event_desc_ptr[0], event_inst_ptr) == 0, "EventDescription_CreateInstance failed!"
            assert self._studio.FMOD_Studio_EventInstance_Start(event_inst_ptr[0]) == 0, "EventInstance_Start failed!"
            if event.playback == Events.AudioTrigger.PlaybackType.FIRE_AND_FORGET:
                assert self._studio.FMOD_Studio_EventInstance_Release(event_inst_ptr[0]) == 0, "EventInstance_Release!"
            else:
                composite_key = (event.fmod_event, event.eid)
                if composite_key in self._pinned_events:
                    old_inst_ptr = self._pinned_events[composite_key]["event_inst_ptr"]
                    assert self._studio.FMOD_Studio_EventInstance_Stop(old_inst_ptr, self._studio.FMOD_STUDIO_STOP_ALLOWFADEOUT) == 0, "EventInstance_Stop failed for replacement!"
                    assert self._studio.FMOD_Studio_EventInstance_SetCallback(old_inst_ptr, self._ffi.NULL, 0) == 0, "EventInstance_SetCallback failed for replacement!"
                    assert self._studio.FMOD_Studio_EventInstance_Release(old_inst_ptr) == 0, "EventInstance_Release failed on replaced event!"
                masks = self._studio.FMOD_STUDIO_EVENT_CALLBACK_STOPPED | self._studio.FMOD_STUDIO_EVENT_CALLBACK_DESTROYED
                assert self._studio.FMOD_Studio_EventInstance_SetCallback(event_inst_ptr[0], self._event_callback, masks) == 0, "EventInstance_SetCallback failed!"
                self._pinned_events[composite_key] = {
                    "event_inst_ptr": event_inst_ptr[0],
                    "playback": event.playback
                }
                for name, details in event.parameters.items():
                    value = details.get("value")
                    ignore = details.get("ignore", 1)
                    if type(value) == str:
                        self._studio.FMOD_Studio_EventInstance_SetParameterByNameWithLabel(event_inst_ptr[0], name.encode("ascii"), value.encode("ascii"), ignore)
                    else:
                        self._studio.FMOD_Studio_EventInstance_SetParameterByName(event_inst_ptr[0], name.encode("ascii"), float(value or 0), ignore)

        except AssertionError as err:
            print(f"Failed to play sound: {err}") #TODO: propper logging!
        return event.result

    
    @Systems.on(Events.AudioParameters, Systems.Priority.DEFAULT)
    async def onParameterchange(self, event: Events.AudioParameters) -> Events.Result:
        composite_key = (event.fmod_event, event.eid)
        instance = self._pinned_events.get(composite_key)
        if instance:
            for name, details in event.parameters.items():
                value = details.get("value")
                ignore = details.get("ignore", 1)
                if type(value) == str:
                    self._studio.FMOD_Studio_EventInstance_SetParameterByNameWithLabel(instance["event_inst_ptr"], name.encode("ascii"), value.encode("ascii"), ignore)
                else:
                    self._studio.FMOD_Studio_EventInstance_SetParameterByName(instance["event_inst_ptr"], name.encode("ascii"), float(value or 0), ignore)