from __future__ import annotations
from cffi import FFI
import sys
import os
import platform
import ctypes
import Systems, Events, Resources, Components

class AudioTrigger(Events.Event):
    def __init__(self, fmod_event: str, **kwargs):
        super().__init__(**kwargs)
        self.fmod_event: str = fmod_event

class AudioController(Systems.System):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._ffi = None
        self._core = None
        self._studio = None
        self._system = None
        self._pinned_banks = {}

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
            assert self._studio.FMOD_Studio_System_Initialize(self._system, 256, 0, 0, self._ffi.NULL) == 0, "System_Initialize Failed!"

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
        except AssertionError as err:
            print(f"Failed to boot: {err}") #TODO: another place to properly log
            result = False
        return result

    async def unboot(self) -> None:
        #TODO: Must clear out all the pinned stuff
        self._studio.FMOD_Studio_System_Release(self._system)

    @Systems.on(Events.Logic, Systems.Priority.LOWEST)
    async def onUpdate(self, event: Events.Logic) -> Events.Result:
        self._studio.FMOD_Studio_System_Update(self._system)
        return event.result

    @Systems.on(Events.AudioTrigger, Systems.Priority.DEFAULT)
    async def onAudioTrigger(self, event: Events.AudioTrigger) -> Events.Result:
        event_desc_ptr = self._ffi.new("FMOD_STUDIO_EVENTDESCRIPTION**")
        event_desc_buffer = self._ffi.new("char[]", event.fmod_event.encode("ascii"))
        event_inst_ptr = self._ffi.new("FMOD_STUDIO_EVENTINSTANCE**")
        try:
            assert self._studio.FMOD_Studio_System_GetEvent(self._system, event_desc_buffer, event_desc_ptr) == 0, "System_GetEvent failed!"
            assert self._studio.FMOD_Studio_EventDescription_CreateInstance(event_desc_ptr[0], event_inst_ptr) == 0, "EventDescription_CreateInstance failed!"
            assert self._studio.FMOD_Studio_EventInstance_Start(event_inst_ptr[0]) == 0, "EventInstance_Start failed!"
            assert self._studio.FMOD_Studio_EventInstance_Release(event_inst_ptr[0]) == 0, "EventInstance_Release failed!"
        except AssertionError as err:
            print(f"Failed to play sound: ${err}") #TODO: propper logging!
        return event.result