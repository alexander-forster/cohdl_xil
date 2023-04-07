from cohdl import std

from cohdl_xil.boards.trenz import NexysA7
from cohdl_xil.ip.axi_uartlite import AxiUartlite

board = NexysA7("build", top_entity_name="ExampleIpEntity")

# this example implements a uart echo design using the xilinx
# axi uart ip block and the experimental cohdl builtin axi module


@board.architecture
def architecture():
    # reserve clock and reset ports
    clk = board.clock()
    reset = std.Reset(board.btn_reset(), active_low=True)

    # reserve the uart ports of the board
    rx = board.uart_in()
    tx = board.uart_out()

    # instantiate the Xilinx axi_uartlite ip core
    # configured with a baud rate of 115200 and no parity
    uart = AxiUartlite(
        clk,
        reset,
        rx,
        tx,
        baud=115200,
        parity=AxiUartlite.Parity.NO_PARITY,
    )

    # use the read_word and write_word coroutine methods to perform
    # axi reads and writes to the axi_uartlite ip core.
    @std.sequential(clk, reset)
    async def proc_uart_echo():
        # read the status register at address 8
        status, _ = await uart.axi.read_word(8)

        # when new data is available read one character
        # from the receive fifo at address 0 and
        # send it back by writing to address 4
        #
        # Note that this is just an example to demonstrate
        # how CoHDL coroutines can wrap axi transactions in reusable
        # methods. In a real design the write part part should be
        # placed in a separate sequential context so sending
        # and receiving can happen in parallel.
        if status[0]:
            received_data, received_resp = await uart.axi.read_word(0)
            await uart.axi.write_word(4, received_data)
