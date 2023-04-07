import enum
from cohdl import Port, Bit, BitVector, Signal
from cohdl import std

from cohdl_xil import ip_block

Axi4Light = std.axi.axi4_light.Axi4Light


class Parity(enum.Enum):
    NO_PARITY = enum.auto()
    EVEN = enum.auto()
    ODD = enum.auto()

    def config_str(self):
        return {Parity.NO_PARITY: "No_Parity", Parity.EVEN: "Even", Parity.ODD: "Odd"}[
            self
        ]


Parity_ = Parity


class AxiUartlite:
    Parity = Parity_

    supported_baud = [
        110,
        300,
        1200,
        2400,
        4800,
        9600,
        19200,
        38400,
        57600,
        115200,
        128000,
        230400,
    ]

    def __init__(
        self,
        clk: std.Clock,
        reset: std.Reset,
        rx: Signal[Bit],
        tx: Signal[Bit],
        *,
        baud: int = 115200,
        parity: Parity = Parity.NO_PARITY,
        data_bits: int = 8,
    ):
        freq_mhz = clk.frequency().megahertz()

        assert 10 <= freq_mhz <= 300
        assert baud in self.supported_baud
        assert 5 <= data_bits <= 8

        ports = {
            "s_axi_aclk": Port.input(Bit),
            "s_axi_aresetn": Port.input(Bit),
            "interrupt": Port.output(Bit),
            "s_axi_awaddr": Port.input(BitVector[4]),
            "s_axi_awvalid": Port.input(Bit),
            "s_axi_awready": Port.output(Bit),
            "s_axi_wdata": Port.input(BitVector[32]),
            "s_axi_wstrb": Port.input(BitVector[4]),
            "s_axi_wvalid": Port.input(Bit),
            "s_axi_wready": Port.output(Bit),
            "s_axi_bresp": Port.output(BitVector[2]),
            "s_axi_bvalid": Port.output(Bit),
            "s_axi_bready": Port.input(Bit),
            "s_axi_araddr": Port.input(BitVector[4]),
            "s_axi_arvalid": Port.input(Bit),
            "s_axi_arready": Port.output(Bit),
            "s_axi_rdata": Port.output(BitVector[32]),
            "s_axi_rresp": Port.output(BitVector[2]),
            "s_axi_rvalid": Port.output(Bit),
            "s_axi_rready": Port.input(Bit),
            "rx": Port.input(Bit),
            "tx": Port.output(Bit),
        }

        ip = ip_block(
            name="axi_uartlite",
            vendor="xilinx.com",
            library="ip",
            version="2.0",
            module_name="ip_axi_uartlite",
            properties={
                "CONFIG.C_BAUDRATE": str(baud),
                "CONFIG.PARITY": parity.config_str(),
                "CONFIG.C_DATA_BITS": str(data_bits),
                "CONFIG.C_S_AXI_ACLK_FREQ_HZ_d": str(freq_mhz),
            },
            ports=ports,
        )

        axi = Axi4Light.signal(
            clk,
            reset.active_low_signal(),
            addr_width=4,
            data_width=32,
            prot_width=None,
            resp_width=2,
            strb_width=4,
        )

        self.axi = axi
        self.interrupt = Signal[Bit]()

        connected = {
            "s_axi_aclk": clk.signal(),
            "s_axi_aresetn": reset.active_low_signal(),
            "interrupt": self.interrupt,
            "s_axi_awaddr": axi.wraddr.awaddr,
            "s_axi_awvalid": axi.wraddr.valid,
            "s_axi_awready": axi.wraddr.ready,
            "s_axi_wdata": axi.wrdata.wdata,
            "s_axi_wstrb": axi.wrdata.wstrb,
            "s_axi_wvalid": axi.wrdata.valid,
            "s_axi_wready": axi.wrdata.ready,
            "s_axi_bresp": axi.wrresp.bresp,
            "s_axi_bvalid": axi.wrresp.valid,
            "s_axi_bready": axi.wrresp.ready,
            "s_axi_araddr": axi.rdaddr.araddr,
            "s_axi_arvalid": axi.rdaddr.valid,
            "s_axi_arready": axi.rdaddr.ready,
            "s_axi_rdata": axi.rddata.rdata,
            "s_axi_rresp": axi.rddata.rresp,
            "s_axi_rvalid": axi.rddata.valid,
            "s_axi_rready": axi.rddata.ready,
            "rx": rx,
            "tx": tx,
        }

        ip(**connected)
