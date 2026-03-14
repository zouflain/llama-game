from .resource import Resource
from .shader import Shader
from PIL import Image
from enum import Enum, Flag, auto as EnumAuto
import OpenGL.GL as GL
import numpy as np


class GlyphSet(Resource):
    __MAX_CHARACTERS: int = 500
    __glyph_dtype: np.dtype = np.dtype(
        [
            ("char", np.int32),
            ("flags", np.uint32),
            ("color", (np.float32, 3))
        ]
    )

    class Flag(int, Flag):
        BOLD = EnumAuto()


    class Bindings(int, Enum):
        #SSBO bindings
        GLYPHS = 0

        #Uniform Bindings
        GLYPH_IMAGE = 0
        SOURCE_IMAGE = 1

        #Uniform Layouts
        START_OFFSET = 0
        BOX_SIZE = 1
        LINE_LENGTH = 2
        GLYPH_SIZE = 3


    def __init__(self, name: str, permanent: bool, texture_id: int, glyph_ssbo: int):
        super().__init__(name, permanent)
        self.texture_id: int = texture_id
        self.glyph_ssbo: int = glyph_ssbo

    def getArray(self, raw_text: str, line_length: int, max_lines: int, base_color: tuple[float, float, float]) -> np.array:
        flags = 0
        index = 0
        color = base_color
        glyph_arr = np.zeros(GlyphSet.__MAX_CHARACTERS, dtype=GlyphSet.__glyph_dtype)
        glyph_arr[:]["char"] = ord(' ') # unrenderable characters often have giberish glyphs (eg chr(0))
        text = raw_text[:]

        # Format the text
        ## split into initial lines
        lines = text.split("\n")
        new_lines = []
        for line in lines:
            # split initial lines into further lines, where necessary (skip formatting)
            new_line = ""
            count = 0
            while line:
                letter = line[0]
                match letter:
                    case '*':
                        new_line += letter
                        line = line[1:]
                    case '#':
                        if line[1] == '#':
                            new_line += line[0:2]
                            line = line[2:]
                        else:
                            new_line += line[0:7]
                            line = line[7:]
                    case _:
                        new_line += letter
                        line = line[1:]
                        count += 1
                if count == line_length:
                    new_lines.append(new_line)
                    new_line = ""
                    count = 0
            if new_line:
                new_lines.append(new_line.ljust(line_length+len(new_line)-count, ' '))
        
            

        text = "".join(new_lines[:max_lines])
        while text and index < min(line_length*max_lines, GlyphSet.__MAX_CHARACTERS):
            letter = text[0]
            match letter:
                case '*':
                    flags = flags ^ GlyphSet.Flag.BOLD
                    text = text[1:]
                    continue
                case '#':
                    if text[1] == '#':
                        color = base_color
                        text = text[2:]
                        continue
                    else:
                        hex = text[1:7]
                        color = (
                            int(f"0x{text[1:3]}", 0)/255.0,
                            int(f"0x{text[3:5]}", 0)/255.0,
                            int(f"0x{text[5:7]}", 0)/255.0
                        )
                        text = text[7:]
                        continue
                case _:
                    text = text[1:]
            glyph_arr[index]["color"] = color
            glyph_arr[index]["flags"] = flags
            glyph_arr[index]["char"] = ord(letter)
            index += 1

        return glyph_arr

    def draw(self, program: Shader.Binding, resolution: tuple[int, int], source_layer: int, text: str, where: tuple[int, int], char_size: int, box_size: tuple[float, float], base_color: tuple[float, float, float]) -> None:
        line_length = int(box_size[0]/float(char_size if char_size > 0 else 1))
        max_lines = int(box_size[1]/float(char_size if char_size > 0 else 1))

        buffer_array = self.getArray(text, line_length, max_lines, base_color)
        GL.glNamedBufferSubData(self.glyph_ssbo, 0, buffer_array.nbytes, buffer_array)

        program.bind(GL.GL_SHADER_STORAGE_BUFFER, GlyphSet.Bindings.GLYPHS, self.glyph_ssbo)

        GL.glUniform2iv(GlyphSet.Bindings.START_OFFSET, 1, where)
        GL.glUniform2iv(GlyphSet.Bindings.BOX_SIZE, 1, box_size)
        GL.glUniform1i(GlyphSet.Bindings.LINE_LENGTH, line_length)
        #GL.glUniform1f(GlyphSet.Bindings.GLYPH_SIZE, line_length)
        GL.glBindTextureUnit(GlyphSet.Bindings.GLYPH_IMAGE, self.texture_id)
        #GL.glBindImageTexture(GlyphSet.Bindings.GLYPH_IMAGE, self.texture_id, 0, GL.GL_FALSE, 0, GL.GL_READ_ONLY, GL.GL_RGBA8)
        GL.glBindImageTexture(GlyphSet.Bindings.SOURCE_IMAGE, source_layer, 0, GL.GL_FALSE, 0, GL.GL_READ_WRITE, GL.GL_RGBA32F)
        GL.glDispatchCompute(int(resolution[0]/32)+1, int(resolution[1]/32)+1, 1, 0)


    @staticmethod
    async def allocate(name: str, permanent: bool, file_list: list[str]) -> GlyphSet:
        for fname in file_list:
            with Resource.file_system().openbin(fname, mode="rb") as file:
                with Image.open(file) as raw:
                    image = raw.convert("RGBA")
                    width, height = image.size

                    texture_id = GL.glGenTextures(1)
                    GL.glBindTexture(GL.GL_TEXTURE_2D, texture_id)
                    GL.glPixelStorei(GL.GL_UNPACK_ALIGNMENT, 1)
                    GL.glTexImage2D(GL.GL_TEXTURE_2D, 0, GL.GL_RGBA8, width, height, 0, GL.GL_RGBA, GL.GL_UNSIGNED_BYTE, image.tobytes())
                    GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, GL.GL_LINEAR)
                    GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, GL.GL_LINEAR)
                    GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_S, GL.GL_CLAMP_TO_EDGE)
                    GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_T, GL.GL_CLAMP_TO_EDGE)

                    buffer_array = (GL.GLuint * 1)()
                    GL.glCreateBuffers(1, buffer_array)
                    glyph_ssbo = buffer_array[0]
                    GL.glNamedBufferStorage(glyph_ssbo, GlyphSet.__MAX_CHARACTERS*GlyphSet.__glyph_dtype.itemsize, None, GL.GL_DYNAMIC_STORAGE_BIT)

        item = GlyphSet(name, permanent, texture_id, glyph_ssbo)
        await item.register()
        return item

    async def deallocate(self) -> None:
        GL.glDeleteTextures(1, [self.texture_id])
        self.texture = 0
        await super().deallocate()