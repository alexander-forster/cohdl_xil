from __future__ import annotations

import cohdl
from cohdl import Port, Bit, Signal, Block
from cohdl_xil._common import IpBase
from cohdl import std

from dataclasses import dataclass


class FloatRange:
    @staticmethod
    def filter_overlapping(first: list[FloatRange], *rest: list[FloatRange]):
        if len(rest) == 0:
            return first

        second, *rest = rest

        result = []

        for elem_first in first:
            for elem_snd in second:
                overlapp = elem_first.overlapp(elem_snd)
                if overlapp is not None:
                    result.append(overlapp)

        return FloatRange.filter_overlapping(result, *rest)

    @staticmethod
    def from_error(value, error):
        return FloatRange(value - value * error, value + value * error)

    def __init__(self, lower, upper):
        self.lower = lower
        self.upper = upper

    def overlapp(self, other: FloatRange):
        if self.upper < other.lower or self.lower > other.upper:
            return None

        return FloatRange(max(self.lower, other.lower), min(self.upper, other.upper))

    def midpoint(self):
        return (self.lower + self.upper) / 2

    def __contains__(self, value):
        return self.lower <= value <= self.upper

    def __lt__(self, other):
        if isinstance(other, FloatRange):
            return self.upper < other.lower
        return self.upper < other

    def __gt__(self, other):
        if isinstance(other, FloatRange):
            return self.lower > other.upper
        return self.lower > other

    def __mul__(self, factor):
        if isinstance(factor, FloatRange):
            return FloatRange(self.lower * factor.lower, self.upper * factor.upper)
        return FloatRange(self.lower * factor, self.upper * factor)

    def __truediv__(self, other):
        return FloatRange(self.lower / other, self.upper / other)


class _MmcmImpl:
    def __init__(
        self,
        clk: std.Clock,
        reset: std.Reset,
        locked: Signal[Bit],
        mult: float,
        div: int,
    ):
        self.ip = IpBase(
            name="clk_wiz",
            vendor="xilinx.com",
            library="ip",
            version="6.0",
            module_name="clk_wiz_0",
        )

        freq_mhz = clk.frequency().megahertz()
        period = 1 / freq_mhz * 1000

        self._outcnt = 0

        self._freq_int = freq_mhz * mult / div
        self._mult = mult
        self._div = div
        self._locked = locked

        self.ip.set_property("CONFIG.PRIM_IN_FREQ", str(freq_mhz))
        self.ip.set_property("CONFIG.MMCM_CLKIN1_PERIOD", str(period))
        self.ip.set_property("CONFIG.MMCM_CLKFBOUT_MULT_F", str(mult))
        self.ip.set_property("CONFIG.MMCM_DIVCLK_DIVIDE", str(div))

        self.ip.add_port(Port.input(Bit, name="clk_in1"), clk.signal())
        self.ip.add_port(Port.input(Bit, name="reset"), reset.active_high_signal())
        self.ip.add_port(Port.output(Bit, name="locked"), locked)

    def instantiate(self):
        self.ip.instantiate()

    def reserve_output(self, divide, signal=None):
        self._outcnt += 1

        if self._outcnt > 1:
            self.ip.set_property(f"CONFIG.CLKOUT{self._outcnt}_USED", "true")

        self.ip.set_property("CONFIG.NUM_OUT_CLKS", str(self._outcnt))

        if self._outcnt == 1:
            self.ip.set_property("CONFIG.MMCM_CLKOUT0_DIVIDE_F", str(divide))
        else:
            self.ip.set_property(
                f"CONFIG.MMCM_CLKOUT{self._outcnt-1}_DIVIDE", str(divide)
            )

        freq = self._freq_int / divide
        self.ip.set_property(
            f"CONFIG.CLKOUT{self._outcnt}_REQUESTED_OUT_FREQ", str(freq)
        )

        if signal is None:
            signal = Signal[Bit](name=f"mmcm_out_{self._outcnt}")

        self.ip.add_port(Port.output(Bit, name=f"clk_out{self._outcnt}"), signal)

        return std.Clock(signal)


class Mmcm:
    @dataclass
    class OutputInfo:
        frequency: FloatRange
        signal: Signal[Bit]
        possible_div: list[float]

        def possible_f_int(self):
            return [self.frequency * div for div in self.possible_div]

    def _instantiate(self):
        if len(self._output_info) == 0:
            print("MMCM not instantiated because no outputs are used")
            return

        freq = self.clk.frequency().megahertz()

        possible_f_int = FloatRange.filter_overlapping(
            *[o.possible_f_int() for o in self._output_info]
        )

        assert len(possible_f_int) != 0, "could not reach requested output frequencies"

        def find_m_d():
            for f_int in possible_f_int:
                quot = f_int / freq

                for d in range(1, 107):
                    m = round(quot.midpoint() * d * 8) / 8

                    if m < 2:
                        continue
                    if m > 64:
                        break

                    if m * d in quot:
                        return f_int.midpoint(), m, d
            raise AssertionError("could not reach requested output frequencies")

        f_int, m, d = find_m_d()

        mmcm = _MmcmImpl(self.clk, self.reset, self._locked, m, d)

        for o in self._output_info:
            freq = o.frequency.midpoint()
            div = round(f_int / freq * 8) / 8
            mmcm.reserve_output(div, o.signal)

        mmcm.instantiate()

    def __init__(self, clk: std.Clock, reset: std.Reset):
        self.clk = clk
        self.reset = reset
        self._output_info: list[Mmcm.OutputInfo] = []
        self._cnt = 0
        self._locked = Signal[Bit](name="locked")

        cohdl.on_block_exit(self._instantiate)

    def locked(self):
        return self._locked

    def reserve(self, frequency: std.Frequency, allowed_error=0):
        assert isinstance(frequency, std.Frequency)

        frequency_mhz = frequency.megahertz()

        assert (
            4.687 <= frequency_mhz <= 800.000
        ), f"frequency {frequency_mhz} MHz outside allowed range [4.687 MHz - 800.000 MHz]"

        self._cnt += 1
        assert self._cnt <= 7, "maximum output clock cnt reached"

        if self._cnt == 1:
            possible_div = [x / 8 for x in range(8, 1024)]
        else:
            possible_div = [*range(1, 128)]

        signal = Signal[Bit]()
        self._output_info.append(
            Mmcm.OutputInfo(
                FloatRange.from_error(frequency_mhz, allowed_error),
                signal,
                possible_div,
            )
        )
        return std.Clock(signal, frequency=frequency_mhz * 1e6)
