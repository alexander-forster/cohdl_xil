from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import cohdl
from cohdl_xil.fpgas.artix.artix_7 import Artix7
from cohdl_xil._common.fpga import Direction, IoStandard, PortConfiguration

from cohdl import std

INPUT = Direction.INPUT
OUTPUT = Direction.OUTPUT
INOUT = Direction.INOUT
IO = IoStandard


class RGB:
    def __init__(self, red, green, blue):
        self.red = red
        self.green = green
        self.blue = blue


class SevenSegment:
    def __init__(self, cathodes, anodes):
        self.cathodes = cathodes
        self.anodes = anodes

    def enable_display(self, nr: int):
        self.anodes[nr] <<= False

    def disable_display(self, nr: int):
        self.anodes[nr] <<= True

    def set_pattern(self, pattern):
        self.cathodes <<= ~pattern


class Buttons:
    def __init__(self, center, up, down, left, right):
        self.center = center
        self.right = right
        self.down = down
        self.left = left
        self.up = up


class Vga:
    def __init__(self, r, g, b, hs, vs):
        self.r = r
        self.g = g
        self.b = b
        self.hs = hs
        self.vs = vs


class Ps2:
    def __init__(self, clk: cohdl.Signal[cohdl.Bit], data: cohdl.Signal[cohdl.Bit]):
        self.clk = clk
        self.data = data


class Accelerometer:
    @dataclass
    class Connections:
        int_1: Any
        int_2: Any
        mosi: Any
        miso: Any
        cs: Any
        sclk: Any

    def __init__(self, sclk, mosi, miso, cs, int_1, int_2) -> None:
        self.spi = std.spi.Spi(sclk=sclk, mosi=mosi, miso=miso, chip_select=cs)
        self.int_1 = int_1
        self.int_2 = int_2


