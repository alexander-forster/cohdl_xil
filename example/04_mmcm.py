from cohdl import Signal, Unsigned

from cohdl import std

from cohdl_xil.boards.trenz import NexysA7
from cohdl_xil.ip.mmcm import Mmcm

board = NexysA7("build", top_entity_name="ExampleIpEntity")

# this example demonstrates a design using
# the xilinx mixed mode clock manager ip


@board.architecture
def architecture():
    clk = board.clock()
    reset = std.Reset(board.btn_reset(positive_logic=True))

    # use xilinx mixed mode clock manager ip
    # to generate a 25MHz and a 150MHz clock from
    # the 100MHz board clock
    mmcm = Mmcm(clk, reset)

    # use the method reserve to get a new clock
    # with the given frequency in MHz
    clk_pll1 = mmcm.reserve(25)
    clk_pll2 = mmcm.reserve(150)

    # define counter signals and increment each
    # every clock cycle of the corresponding clock
    cnt_pll1 = Signal[Unsigned[30]]()
    cnt_pll2 = Signal[Unsigned[30]]()

    @std.sequential(clk_pll1)
    def proc_clk_pll1():
        cnt_pll1.next = cnt_pll1 + 1

    @std.sequential(clk_pll2)
    def proc_clk_pll2():
        cnt_pll2.next = cnt_pll2 + 1

    led = board.leds()

    @std.concurrent
    def logic():
        # display counters on board leds to show difference in clock speed
        # use msbs to slow down counters
        led[7:0] <<= cnt_pll1.msb(8)
        led[15:8] <<= cnt_pll2.msb(8)
