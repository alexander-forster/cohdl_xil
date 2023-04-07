from __future__ import annotations

import cohdl
from cohdl import Signal, Unsigned, Bit, Array, BitVector
from cohdl import std


from example.vga.vga_impl.vga import VgaScreen, VgaWindow, Rgb
from example.vga.vga_impl.font_reader import FontReader


class Font:
    @cohdl.consteval
    def __init__(self):
        ...

    @cohdl.consteval
    def gen_lookup(self, cnt: int):
        return Signal[Array[Unsigned.upto(self.symbol_cnt() - 1), cnt]]()

    @cohdl.consteval
    def gen_memory(self):
        return Signal[Array[BitVector[self.symbol_bits()], self.symbol_cnt()]](
            self.array_definition()
        )

    @cohdl.consteval
    def symbol_cnt(self):
        return len(self.array_definition())

    @cohdl.consteval
    def pixel_cnt(self):
        return self.width() * self.height()

    @cohdl.consteval
    def symbol_bits(self):
        return len(self.array_definition()[0])

    @cohdl.consteval
    def get_letter(self, index):
        return self.array_definition()[index]

    def decode_pixel(self, pixelmask, pixelindex):
        return pixelmask[pixelindex]

    #
    #
    #

    @cohdl.consteval
    def array_definition(self):
        return []

    @cohdl.consteval
    def width(self):
        pass

    @cohdl.consteval
    def height(self):
        pass


class FileFont(Font):
    def __init__(self, filepath, height):
        super().__init__()

        font_reader = FontReader(filepath, height)
        self._array_def = font_reader.array_def()
        self._char_width = 8
        self._char_height = height

    @cohdl.consteval
    def array_definition(self):
        return self._array_def

    def decode_pixel(self, pixelmask, pixelindex):
        return pixelmask[pixelindex]

    @cohdl.consteval
    def width(self):
        return self._char_width

    @cohdl.consteval
    def height(self):
        return self._char_height


#
#
#
#


class AsciiWindow(VgaWindow):
    def __init__(
        self,
        screen: VgaScreen,
        line_cnt: int,
        column_cnt: int,
        font: Font = Font(),
        offset_x: int = 0,
        offset_y: int = 0,
        background=Rgb.black(),
        foreground=Rgb.white(),
        scale=1,
    ):
        scale_x = scale
        scale_y = scale

        self.foreground = foreground

        width = column_cnt * font.width() * scale_x
        height = line_cnt * font.height() * scale_y
        char_cnt = line_cnt * column_cnt
        super().__init__(
            screen, offset_x, offset_y, width, height, background=background
        )

        self.font = font
        self.font_memory = font.gen_memory()
        self.char_map = font.gen_lookup(char_cnt)

        self.end_of_line = Signal[bool](False)
        self.end_of_screen = Signal[bool](False)
        self.end_of_column = Signal[bool](False)
        self.end_of_char = Signal[bool](False)

        self.column_pos = Signal[Unsigned.upto(font.width() - 1)](0)
        self.pixel_index = Signal[Unsigned.upto(font.symbol_bits() - 1)](0)
        self.char_index = Signal[Unsigned.upto(char_cnt - 1)](0)
        self.current_bit = Signal[Bit](False)

        if scale_x == 1:
            scale_cnt_x = 0
        else:
            scale_cnt_x = Signal[Unsigned.upto(scale_x - 1)](0)

        if scale_y == 1:
            scale_cnt_y = 0
        else:
            scale_cnt_y = Signal[Unsigned.upto(scale_y - 1)](0)

        @std.concurrent
        def logic():
            self.end_of_column <<= self.column_pos == (font.width() - 1)
            self.end_of_line <<= self.x == (width - 1)
            self.end_of_screen <<= (self.x == (width - 1)) and (self.y == (height - 1))
            self.end_of_char <<= self.pixel_index == (font.pixel_cnt() - 1)

            currentchar = self.char_map[self.char_index]
            pixelmask = self.font_memory[currentchar]
            self.current_bit <<= font.decode_pixel(pixelmask, self.pixel_index)

        @std.sequential(screen.clk, screen.reset)
        def proc_column_pos():
            if self.active():
                if scale_cnt_x == scale_x - 1:
                    if self.end_of_column or self.end_of_screen:
                        self.column_pos <<= 0
                    else:
                        self.column_pos <<= self.column_pos + 1

        @std.sequential(screen.clk, screen.reset)
        def proc_indeces():
            if self.active():
                if self.end_of_screen:
                    if scale_x != 1:
                        scale_cnt_x.next = 0
                    if scale_y != 1:
                        scale_cnt_y.next = 0
                    self.pixel_index <<= 0
                    self.char_index <<= 0
                else:
                    if scale_cnt_x == scale_x - 1:
                        if scale_x != 1:
                            scale_cnt_x.next = 0

                        self.pixel_index <<= self.pixel_index + 1

                        if self.end_of_column:
                            self.pixel_index <<= self.pixel_index - (font.width() - 1)
                            self.char_index <<= self.char_index + 1

                        if self.end_of_line:
                            if scale_cnt_y == scale_y - 1:
                                if scale_y != 1:
                                    scale_cnt_y.next = 0

                                if self.end_of_char:
                                    self.pixel_index <<= 0
                                else:
                                    self.pixel_index <<= self.pixel_index + 1
                                    self.char_index <<= self.char_index - (
                                        column_cnt - 1
                                    )
                            else:
                                if scale_y != 1:
                                    scale_cnt_y.next = scale_cnt_y + 1
                                self.char_index <<= self.char_index - (column_cnt - 1)
                    else:
                        scale_cnt_x.next = scale_cnt_x + 1

    def set_letter(self, pos, letter):
        self.char_map[pos] <<= letter

    def draw(self, rgb: Rgb):
        if self.active():
            if self.current_bit:
                rgb.r <<= cohdl.Full
                rgb.g <<= cohdl.Full
                rgb.b <<= cohdl.Full
            else:
                rgb.r <<= cohdl.Null
                rgb.g <<= cohdl.Null
                rgb.b <<= cohdl.Null
