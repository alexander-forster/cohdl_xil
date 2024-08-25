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
        self.spi = std.spi.Spi(sclk=sclk, mosi=mosi, miso=miso, chip_select=cs)
        self.int_1 = int_1
        self.int_2 = int_2


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
        self.ui_ctx = std.SequentialContext(
            std.Clock(signals.ui_clk, frequency=ui_frequency),
            std.Reset(signals.ui_clk_sync_rst, active_low=False),
        )

    async def read_data(self, addr) -> BitVector[128]:
        signals = self.signals
        line_addr = addr.msb(rest=4) @ std.zeros(4)

        signals.app_cmd <<= self.CMD_READ
        signals.app_addr <<= line_addr
        signals.app_en <<= True

        await signals.app_rdy
        signals.app_en <<= False
        await signals.app_rd_data_valid
        return signals.app_rd_data.copy()

    async def write_data(self, addr, data: BitVector[128], mask=Null):
        assert data.width == 128
        signals = self.signals

        signals.app_wdf_mask <<= mask
        signals.app_wdf_data <<= data
        signals.app_wdf_wren <<= True
        signals.app_wdf_end <<= True
        await signals.app_wdf_rdy
        signals.app_wdf_wren <<= False
        signals.app_wdf_end <<= False

        line_addr = addr.msb(rest=4) @ std.zeros(4)

        signals.app_cmd <<= self.CMD_WRITE
        signals.app_addr <<= line_addr
        signals.app_en <<= True
        await signals.app_rdy
        signals.app_en <<= False


from cohdl.std.bitfield import Field, BitField


