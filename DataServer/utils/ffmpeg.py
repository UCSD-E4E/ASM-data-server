from abc import ABC, abstractmethod
from typing import List, Optional

class MediaInput(ABC):
    @abstractmethod
    def create_ffmpeg_opts(self) -> List[str]:
        pass

class MediaOutput(ABC):
    @abstractmethod
    def create_ffmpeg_opts(self) -> List[str]:
        pass

class FFMPEGInstance:
    def __init__(self, *, input_obj: Optional[MediaInput] = None, output_obj: Optional[MediaOutput] = None):
        self.__input = input_obj
        self.__output = output_obj
        self.__time: Optional[int] = None

    def get_args(self) -> List[str]:
        opts = []
        if self.__input is None:
            raise RuntimeError("No input configuration")
        opts.extend(self.__input.create_ffmpeg_opts())
        if self.__time is not None:
            opts.extend(['-t', f'{self.__time}'])
        if self.__output is None:
            raise RuntimeError("No output configuration")
        opts.extend(self.__output.create_ffmpeg_opts())
        return opts

    def get_command(self) -> List[str]:
        cmd = ['ffmpeg']
        cmd.extend(self.get_args())
        return cmd

    def set_input(self, input_obj: MediaInput):
        self.__input = input_obj

    def set_output(self, output_obj: MediaOutput):
        self.__output = output_obj

    def set_time(self, time_s:int):
        self.__time = time_s