class PinMapping:
    # fmt: off
    switches = [
        PortConfiguration("J15", INPUT, IO.LVCMOS33),
        PortConfiguration("L16", INPUT, IO.LVCMOS33),
        PortConfiguration("M13", INPUT, IO.LVCMOS33),
        PortConfiguration("R15", INPUT, IO.LVCMOS33),
        PortConfiguration("R17", INPUT, IO.LVCMOS33),
        PortConfiguration("T18", INPUT, IO.LVCMOS33),
        PortConfiguration("U18", INPUT, IO.LVCMOS33),
        PortConfiguration("R13", INPUT, IO.LVCMOS33),
        PortConfiguration("T8" , INPUT, IO.LVCMOS18), # sw[8] and sw[9] require a LVCMOS18
        PortConfiguration("U8" , INPUT, IO.LVCMOS18), # 
        PortConfiguration("R16", INPUT, IO.LVCMOS33),
        PortConfiguration("T13", INPUT, IO.LVCMOS33),
        PortConfiguration("H6" , INPUT, IO.LVCMOS33),
        PortConfiguration("U12", INPUT, IO.LVCMOS33),
        PortConfiguration("U11", INPUT, IO.LVCMOS33),
        PortConfiguration("V10", INPUT, IO.LVCMOS33),
    ]

    leds = [
        PortConfiguration("H17", OUTPUT, IO.LVCMOS33),
        PortConfiguration("K15", OUTPUT, IO.LVCMOS33),
        PortConfiguration("J13", OUTPUT, IO.LVCMOS33),
        PortConfiguration("N14", OUTPUT, IO.LVCMOS33),
        PortConfiguration("R18", OUTPUT, IO.LVCMOS33),
        PortConfiguration("V17", OUTPUT, IO.LVCMOS33),
        PortConfiguration("U17", OUTPUT, IO.LVCMOS33),
        PortConfiguration("U16", OUTPUT, IO.LVCMOS33),
        PortConfiguration("V16", OUTPUT, IO.LVCMOS33),
        PortConfiguration("T15", OUTPUT, IO.LVCMOS33),
        PortConfiguration("U14", OUTPUT, IO.LVCMOS33),
        PortConfiguration("T16", OUTPUT, IO.LVCMOS33),
        PortConfiguration("V15", OUTPUT, IO.LVCMOS33),
        PortConfiguration("V14", OUTPUT, IO.LVCMOS33),
        PortConfiguration("V12", OUTPUT, IO.LVCMOS33),
        PortConfiguration("V11", OUTPUT, IO.LVCMOS33),
    ]

    rgb_1 = RGB(
        red   = PortConfiguration("N15", OUTPUT, IO.LVCMOS33),
        green = PortConfiguration("M16", OUTPUT, IO.LVCMOS33),
        blue  = PortConfiguration("R12", OUTPUT, IO.LVCMOS33),
    )

    rgb_2 = RGB(
        red   = PortConfiguration("N16", OUTPUT, IO.LVCMOS33),
        green = PortConfiguration("R11", OUTPUT, IO.LVCMOS33),
        blue  = PortConfiguration("G14", OUTPUT, IO.LVCMOS33),
    )

    # seven segment
    seven_segment_cathodes = [
        PortConfiguration("T10", OUTPUT, IO.LVCMOS33),
        PortConfiguration("R10", OUTPUT, IO.LVCMOS33),
        PortConfiguration("K16", OUTPUT, IO.LVCMOS33),
        PortConfiguration("K13", OUTPUT, IO.LVCMOS33),
        PortConfiguration("P15", OUTPUT, IO.LVCMOS33),
        PortConfiguration("T11", OUTPUT, IO.LVCMOS33),
        PortConfiguration("L18", OUTPUT, IO.LVCMOS33),
        PortConfiguration("H15", OUTPUT, IO.LVCMOS33),
    ]

    seven_segment_anodes = [
        PortConfiguration("J17", OUTPUT, IO.LVCMOS33),
        PortConfiguration("J18", OUTPUT, IO.LVCMOS33),
        PortConfiguration("T9" , OUTPUT, IO.LVCMOS33),
        PortConfiguration("J14", OUTPUT, IO.LVCMOS33),
        PortConfiguration("P14", OUTPUT, IO.LVCMOS33),
        PortConfiguration("T14", OUTPUT, IO.LVCMOS33),
        PortConfiguration("K2" , OUTPUT, IO.LVCMOS33),
        PortConfiguration("U13", OUTPUT, IO.LVCMOS33),
    ]

    # buttons
    bnt_reset = PortConfiguration("C12", INPUT, IO.LVCMOS33)

    btn_center = PortConfiguration("N17", INPUT, IO.LVCMOS33)
    btn_up     = PortConfiguration("M18", INPUT, IO.LVCMOS33)
    btn_left   = PortConfiguration("P17", INPUT, IO.LVCMOS33)
    btn_right  = PortConfiguration("M17", INPUT, IO.LVCMOS33)
    btn_down   = PortConfiguration("P18", INPUT, IO.LVCMOS33)

    # uart

    ##USB-RS232 Interface

    uart_txd_in  = PortConfiguration("C4", INPUT , IO.LVCMOS33)
    uart_rxd_out = PortConfiguration("D4", OUTPUT, IO.LVCMOS33)
    #uart_cts     = PortConfiguration("D3", OUTPUT, IO.LVCMOS33)
    #uart_rts     = PortConfiguration("E5", INPUT , IO.LVCMOS33)

    # accelerometer

    accelerometer = Accelerometer.Connections(
        int_1=PortConfiguration("B13", INPUT, IO.LVCMOS33),
        int_2=PortConfiguration("C16", INPUT, IO.LVCMOS33),
        mosi=PortConfiguration("F14", OUTPUT, IO.LVCMOS33),
        miso=PortConfiguration("E15", INPUT, IO.LVCMOS33),
        cs=PortConfiguration("D15", OUTPUT, IO.LVCMOS33),
        sclk=PortConfiguration("F15", OUTPUT, IO.LVCMOS33),
    )

    # vga
    vga = Vga(
        r = [
            PortConfiguration("A3", OUTPUT, IO.LVCMOS33),
            PortConfiguration("B4", OUTPUT, IO.LVCMOS33),
            PortConfiguration("C5", OUTPUT, IO.LVCMOS33),
            PortConfiguration("A4", OUTPUT, IO.LVCMOS33),
        ],
        g = [
            
            PortConfiguration("C6", OUTPUT, IO.LVCMOS33),
            PortConfiguration("A5", OUTPUT, IO.LVCMOS33),
            PortConfiguration("B6", OUTPUT, IO.LVCMOS33),
            PortConfiguration("A6", OUTPUT, IO.LVCMOS33),
        ],
        b = [
            PortConfiguration("B7", OUTPUT, IO.LVCMOS33),
            PortConfiguration("C7", OUTPUT, IO.LVCMOS33),
            PortConfiguration("D7", OUTPUT, IO.LVCMOS33),
            PortConfiguration("D8", OUTPUT, IO.LVCMOS33),
        ],
        hs = PortConfiguration("B11", OUTPUT, IO.LVCMOS33),
        vs = PortConfiguration("B12", OUTPUT, IO.LVCMOS33),
    )

    # PS2
    ps2 = Ps2(
        clk  = PortConfiguration("F4", INOUT, IO.LVCMOS33),
        data = PortConfiguration("B2", INOUT, IO.LVCMOS33)
    )

    # PMOD

    @staticmethod
    def _pmod_config(*pins, direction):
        return [PortConfiguration(pin, direction, IO.LVCMOS33) for pin in pins]
    
    @classmethod
    def pmod(cls, connector, direction=INPUT):
        return {
            "A": cls._pmod_config("C17","D18","E18","G17","D17","E17","F18","G18", direction=direction),
            "B": cls._pmod_config("D14","F16","G16","H14","E16","F13","G13","H16", direction=direction),
        }[connector]
        
    # board clock
    clock = PortConfiguration("E3",   INPUT, IO.LVCMOS33)

    # fmt: on