class SynchronizedMemoryInterface:
    def __init__(
        self,
        interface: DDR2_UserInterface,
        sys_ctx: std.SequentialContext,
        request_ctx: std.SequentialContext | None = None,
    ):
        from cohdl_xil.ip.fifo import IndependentClkFifo

        class Request(std.Record):
            is_write: Bit
            addr: BitVector[27]
            mask: BitVector[16]

        self._Request = Request

        if request_ctx is None:
            request_ctx = sys_ctx

        self.interface = interface
        self.ui_ctx = self.interface.ui_ctx

        self.ADDR_WIDTH = interface.signals.app_addr.width

        self.req_box = std.Mailbox[BitVector[128]](delay=3)
        self.resp_box = std.Mailbox[BitVector[128]](delay=3)

        self.data_buffer = Signal[BitVector[128]](Null)

        @self.ui_ctx
        async def proc_ui_interface():
            req = std.from_bits[Request](
                (await self.req_box.receive()).lsb(std.count_bits(Request)),
                qualifier=Signal,
            )

            if req.is_write:
                data = await self.req_box.receive()
                await interface.write_data(req.addr, data, req.mask)

            else:
                resp = await interface.read_data(req.addr)
                self.resp_box.send(resp)

    async def write(self, addr, data, mask):
        req = self._Request(is_write=Bit(1), addr=addr, mask=mask)
        data_buffer = Signal(data)

        self.req_box.send(std.leftpad(std.to_bits(req), 128))
        await self.req_box.is_clear()
        self.req_box.send(data_buffer)
        await self.req_box.is_clear()

    async def read(self, addr):
        req = self._Request(is_write=Bit(0), addr=addr, mask=Null)
        self.req_box.send(std.leftpad(std.to_bits(req), 128))
        return await self.resp_box.receive()


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

    # ddr2 memory

    ddr2_ports = Ddr2Memory(
        ddr2_dq=PortConfiguration(None, INOUT, None),
        ddr2_dqs_n=PortConfiguration(None, INOUT, None),
        ddr2_dqs_p=PortConfiguration(None, INOUT, None),


        ddr2_addr  = PortConfiguration(None, OUTPUT, None),
        ddr2_ba    = PortConfiguration(None, OUTPUT, None),
        ddr2_ras_n = PortConfiguration(None, OUTPUT, None),
        ddr2_cas_n = PortConfiguration(None, OUTPUT, None),
        ddr2_we_n  = PortConfiguration(None, OUTPUT, None),
        ddr2_ck_p  = PortConfiguration(None, OUTPUT, None),
        ddr2_ck_n  = PortConfiguration(None, OUTPUT, None),
        ddr2_cke   = PortConfiguration(None, OUTPUT, None),
        ddr2_cs_n  = PortConfiguration(None, OUTPUT, None),
        ddr2_dm    = PortConfiguration(None, OUTPUT, None),
        ddr2_odt   = PortConfiguration(None, OUTPUT, None)
    )

    # ethernet
    
    ethernet = EthernetCon(
        mdio        = PortConfiguration("A9",   INPUT, IO.LVCMOS33),
        mdc         = PortConfiguration("C9",  OUTPUT, IO.LVCMOS33),
        reset       = PortConfiguration("B3",  OUTPUT, IO.LVCMOS33),
        rxd1        = PortConfiguration("D10",  INPUT, IO.LVCMOS33),
        rxd0        = PortConfiguration("C11",  INPUT, IO.LVCMOS33),
        rxerr       = PortConfiguration("C10",  INPUT, IO.LVCMOS33),
        txd0        = PortConfiguration("A10", OUTPUT, IO.LVCMOS33),
        txd1        = PortConfiguration("A8",  OUTPUT, IO.LVCMOS33),
        txen        = PortConfiguration("B9",  OUTPUT, IO.LVCMOS33),
        crsdv       = PortConfiguration("D9",   INPUT, IO.LVCMOS33),
        int         = PortConfiguration("B8",   INPUT, IO.LVCMOS33),
        clk         = PortConfiguration("D5",  OUTPUT, IO.LVCMOS33)
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

        self.fpga.constraints().add_tcl_lines(
            "set_property CFGBVS VCCO [current_design]",
            "set_property CONFIG_VOLTAGE 3.3 [current_design]",
        )

    def board_context(self):
        return std.SequentialContext(self.clock(), self.reset())

    def clock(self):
        return self.fpga.reserve_clock("board_clk", PinMapping.clock, 10.0)
        ### Clock signal
        # set_property -dict { PACKAGE_PIN E3    IOSTANDARD LVCMOS33 } [get_ports { CLK100MHZ }]; #IO_L12P_T1_MRCC_35 Sch=clk100mhz
        # create_clock -add -name sys_clk_pin -period 10.00 -waveform {0 5} [get_ports {CLK100MHZ}];

    def reset(self):
        return std.Reset(self.btn_reset(), active_low=True)

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

    def pmod_pin(self, connector: str, nr: int, direction: Direction = INPUT):
        return self.fpga.reserve_port(
            f"pmod_{connector}_{nr}",
            cohdl.Bit,
            PinMapping.pmod(connector, direction)[nr],
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

    def ethernet(self):
        pm = PinMapping.ethernet

        return EthernetCon(
            mdio=self.fpga.reserve_port("eth_mdio", cohdl.Bit, pm.mdio),
            mdc=self.fpga.reserve_port("eth_mdc", cohdl.Bit, pm.mdc),
            reset=self.fpga.reserve_port("eth_reset", cohdl.Bit, pm.reset),
            rxd1=self.fpga.reserve_port("eth_rxd1", cohdl.Bit, pm.rxd1),
            rxd0=self.fpga.reserve_port("eth_rxd0", cohdl.Bit, pm.rxd0),
            rxerr=self.fpga.reserve_port("eth_rxerr", cohdl.Bit, pm.rxerr),
            txd0=self.fpga.reserve_port("eth_txd0", cohdl.Bit, pm.txd0),
            txd1=self.fpga.reserve_port("eth_txd1", cohdl.Bit, pm.txd1),
            txen=self.fpga.reserve_port("eth_txen", cohdl.Bit, pm.txen),
            crsdv=self.fpga.reserve_port("eth_crsdv", cohdl.Bit, pm.crsdv),
            int=self.fpga.reserve_port("eth_int_refclk0", cohdl.Bit, pm.int),
            clk=self.fpga.reserve_port("eth_clk", cohdl.Bit, pm.clk),
        )

    def ddr2_memory(self, ctx_system: std.SequentialContext, zero_unused_ports=True):
        from cohdl import Port, Bit, BitVector

        assert ctx_system.clk().frequency() == std.MHz(200)

        properties = {
            "CONFIG.ARESETN.INSERT_VIP": "0",
            "CONFIG.BOARD_MIG_PARAM": "Custom",
            "CONFIG.C0_ARESETN.INSERT_VIP": "0",
            "CONFIG.C0_CLOCK.INSERT_VIP": "0",
            "CONFIG.C0_DDR2_RESET.INSERT_VIP": "0",
            "CONFIG.C0_DDR3_RESET.INSERT_VIP": "0",
            "CONFIG.C0_LPDDR2_RESET.INSERT_VIP": "0",
            "CONFIG.C0_MMCM_CLKOUT0.INSERT_VIP": "0",
            "CONFIG.C0_MMCM_CLKOUT1.INSERT_VIP": "0",
            "CONFIG.C0_MMCM_CLKOUT2.INSERT_VIP": "0",
            "CONFIG.C0_MMCM_CLKOUT3.INSERT_VIP": "0",
            "CONFIG.C0_MMCM_CLKOUT4.INSERT_VIP": "0",
            "CONFIG.C0_QDRIIP_RESET.INSERT_VIP": "0",
            "CONFIG.C0_RESET.INSERT_VIP": "0",
            "CONFIG.C0_RLDIII_RESET.INSERT_VIP": "0",
            "CONFIG.C0_RLDII_RESET.INSERT_VIP": "0",
            "CONFIG.C0_SYS_CLK_I.INSERT_VIP": "0",
            "CONFIG.C1_ARESETN.INSERT_VIP": "0",
            "CONFIG.C1_CLOCK.INSERT_VIP": "0",
            "CONFIG.C1_DDR2_RESET.INSERT_VIP": "0",
            "CONFIG.C1_DDR3_RESET.INSERT_VIP": "0",
            "CONFIG.C1_LPDDR2_RESET.INSERT_VIP": "0",
            "CONFIG.C1_MMCM_CLKOUT0.INSERT_VIP": "0",
            "CONFIG.C1_MMCM_CLKOUT1.INSERT_VIP": "0",
            "CONFIG.C1_MMCM_CLKOUT2.INSERT_VIP": "0",
            "CONFIG.C1_MMCM_CLKOUT3.INSERT_VIP": "0",
            "CONFIG.C1_MMCM_CLKOUT4.INSERT_VIP": "0",
            "CONFIG.C1_QDRIIP_RESET.INSERT_VIP": "0",
            "CONFIG.C1_RESET.INSERT_VIP": "0",
            "CONFIG.C1_RLDIII_RESET.INSERT_VIP": "0",
            "CONFIG.C1_RLDII_RESET.INSERT_VIP": "0",
            "CONFIG.C1_SYS_CLK_I.INSERT_VIP": "0",
            "CONFIG.C2_ARESETN.INSERT_VIP": "0",
            "CONFIG.C2_CLOCK.INSERT_VIP": "0",
            "CONFIG.C2_DDR2_RESET.INSERT_VIP": "0",
            "CONFIG.C2_DDR3_RESET.INSERT_VIP": "0",
            "CONFIG.C2_LPDDR2_RESET.INSERT_VIP": "0",
            "CONFIG.C2_MMCM_CLKOUT0.INSERT_VIP": "0",
            "CONFIG.C2_MMCM_CLKOUT1.INSERT_VIP": "0",
            "CONFIG.C2_MMCM_CLKOUT2.INSERT_VIP": "0",
            "CONFIG.C2_MMCM_CLKOUT3.INSERT_VIP": "0",
            "CONFIG.C2_MMCM_CLKOUT4.INSERT_VIP": "0",
            "CONFIG.C2_QDRIIP_RESET.INSERT_VIP": "0",
            "CONFIG.C2_RESET.INSERT_VIP": "0",
            "CONFIG.C2_RLDIII_RESET.INSERT_VIP": "0",
            "CONFIG.C2_RLDII_RESET.INSERT_VIP": "0",
            "CONFIG.C2_SYS_CLK_I.INSERT_VIP": "0",
            "CONFIG.C3_ARESETN.INSERT_VIP": "0",
            "CONFIG.C3_CLOCK.INSERT_VIP": "0",
            "CONFIG.C3_DDR2_RESET.INSERT_VIP": "0",
            "CONFIG.C3_DDR3_RESET.INSERT_VIP": "0",
            "CONFIG.C3_LPDDR2_RESET.INSERT_VIP": "0",
            "CONFIG.C3_MMCM_CLKOUT0.INSERT_VIP": "0",
            "CONFIG.C3_MMCM_CLKOUT1.INSERT_VIP": "0",
            "CONFIG.C3_MMCM_CLKOUT2.INSERT_VIP": "0",
            "CONFIG.C3_MMCM_CLKOUT3.INSERT_VIP": "0",
            "CONFIG.C3_MMCM_CLKOUT4.INSERT_VIP": "0",
            "CONFIG.C3_QDRIIP_RESET.INSERT_VIP": "0",
            "CONFIG.C3_RESET.INSERT_VIP": "0",
            "CONFIG.C3_RLDIII_RESET.INSERT_VIP": "0",
            "CONFIG.C3_RLDII_RESET.INSERT_VIP": "0",
            "CONFIG.C3_SYS_CLK_I.INSERT_VIP": "0",
            "CONFIG.C4_ARESETN.INSERT_VIP": "0",
            "CONFIG.C4_CLOCK.INSERT_VIP": "0",
            "CONFIG.C4_DDR2_RESET.INSERT_VIP": "0",
            "CONFIG.C4_DDR3_RESET.INSERT_VIP": "0",
            "CONFIG.C4_LPDDR2_RESET.INSERT_VIP": "0",
            "CONFIG.C4_MMCM_CLKOUT0.INSERT_VIP": "0",
            "CONFIG.C4_MMCM_CLKOUT1.INSERT_VIP": "0",
            "CONFIG.C4_MMCM_CLKOUT2.INSERT_VIP": "0",
            "CONFIG.C4_MMCM_CLKOUT3.INSERT_VIP": "0",
            "CONFIG.C4_MMCM_CLKOUT4.INSERT_VIP": "0",
            "CONFIG.C4_QDRIIP_RESET.INSERT_VIP": "0",
            "CONFIG.C4_RESET.INSERT_VIP": "0",
            "CONFIG.C4_RLDIII_RESET.INSERT_VIP": "0",
            "CONFIG.C4_RLDII_RESET.INSERT_VIP": "0",
            "CONFIG.C4_SYS_CLK_I.INSERT_VIP": "0",
            "CONFIG.C5_ARESETN.INSERT_VIP": "0",
            "CONFIG.C5_CLOCK.INSERT_VIP": "0",
            "CONFIG.C5_DDR2_RESET.INSERT_VIP": "0",
            "CONFIG.C5_DDR3_RESET.INSERT_VIP": "0",
            "CONFIG.C5_LPDDR2_RESET.INSERT_VIP": "0",
            "CONFIG.C5_MMCM_CLKOUT0.INSERT_VIP": "0",
            "CONFIG.C5_MMCM_CLKOUT1.INSERT_VIP": "0",
            "CONFIG.C5_MMCM_CLKOUT2.INSERT_VIP": "0",
            "CONFIG.C5_MMCM_CLKOUT3.INSERT_VIP": "0",
            "CONFIG.C5_MMCM_CLKOUT4.INSERT_VIP": "0",
            "CONFIG.C5_QDRIIP_RESET.INSERT_VIP": "0",
            "CONFIG.C5_RESET.INSERT_VIP": "0",
            "CONFIG.C5_RLDIII_RESET.INSERT_VIP": "0",
            "CONFIG.C5_RLDII_RESET.INSERT_VIP": "0",
            "CONFIG.C5_SYS_CLK_I.INSERT_VIP": "0",
            "CONFIG.C6_ARESETN.INSERT_VIP": "0",
            "CONFIG.C6_CLOCK.INSERT_VIP": "0",
            "CONFIG.C6_DDR2_RESET.INSERT_VIP": "0",
            "CONFIG.C6_DDR3_RESET.INSERT_VIP": "0",
            "CONFIG.C6_LPDDR2_RESET.INSERT_VIP": "0",
            "CONFIG.C6_MMCM_CLKOUT0.INSERT_VIP": "0",
            "CONFIG.C6_MMCM_CLKOUT1.INSERT_VIP": "0",
            "CONFIG.C6_MMCM_CLKOUT2.INSERT_VIP": "0",
            "CONFIG.C6_MMCM_CLKOUT3.INSERT_VIP": "0",
            "CONFIG.C6_MMCM_CLKOUT4.INSERT_VIP": "0",
            "CONFIG.C6_QDRIIP_RESET.INSERT_VIP": "0",
            "CONFIG.C6_RESET.INSERT_VIP": "0",
            "CONFIG.C6_RLDIII_RESET.INSERT_VIP": "0",
            "CONFIG.C6_RLDII_RESET.INSERT_VIP": "0",
            "CONFIG.C6_SYS_CLK_I.INSERT_VIP": "0",
            "CONFIG.C7_ARESETN.INSERT_VIP": "0",
            "CONFIG.C7_CLOCK.INSERT_VIP": "0",
            "CONFIG.C7_DDR2_RESET.INSERT_VIP": "0",
            "CONFIG.C7_DDR3_RESET.INSERT_VIP": "0",
            "CONFIG.C7_LPDDR2_RESET.INSERT_VIP": "0",
            "CONFIG.C7_MMCM_CLKOUT0.INSERT_VIP": "0",
            "CONFIG.C7_MMCM_CLKOUT1.INSERT_VIP": "0",
            "CONFIG.C7_MMCM_CLKOUT2.INSERT_VIP": "0",
            "CONFIG.C7_MMCM_CLKOUT3.INSERT_VIP": "0",
            "CONFIG.C7_MMCM_CLKOUT4.INSERT_VIP": "0",
            "CONFIG.C7_QDRIIP_RESET.INSERT_VIP": "0",
            "CONFIG.C7_RESET.INSERT_VIP": "0",
            "CONFIG.C7_RLDIII_RESET.INSERT_VIP": "0",
            "CONFIG.C7_RLDII_RESET.INSERT_VIP": "0",
            "CONFIG.C7_SYS_CLK_I.INSERT_VIP": "0",
            "CONFIG.CLK_REF_I.INSERT_VIP": "0",
            "CONFIG.CLOCK.INSERT_VIP": "0",
            "CONFIG.DDR2_RESET.INSERT_VIP": "0",
            "CONFIG.DDR3_RESET.INSERT_VIP": "0",
            "CONFIG.LPDDR2_RESET.INSERT_VIP": "0",
            "CONFIG.MIG_DONT_TOUCH_PARAM": "Custom",
            "CONFIG.MMCM_CLKOUT0.INSERT_VIP": "0",
            "CONFIG.MMCM_CLKOUT1.INSERT_VIP": "0",
            "CONFIG.MMCM_CLKOUT2.INSERT_VIP": "0",
            "CONFIG.MMCM_CLKOUT3.INSERT_VIP": "0",
            "CONFIG.MMCM_CLKOUT4.INSERT_VIP": "0",
            "CONFIG.QDRIIP_RESET.INSERT_VIP": "0",
            "CONFIG.RESET.INSERT_VIP": "0",
            "CONFIG.RESET_BOARD_INTERFACE": "Custom",
            "CONFIG.RLDIII_RESET.INSERT_VIP": "0",
            "CONFIG.RLDII_RESET.INSERT_VIP": "0",
            "CONFIG.S0_AXI.INSERT_VIP": "0",
            "CONFIG.S0_AXI_CTRL.INSERT_VIP": "0",
            "CONFIG.S1_AXI.INSERT_VIP": "0",
            "CONFIG.S1_AXI_CTRL.INSERT_VIP": "0",
            "CONFIG.S2_AXI.INSERT_VIP": "0",
            "CONFIG.S2_AXI_CTRL.INSERT_VIP": "0",
            "CONFIG.S3_AXI.INSERT_VIP": "0",
            "CONFIG.S3_AXI_CTRL.INSERT_VIP": "0",
            "CONFIG.S4_AXI.INSERT_VIP": "0",
            "CONFIG.S4_AXI_CTRL.INSERT_VIP": "0",
            "CONFIG.S5_AXI.INSERT_VIP": "0",
            "CONFIG.S5_AXI_CTRL.INSERT_VIP": "0",
            "CONFIG.S6_AXI.INSERT_VIP": "0",
            "CONFIG.S6_AXI_CTRL.INSERT_VIP": "0",
            "CONFIG.S7_AXI.INSERT_VIP": "0",
            "CONFIG.S7_AXI_CTRL.INSERT_VIP": "0",
            "CONFIG.SYSTEM_RESET.INSERT_VIP": "0",
            "CONFIG.SYS_CLK_I.INSERT_VIP": "0",
            "CONFIG.S_AXI.INSERT_VIP": "0",
            "CONFIG.S_AXI_CTRL.INSERT_VIP": "0",
        }

        ports = {
            "ddr2_dq": Port.inout(BitVector[16]),
            "ddr2_dqs_p": Port.inout(BitVector[2]),
            "ddr2_dqs_n": Port.inout(BitVector[2]),
            "ddr2_addr": Port.output(BitVector[13]),
            "ddr2_ba": Port.output(BitVector[3]),
            "ddr2_ras_n": Port.output(Bit),
            "ddr2_cas_n": Port.output(Bit),
            "ddr2_we_n": Port.output(Bit),
            "ddr2_ck_p": Port.output(BitVector[1]),
            "ddr2_ck_n": Port.output(BitVector[1]),
            "ddr2_cke": Port.output(BitVector[1]),
            "ddr2_cs_n": Port.output(BitVector[1]),
            "ddr2_dm": Port.output(BitVector[2]),
            "ddr2_odt": Port.output(BitVector[1]),
            "app_addr": Port.input(BitVector[27]),
            "app_cmd": Port.input(BitVector[3]),
            "app_en": Port.input(Bit),
            "app_wdf_data": Port.input(BitVector[128]),
            "app_wdf_end": Port.input(Bit),
            "app_wdf_mask": Port.input(BitVector[16]),
            "app_wdf_wren": Port.input(Bit),
            "app_rd_data": Port.output(BitVector[128]),
            "app_rd_data_end": Port.output(Bit),
            "app_rd_data_valid": Port.output(Bit),
            "app_rdy": Port.output(Bit),
            "app_wdf_rdy": Port.output(Bit),
            "app_sr_req": Port.input(Bit),
            "app_ref_req": Port.input(Bit),
            "app_zq_req": Port.input(Bit),
            "app_sr_active": Port.output(Bit),
            "app_ref_ack": Port.output(Bit),
            "app_zq_ack": Port.output(Bit),
            "ui_clk": Port.output(Bit),
            "ui_clk_sync_rst": Port.output(Bit),
            "init_calib_complete": Port.output(Bit),
            "sys_clk_i": Port.input(Bit),
            "sys_rst": Port.input(Bit),
        }

        from cohdl_xil.ip.mig import mig
        from pathlib import Path

        with open(Path(__file__).parent / "nexys_a7_dep" / "default_mig.prj") as file:
            prj_file_content = file.read()

        pins = PinMapping.ddr2_ports
        reserve = self.fpga.reserve_port

        signals = {}

        def reserve(name, type):
            config: Ddr2Memory = getattr(pins, name)
            signals[name] = self.fpga.reserve_port(name, type, config)

        reserve("ddr2_dq", BitVector[16])
        reserve("ddr2_dqs_p", BitVector[2])
        reserve("ddr2_dqs_n", BitVector[2])
        reserve("ddr2_addr", BitVector[13])
        reserve("ddr2_ba", BitVector[3])
        reserve("ddr2_ras_n", Bit)
        reserve("ddr2_cas_n", Bit)
        reserve("ddr2_we_n", Bit)
        reserve("ddr2_ck_p", BitVector[1])
        reserve("ddr2_ck_n", BitVector[1])
        reserve("ddr2_cke", BitVector[1])
        reserve("ddr2_cs_n", BitVector[1])
        reserve("ddr2_dm", BitVector[2])
        reserve("ddr2_odt", BitVector[1])

        with std.prefix("ddr2ui"):
            n = std.name
            interface = DDR2_UserInterfaceSignals(
                app_addr=Signal[BitVector[27]](name=n("addr")),
                app_cmd=Signal[BitVector[3]](name=n("cmd")),
                app_en=Signal[Bit](name=n("en")),
                app_wdf_data=Signal[BitVector[128]](name=n("wdf_data")),
                app_wdf_end=Signal[Bit](name=n("wdf_end")),
                app_wdf_mask=Signal[BitVector[16]](name=n("wdf_mask")),
                app_wdf_wren=Signal[Bit](name=n("wdf_wren")),
                app_rd_data=Signal[BitVector[128]](name=n("rd_data")),
                app_rd_data_end=Signal[Bit](name=n("rd_data_end")),
                app_rd_data_valid=Signal[Bit](name=n("rd_data_valid")),
                app_rdy=Signal[Bit](name=n("rdy")),
                app_wdf_rdy=Signal[Bit](name=n("wdf_rdy")),
                app_sr_req=Signal[Bit](name=n("sr_req")),
                app_ref_req=Signal[Bit](name=n("ref_req")),
                app_zq_req=Signal[Bit](name=n("zq_req")),
                app_sr_active=Signal[Bit](name=n("sr_active")),
                app_ref_ack=Signal[Bit](name=n("ref_ack")),
                app_zq_ack=Signal[Bit](name=n("zq_ack")),
                ui_clk=Signal[Bit](name=n("clk")),
                ui_clk_sync_rst=Signal[Bit](name=n("clk_sync_rst")),
                init_calib_complete=Signal[Bit](name=n("init_calib_complete")),
                sys_clk_i=ctx_system.clk().signal(),
                sys_rst=ctx_system.reset().active_low_signal(),
            )

        signals.update(interface.__dict__)

        mig(
            prj_file_content=prj_file_content,
            properties=properties,
            ports=ports,
            signals=signals,
        )

        result = DDR2_UserInterface(interface, ui_frequency=std.MHz(75))

        if zero_unused_ports:
            std.concurrent_assign(result.signals.app_sr_req, Null)
            std.concurrent_assign(result.signals.app_ref_req, Null)
            std.concurrent_assign(result.signals.app_zq_req, Null)

        return result

    def synchronized_dd2_access(
        self,
        system_ctx: std.SequentialContext,
        req_ctx: std.SequentialContext | None = None,
        zero_unused_ports=True,
    ):
        return SynchronizedMemoryInterface(
            self.ddr2_memory(system_ctx, zero_unused_ports=zero_unused_ports),
            system_ctx,
            req_ctx,
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
