from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import cohdl
from cohdl import Signal, Bit, BitVector, Port, Null
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
        self.spi: std.spi.Spi
        self.int_1: Signal[Bit]
        self.int_2: Signal[Bit]

@dataclass
class Ddr2Memory:
    ddr2_dq: Port[BitVector[16], Port.Direction.INOUT]
    ddr2_dqs_p: Port[BitVector[2], Port.Direction.INOUT]
    ddr2_dqs_n: Port[BitVector[2], Port.Direction.INOUT]
    ddr2_addr: Port[BitVector[13], Port.Direction.OUTPUT]
    ddr2_ba: Port[BitVector[3], Port.Direction.OUTPUT]
    ddr2_ras_n: Port[Bit, Port.Direction.OUTPUT]
    ddr2_cas_n: Port[Bit, Port.Direction.OUTPUT]
    ddr2_we_n: Port[Bit, Port.Direction.OUTPUT]
    ddr2_ck_p: Port[BitVector[1], Port.Direction.OUTPUT]
    ddr2_ck_n: Port[BitVector[1], Port.Direction.OUTPUT]
    ddr2_cke: Port[BitVector[1], Port.Direction.OUTPUT]
    ddr2_cs_n: Port[BitVector[1], Port.Direction.OUTPUT]
    ddr2_dm: Port[BitVector[2], Port.Direction.OUTPUT]
    ddr2_odt: Port[BitVector[1], Port.Direction.OUTPUT]

@dataclass
class DDR2_UserInterfaceSignals:
    app_addr: Signal[BitVector[27]]
    app_cmd: Signal[BitVector[3]]
    app_en: Signal[Bit]
    app_wdf_data: Signal[BitVector[128]]
    app_wdf_end: Signal[Bit]
    app_wdf_mask: Signal[BitVector[16]]
    app_wdf_wren: Signal[Bit]
    app_rd_data: Signal[BitVector[128]]
    app_rd_data_end: Signal[Bit]
    app_rd_data_valid: Signal[Bit]
    app_rdy: Signal[Bit]
    app_wdf_rdy: Signal[Bit]
    app_sr_req: Signal[Bit]
    app_ref_req: Signal[Bit]
    app_zq_req: Signal[Bit]
    app_sr_active: Signal[Bit]
    app_ref_ack: Signal[Bit]
    app_zq_ack: Signal[Bit]
    init_calib_complete: Signal[Bit]
    ui_clk: Signal[Bit]
    ui_clk_sync_rst: Signal[Bit]
    sys_clk_i: Signal[Bit]
    sys_rst: Signal[Bit]

class DDR2_UserInterface:
    CMD_WRITE = std.as_bitvector("000")
    CMD_READ = std.as_bitvector("001")

    def __init__(self, signals: DDR2_UserInterfaceSignals, ui_frequency):
        self.signals = signals
        self.ui_ctx: std.SequentialContext

    async def read_data(self, addr) -> BitVector[128]: ...
    async def write_data(self, addr, data: BitVector[128], mask=Null): ...

class SynchronizedMemoryInterface:
    def __init__(
        self,
        interface: DDR2_UserInterface,
        sys_ctx: std.SequentialContext,
        request_ctx: std.SequentialContext | None = None,
    ): ...
    async def write(self, addr, data, mask): ...
    async def read(self, addr) -> BitVector: ...

@dataclass
class EthernetCon:
    mdio: Bit
    mdc: Bit
    reset: Bit

    rxd0: Bit
    rxd1: Bit
    rxerr: Bit

    txd0: Bit
    txd1: Bit
    txen: Bit

    crsdv: Bit
    int: Bit

    clk: Bit

class NexysA7:
    def __init__(
        self, build_dir: str = "build", *, top_entity_name="NexysA7_TopEntity"
    ):
        self.fpga: Artix7

    def board_context(self) -> std.SequentialContext: ...
    def clock(self) -> std.Clock: ...
    def reset(self) -> std.Reset: ...
    def switches(self) -> Signal[BitVector[16]]: ...
    def leds(self) -> Signal[BitVector[16]]: ...
    def rgb_1(self) -> RGB: ...
    def rgb_2(self) -> RGB: ...
    def seven_segment(self, positive_logic: bool = False) -> SevenSegment: ...
    def btn_reset(self, positive_logic: bool = False) -> Signal[Bit]: ...
    def buttons(self) -> Buttons: ...
    def vga(self) -> Vga: ...
    def ps2(self) -> Ps2: ...
    def pmod(
        self, connector: str, direction: Direction = INPUT
    ) -> Signal[BitVector[8]]: ...
    def pmod_pin(
        self, connector: str, nr: int, direction: Direction = INPUT
    ) -> Signal[Bit]: ...
    def uart_in(self) -> Signal[Bit]: ...
    def uart_out(self) -> Signal[Bit]: ...
    def accelerometer(self) -> Accelerometer: ...
    def ethernet(self) -> EthernetCon: ...
    def ddr2_memory(
        self, ctx_system: std.SequentialContext, zero_unused_ports=True
    ) -> DDR2_UserInterface: ...
    def synchronized_dd2_access(
        self,
        system_ctx: std.SequentialContext,
        req_ctx: std.SequentialContext | None = None,
        zero_unused_ports=True,
    ) -> SynchronizedMemoryInterface: ...
    def architecture_impl(self, fn=None, *, build=True): ...
    def architecture(self, fn=None, *, build=True): ...
    def architecture(self, fn=None, *, build=True): ...
    def build(self): ...
