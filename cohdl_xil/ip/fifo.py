from __future__ import annotations

import enum
from cohdl import Port, Bit, BitVector, Signal
from cohdl import std

from cohdl_xil import ip_block


class ReadMode(enum.Enum):
    STANDARD = enum.auto()
    FIRST_WORD_FALLTHROUGH = enum.auto()


_allowed_depth = [
    2**9,
    2**10,
    2**11,
    2**12,
    2**13,
    2**14,
    2**15,
    2**16,
    2**17,
]


def _gen_ip_block(properties: dict[str, str], ports):
    return ip_block(
        name="fifo_generator",
        vendor="xilinx.com",
        library="ip",
        version="13.2",
        module_name="fifo_generator",
        properties=properties,
        ports=ports,
    )


def _gen_common_clk_fifo(
    data_width: int,
    depth: int,
    read_mode=ReadMode.FIRST_WORD_FALLTHROUGH,
):
    assert 1 <= data_width <= 1024, f"data_width {data_width} out of range [1-1024]"
    assert depth in _allowed_depth, f"invalid fifo depth {depth}"

    properties = {
        "CONFIG.Fifo_Implementation": "Common_Clock_Builtin_FIFO",
        "CONFIG.Input_Data_Width": str(data_width),
        "CONFIG.Input_Depth": str(depth),
    }

    ports = {
        "clk": Port.input(Bit),
        "rst": Port.input(Bit),
        "din": Port.input(BitVector[data_width]),
        "wr_en": Port.input(Bit),
        "rd_en": Port.input(Bit),
        "dout": Port.output(BitVector[data_width]),
        "full": Port.output(Bit),
        "empty": Port.output(Bit),
    }

    if read_mode is ReadMode.FIRST_WORD_FALLTHROUGH:
        properties["CONFIG.Performance_Options"] = "First_Word_Fall_Through"

    return _gen_ip_block(
        properties=properties,
        ports=ports,
    )


def _gen_independent_clk_fifo(
    data_width: int,
    depth: int,
    read_freq_mhz: float,
    write_freq_mhz: float,
    read_mode: ReadMode.FIRST_WORD_FALLTHROUGH,
):
    ports = {
        "rst": Port.input(Bit),
        "wr_clk": Port.input(Bit),
        "rd_clk": Port.input(Bit),
        "din": Port.input(BitVector[data_width]),
        "wr_en": Port.input(Bit),
        "rd_en": Port.input(Bit),
        "dout": Port.output(BitVector[data_width]),
        "full": Port.output(Bit),
        "empty": Port.output(Bit),
    }

    properties = {
        "CONFIG.Fifo_Implementation": "Independent_Clocks_Builtin_FIFO",
        "CONFIG.Input_Data_Width": str(data_width),
        "CONFIG.Input_Depth": str(depth),
        "CONFIG.Read_Clock_Frequency": str(read_freq_mhz),
        "CONFIG.Write_Clock_Frequency": str(write_freq_mhz),
    }

    if read_mode is ReadMode.FIRST_WORD_FALLTHROUGH:
        properties["CONFIG.Performance_Options"] = "First_Word_Fall_Through"

    return _gen_ip_block(properties=properties, ports=ports)


class _FifoBase:
    def __init__(
        self,
        data_width: int,
    ):
        self.wr_en = Signal[Bit](False, name="fifo_wr_en")
        self.rd_en = Signal[Bit](False, name="fifo_rd_en")
        self.data_in = Signal[BitVector[data_width]](name="fifo_data_in")
        self.data_out = Signal[BitVector[data_width]](name="fifo_data_out")
        self.full = Signal[Bit](name="fifo_full")
        self.empty = Signal[Bit](name="fifo_empty")

    def is_empty(self):
        return self.empty

    def is_full(self):
        return self.full

    def push_value(self, value):
        self.wr_en ^= True
        self.data_in <<= value

    def pop_value(self):
        self.rd_en ^= True
        return self.data_out


class CommonClkFifo(_FifoBase):
    def __init__(
        self,
        *,
        reset: std.Reset,
        clk: std.Clock,
        data_width: int,
        depth: int,
        read_mode: ReadMode = ReadMode.FIRST_WORD_FALLTHROUGH,
    ) -> None:
        assert clk.is_rising_edge()

        super().__init__(data_width=data_width)

        ip = _gen_common_clk_fifo(
            data_width=data_width, depth=depth, read_mode=read_mode
        )

        self.reset = reset
        self.clk = clk

        ip(
            clk=self.clk.signal(),
            rst=self.reset.active_high_signal(),
            din=self.data_in,
            wr_en=self.wr_en,
            rd_en=self.rd_en,
            dout=self.data_out,
            full=self.full,
            empty=self.empty,
        )


class IndependentClkFifo(_FifoBase):
    def __init__(
        self,
        *,
        reset: std.Reset,
        clk_read: std.Clock,
        clk_write: std.Clock,
        data_width: int,
        depth: int,
        read_mode: ReadMode = ReadMode.FIRST_WORD_FALLTHROUGH,
    ):
        assert clk_read.is_rising_edge()
        assert clk_write.is_rising_edge()

        super().__init__(data_width=data_width)

        ip = _gen_independent_clk_fifo(
            data_width=data_width,
            depth=depth,
            read_freq_mhz=clk_read.frequency().megahertz(),
            write_freq_mhz=clk_write.frequency().megahertz(),
            read_mode=read_mode,
        )

        self.reset = reset
        self.clk_read = clk_read
        self.clk_write = clk_write

        ip(
            wr_clk=self.clk_write.signal(),
            rd_clk=self.clk_read.signal(),
            rst=self.reset.active_high_signal(),
            din=self.data_in,
            wr_en=self.wr_en,
            rd_en=self.rd_en,
            dout=self.data_out,
            full=self.full,
            empty=self.empty,
        )
