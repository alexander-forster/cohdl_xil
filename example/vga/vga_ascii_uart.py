from cohdl import Signal, Unsigned, BitVector, Bit

from cohdl import std

from cohdl_xil.boards.trenz import NexysA7

from cohdl_xil.ip.mmcm import Mmcm
from cohdl_xil.ip.axi_uartlite import AxiUartlite
from example.vga.vga_impl.vga import VgaScreen, Rgb, XGA_1024_768
from example.vga.vga_impl.vga_text import AsciiWindow, FileFont

board = NexysA7(top_entity_name="ExampleVga")


@board.architecture
def architecture():
    # reserve ports
    clk_board = board.clock()
    reset = std.Reset(board.btn_reset(positive_logic=True))

    # board.vga returns a Python class containing
    # the sync and color signals of the VGA interface
    # of the board
    vga = board.vga()

    # defines width, height and signal timing
    # of the VGA interface
    VGA_SPEC = XGA_1024_768

    # use xilinx mixed mode clock manager ip
    # to create a clock according to the selected VGA specification
    mmcm = Mmcm(clk_board, reset)
    clk = mmcm.reserve(VGA_SPEC.freq, allowed_error=0.0001)

    # the VgaScreen class generates the vga color and sync
    # signals according to the selected VGA specification
    screen = VgaScreen(
        clk,
        reset,
        Rgb(vga.r, vga.g, vga.b),
        vga.hs,
        vga.vs,
        VGA_SPEC,
    )

    # define a font for the VGA screen by reading
    # bit patterns from a file
    vga_font = FileFont("example/vga/vga_impl/FONTS/ISO.F16", 16)

    lines = 16
    columns = 32
    characters = lines * columns

    # create a window of ascii text on the screen
    vga_window = AsciiWindow(
        screen,
        line_cnt=lines,
        column_cnt=columns,
        font=vga_font,
    )

    # the axi uart ip core is used to receive data
    uart = AxiUartlite(
        clk,
        reset,
        board.uart_in(),
        board.uart_out(),
    )

    # signals used to transfer data received from uart
    # to VGA screen
    new_data_available = Signal[Bit](False)
    new_data = Signal[BitVector[32]]()

    @std.sequential(clk, reset)
    async def proc_uart_rx():
        # read the status register
        status, _ = await uart.axi.read_word(8)

        # when data is available
        if status[0]:
            # read one character from the receive fifo
            # and write it to the new_data Signal
            received_data, received_resp = await uart.axi.read_word(0)
            new_data_available.push = True
            new_data.next = received_data

    @std.sequential(clk, reset)
    def proc_write_text(
        char_cnt=Signal[Unsigned.upto(characters - 1)](0),
    ):
        # when new data is available update one character of
        # the VGA screen and increment the letter index
        if new_data_available:
            vga_window.set_letter(char_cnt, new_data[7:0])
            char_cnt.next = char_cnt + 1

    @std.sequential(clk, reset)
    async def proc_uart_tx():
        # write receive data back
        if new_data_available:
            await uart.axi.write_word(4, new_data)
