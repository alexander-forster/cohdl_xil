from cohdl import Signal, Unsigned, Bit
from cohdl import std

from cohdl_xil.boards.trenz import NexysA7
from cohdl_xil.ip.ila import ila

board = NexysA7("build", top_entity_name="ExampleIpEntity")

# with the submodule ip, cohdl_xil provides
# methods to instantiate xilinx ip cores
# this example demonstrates this by using
# an integrated logic analyzer


@board.architecture
def architecture():
    # use the methods of board to reserve
    # ports used by this design
    clk = board.clock()
    sw = board.switches()
    led = board.leds()

    # define local signals
    cnt = Signal[Unsigned[16]]()
    cnt_zero = Signal[Bit]()

    @std.sequential(clk)
    def proc_counter():
        cnt.next = cnt + 1

    @std.concurrent
    def logic():
        led.next = cnt
        cnt_zero.next = cnt == 0

    # use an ila ip block to monitor the signals
    ila(
        # the ila ip block requires a clock signal
        clk,
        dict(
            # Probes are defined using a dictionary.
            # The ila function automatically configures the ip
            # block with the correct number of probes and sets
            # their width to match the width of the given signals.
            # The left hand side of the keyword argument defines
            # the name that will show up in the ila window.
            counter=cnt,
            all_sw=sw,
            # single bit signals are converted to bitvectors
            # internally and forwarded to the ip block
            cnt_zero=cnt_zero,
        ),
    )
