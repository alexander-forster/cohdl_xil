from __future__ import annotations

import cohdl
from cohdl import Signal, Unsigned, Bit
from cohdl import std


class Rgb(std.AssignableType):
    @staticmethod
    def black():
        return Rgb(cohdl.Null, cohdl.Null, cohdl.Null)

    @staticmethod
    def white():
        return Rgb(cohdl.Full, cohdl.Full, cohdl.Full)

    @staticmethod
    def red():
        return Rgb(cohdl.Full, cohdl.Null, cohdl.Null)

    @staticmethod
    def green():
        return Rgb(cohdl.Null, cohdl.Full, cohdl.Null)

    @staticmethod
    def blue():
        return Rgb(cohdl.Null, cohdl.Null, cohdl.Full)

    def __init__(self, r, g, b):
        self.r = r
        self.g = g
        self.b = b

    def _assign_(self, source, mode: cohdl.AssignMode):
        self.r._assign_(source.r, mode)
        self.g._assign_(source.g, mode)
        self.b._assign_(source.b, mode)


class VgaTiming:
    def __init__(self, visible: int, front: int, sync: int, back: int):
        self.visible = visible
        self.front = front
        self.sync = sync
        self.back = back
        self.whole = visible + front + sync + back

        self.cnt_width = self.whole.bit_length()

    def global_last(self):
        return self.whole - 1

    def is_visible(self, global_pos):
        return global_pos < self.visible

    def visible_pos(self, global_pos):
        return global_pos

    def gen_sync(self, global_pos):
        return not (
            self.visible + self.front
            <= global_pos
            < (self.visible + self.front + self.sync)
        )


class VgaSpec:
    def __init__(self, horizontal: VgaTiming, vertical: VgaTiming, freq):
        self.horizontal = horizontal
        self.vertical = vertical
        self.freq = freq


class VgaScreen:
    def _run(self):
        @std.sequential(self.clk, self.reset)
        def proc_draw():
            if self._is_visible:
                for elem in self.elems:
                    if elem.active():
                        elem.draw(self.rgb)
                        break
                else:
                    self.rgb <<= self.background
            else:
                # draw region outside visible range in black
                self.rgb <<= Rgb.black()

    def __init__(
        self,
        clk,
        reset,
        rgb: Rgb,
        hs: Signal[Bit],
        vs: Signal[Bit],
        spec: VgaSpec,
        background: Rgb = Rgb.white(),
    ):
        self.clk = clk
        self.reset = reset
        self.rgb = rgb
        self.hs = hs
        self.vs = vs
        self.h = spec.horizontal
        self.v = spec.vertical
        self.background = background

        self.x = Signal[Unsigned[spec.horizontal.cnt_width]](0)
        self.y = Signal[Unsigned[spec.vertical.cnt_width]](0)

        self.elems: list[VgaElem] = []
        self._is_visible = Signal[bool](False)

        global_x = Signal[Unsigned[spec.horizontal.cnt_width]](0)
        global_y = Signal[Unsigned[spec.vertical.cnt_width]](0)

        @std.sequential(clk, reset)
        def proc_vga():
            if global_x == self.h.global_last():
                global_x.next = 0

                if global_y == self.v.global_last():
                    global_y.next = 0
                else:
                    global_y.next = global_y + 1
            else:
                global_x.next = global_x + 1

        @std.concurrent
        def proc_vga():
            self.x <<= self.h.visible_pos(global_x)
            self.y <<= self.v.visible_pos(global_y)
            self.hs <<= self.h.gen_sync(global_x)
            self.vs <<= self.v.gen_sync(global_y)

            self._is_visible <<= self.h.is_visible(global_x) and self.v.is_visible(
                global_y
            )

        cohdl.on_block_exit(self._run)

    def add_elem(self, elem: VgaElem):
        self.elems.append(elem)


class VgaElem:
    def __init__(self, screen: VgaScreen):
        self.screen = screen
        screen.add_elem(self)

    def active(self):
        return False

    def draw(self, rgb):
        pass


class VgaWindow(VgaElem):
    def __init__(
        self,
        screen: VgaScreen,
        offset_x,
        offset_y,
        width,
        height,
        background: Rgb = Rgb.black(),
    ):
        super().__init__(screen)

        self.x = Signal[Unsigned[11]]()
        self.y = Signal[Unsigned[11]]()
        self.is_active = Signal[bool](False)
        self.background = background

        @std.concurrent
        def logic():
            self.x <<= screen.x - offset_x
            self.y <<= screen.y - offset_y
            self.is_active <<= (offset_x <= screen.x < (offset_x + width)) and (
                offset_y <= screen.y < (offset_y + height)
            )

    def active(self):
        return self.is_active

    def draw(self, rgb):
        rgb <<= self.background


#
#
#
#
#


VGA_640_480 = VgaSpec(
    VgaTiming(
        visible=640,
        front=16,
        sync=96,
        back=48,
    ),
    VgaTiming(
        front=10,
        visible=480,
        sync=2,
        back=33,
    ),
    freq=25.175,
)

XGA_1024_768 = VgaSpec(
    VgaTiming(
        visible=1024,
        front=24,
        sync=136,
        back=160,
    ),
    VgaTiming(
        visible=768,
        front=3,
        sync=6,
        back=29,
    ),
    freq=65,
)

SVGA_800_600 = VgaSpec(
    VgaTiming(
        visible=800,
        front=24,
        sync=72,
        back=128,
    ),
    VgaTiming(
        visible=600,
        front=1,
        sync=2,
        back=22,
    ),
    freq=36,
)