class NexysA7:
    def __init__(
        self, build_dir: str = "build", *, top_entity_name="NexysA7_TopEntity"
    ):
        self.fpga = Artix7(build_dir, top_entity=top_entity_name)

    def clock(self):
        return self.fpga.reserve_clock("board_clk", PinMapping.clock, 10.0)
        ### Clock signal
        # set_property -dict { PACKAGE_PIN E3    IOSTANDARD LVCMOS33 } [get_ports { CLK100MHZ }]; #IO_L12P_T1_MRCC_35 Sch=clk100mhz
        # create_clock -add -name sys_clk_pin -period 10.00 -waveform {0 5} [get_ports {CLK100MHZ}];

    def switches(self):
        assert all(Direction.INPUT is p.direction for p in PinMapping.switches)

        return self.fpga.reserve_port(
            "sw", port_type=cohdl.BitVector[16], config=PinMapping.switches
        )

    def leds(self):
        assert all(Direction.OUTPUT is p.direction for p in PinMapping.leds)

        return self.fpga.reserve_port(
            "led", port_type=cohdl.BitVector[16], config=PinMapping.leds
        )

    def rgb_1(self):
        return RGB(
            red=self.fpga.reserve_port("rgb_1_r", cohdl.Bit, PinMapping.rgb_1.red),
            green=self.fpga.reserve_port("rgb_1_g", cohdl.Bit, PinMapping.rgb_1.green),
            blue=self.fpga.reserve_port("rgb_1_b", cohdl.Bit, PinMapping.rgb_1.blue),
        )

    def rgb_2(self):
        return RGB(
            red=self.fpga.reserve_port("rgb_2_r", cohdl.Bit, PinMapping.rgb_2.red),
            green=self.fpga.reserve_port("rgb_2_g", cohdl.Bit, PinMapping.rgb_2.green),
            blue=self.fpga.reserve_port("rgb_2_b", cohdl.Bit, PinMapping.rgb_2.blue),
        )

    def seven_segment(self, positive_logic: bool = False):
        cathodes = self.fpga.reserve_port(
            "seven_seg_cat", cohdl.BitVector[8], PinMapping.seven_segment_cathodes
        )
        anodes = self.fpga.reserve_port(
            "seven_seg_an", cohdl.BitVector[8], PinMapping.seven_segment_anodes
        )

        if positive_logic:
            assert not cohdl.evaluated()

            inv_cathodes = cohdl.Signal[cohdl.BitVector[8]]()
            inv_anodes = cohdl.Signal[cohdl.BitVector[8]]()

            @cohdl.concurrent_context
            def logic():
                cathodes.next = ~inv_cathodes
                anodes.next = ~inv_anodes

            return SevenSegment(inv_cathodes, inv_anodes)
        else:
            return SevenSegment(cathodes, anodes)

    def btn_reset(self, positive_logic: bool = False):
        btn = self.fpga.reserve_port("btn_reset", cohdl.Bit, PinMapping.bnt_reset)

        if positive_logic:
            inv_btn = cohdl.Signal[cohdl.Bit]()

            @std.concurrent
            def logic():
                inv_btn.next = ~btn

            return inv_btn
        else:
            return btn

    def buttons(self):
        return Buttons(
            center=self.fpga.reserve_port(
                "btn_center", cohdl.Bit, PinMapping.btn_center
            ),
            right=self.fpga.reserve_port("btn_right", cohdl.Bit, PinMapping.btn_right),
            down=self.fpga.reserve_port("btn_down", cohdl.Bit, PinMapping.btn_down),
            left=self.fpga.reserve_port("btn_left", cohdl.Bit, PinMapping.btn_left),
            up=self.fpga.reserve_port("btn_up", cohdl.Bit, PinMapping.btn_up),
        )

    def vga(self):
        return Vga(
            r=self.fpga.reserve_port("vga_r", cohdl.BitVector[4], PinMapping.vga.r),
            g=self.fpga.reserve_port("vga_g", cohdl.BitVector[4], PinMapping.vga.g),
            b=self.fpga.reserve_port("vga_b", cohdl.BitVector[4], PinMapping.vga.b),
            hs=self.fpga.reserve_port("vga_hs", cohdl.Bit, PinMapping.vga.hs),
            vs=self.fpga.reserve_port("vga_vs", cohdl.Bit, PinMapping.vga.vs),
        )

    def ps2(self):
        return Ps2(
            clk=self.fpga.reserve_port("ps2_clk", cohdl.Bit, PinMapping.ps2.clk),
            data=self.fpga.reserve_port("ps2_data", cohdl.Bit, PinMapping.ps2.data),
        )

    def pmod(self, connector: str, direction: Direction = INPUT):
        return self.fpga.reserve_port(
            f"pmod_{connector}",
            cohdl.BitVector[8],
            PinMapping.pmod(connector, direction),
        )

    def uart_in(self):
        return self.fpga.reserve_port("uart_tx_in", cohdl.Bit, PinMapping.uart_txd_in)

    def uart_out(self):
        return self.fpga.reserve_port("uart_rx_out", cohdl.Bit, PinMapping.uart_rxd_out)

    def accelerometer(self):
        pm = PinMapping.accelerometer

        return Accelerometer(
            sclk=self.fpga.reserve_port("acl_sclk", cohdl.Bit, pm.sclk),
            mosi=self.fpga.reserve_port("acl_mosi", cohdl.Bit, pm.mosi),
            miso=self.fpga.reserve_port("acl_miso", cohdl.Bit, pm.miso),
            cs=self.fpga.reserve_port("acl_cs", cohdl.Bit, pm.cs),
            int_1=self.fpga.reserve_port("acl_int_1", cohdl.Bit, pm.int_1),
            int_2=self.fpga.reserve_port("acl_int_2", cohdl.Bit, pm.int_2),
        )

    def architecture_impl(self, fn=None, *, build=True):
        def impl(fn_):
            self.fpga._set_architecture(fn)

            if build:
                self.build()

        if fn is None:
            return impl
        impl(fn)

    def architecture(self, fn=None, *, build=True):
        self.fpga._set_architecture(fn)

    def architecture(self, fn=None, *, build=True):
        if fn is None:

            def helper(fn):
                self.fpga._set_architecture(fn)
                if build:
                    self.build()

        else:
            self.fpga._set_architecture(fn)
            if build:
                self.build()

    def build(self):
        self.fpga.build()


class DutWrapper:
    def __init__(self, dut) -> None:
        self._dut = dut

    def sw(self):
        return self._dut.sw

    def rgb_1(self):
        return RGB(self._dut.rgb_1_r, self._dut.rgb_1_g, self._dut.rgb_1_b)

    def rgb_2(self):
        return RGB(self._dut.rgb_2_r, self._dut.rgb_2_g, self._dut.rgb_2_b)

    def accelerometer(self):
        return Accelerometer.Connections(
            int_1=self._dut.acl_int_1,
            int_2=self._dut.acl_int_2,
            mosi=self._dut.acl_mosi,
            miso=self._dut.acl_miso,
            cs=self._dut.acl_cs,
            sclk=self._dut.acl_sclk,
        )
