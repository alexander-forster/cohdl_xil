from cohdl_xil.boards.trenz import NexysA7
from cohdl import std

# the class NexysA7 abstracts the development board
# it provides methods to reserve pins and generates a Makefile
# project that invokes vivado and produces a bitstream
board = NexysA7("build", top_entity_name="ExampleTopEntity")


# define the top level architecture by
# decorating it with board.architecture
@board.architecture
def architecture():
    # FPGA pins are reserved using methods of
    # the board class. In this example the pins connected
    # to the switches and leds are added to the constraints
    # of the generated vivado project.
    sw = board.switches()
    led = board.leds()

    # this simple design only connects leds to switches
    @std.concurrent
    def logic():
        led.next = sw


# structure of the build/ directory

# build/                         : contains
#    Makefile
#    cohdl_make_util.py          : helper functions used by Makefile
#    generated/                  : vhdl/tcl files produced by cohdl_xil
#    output/                     : output generated when running Makefile
