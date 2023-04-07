from cohdl_xil._common import Fpga, FpgaPorts, PortCapability, Direction, IoStandard

INPUT = Direction.INPUT
OUTPUT = Direction.OUTPUT
INOUT = Direction.INOUT
IO = IoStandard


@staticmethod
def _pmod_capability(*pins):
    return [PortCapability(pin, [INPUT, OUTPUT], [IO.LVCMOS33]) for pin in pins]


# fmt: off
PORTS = FpgaPorts([
    # Switches
    PortCapability("J15", [INPUT], [IO.LVCMOS33]),
    PortCapability("L16", [INPUT], [IO.LVCMOS33]),
    PortCapability("M13", [INPUT], [IO.LVCMOS33]),
    PortCapability("R15", [INPUT], [IO.LVCMOS33]),
    PortCapability("R17", [INPUT], [IO.LVCMOS33]),
    PortCapability("T18", [INPUT], [IO.LVCMOS33]),
    PortCapability("U18", [INPUT], [IO.LVCMOS33]),
    PortCapability("R13", [INPUT], [IO.LVCMOS33]),
    PortCapability("T8" , [INPUT], [IO.LVCMOS18, IO.LVCMOS33]),
    PortCapability("U8" , [INPUT], [IO.LVCMOS18, IO.LVCMOS33]),
    PortCapability("R16", [INPUT], [IO.LVCMOS33]),
    PortCapability("T13", [INPUT], [IO.LVCMOS33]),
    PortCapability("H6" , [INPUT], [IO.LVCMOS33]),
    PortCapability("U12", [INPUT], [IO.LVCMOS33]),
    PortCapability("U11", [INPUT], [IO.LVCMOS33]),
    PortCapability("V10", [INPUT], [IO.LVCMOS33]),

    # LEDS
    PortCapability("H17", [OUTPUT], [IO.LVCMOS33]),
    PortCapability("K15", [OUTPUT], [IO.LVCMOS33]),
    PortCapability("J13", [OUTPUT], [IO.LVCMOS33]),
    PortCapability("N14", [OUTPUT], [IO.LVCMOS33]),
    PortCapability("R18", [OUTPUT], [IO.LVCMOS33]),
    PortCapability("V17", [OUTPUT], [IO.LVCMOS33]),
    PortCapability("U17", [OUTPUT], [IO.LVCMOS33]),
    PortCapability("U16", [OUTPUT], [IO.LVCMOS33]),
    PortCapability("V16", [OUTPUT], [IO.LVCMOS33]),
    PortCapability("T15", [OUTPUT], [IO.LVCMOS33]),
    PortCapability("U14", [OUTPUT], [IO.LVCMOS33]),
    PortCapability("T16", [OUTPUT], [IO.LVCMOS33]),
    PortCapability("V15", [OUTPUT], [IO.LVCMOS33]),
    PortCapability("V14", [OUTPUT], [IO.LVCMOS33]),
    PortCapability("V12", [OUTPUT], [IO.LVCMOS33]),
    PortCapability("V11", [OUTPUT], [IO.LVCMOS33]),

    # RGB LEDs
    # RGB 1
    PortCapability("N15", [OUTPUT], [IO.LVCMOS33]),
    PortCapability("M16", [OUTPUT], [IO.LVCMOS33]),
    PortCapability("R12", [OUTPUT], [IO.LVCMOS33]),

    # RGB 2
    PortCapability("N16", [OUTPUT], [IO.LVCMOS33]),
    PortCapability("R11", [OUTPUT], [IO.LVCMOS33]),
    PortCapability("G14", [OUTPUT], [IO.LVCMOS33]),

    # seven segment displays
    # cathodes
    PortCapability("T10", [OUTPUT], [IO.LVCMOS33]),
    PortCapability("R10", [OUTPUT], [IO.LVCMOS33]),
    PortCapability("K16", [OUTPUT], [IO.LVCMOS33]),
    PortCapability("K13", [OUTPUT], [IO.LVCMOS33]),
    PortCapability("P15", [OUTPUT], [IO.LVCMOS33]),
    PortCapability("T11", [OUTPUT], [IO.LVCMOS33]),
    PortCapability("L18", [OUTPUT], [IO.LVCMOS33]),
    PortCapability("H15", [OUTPUT], [IO.LVCMOS33]),

    # anodes
    PortCapability("J17", [OUTPUT], [IO.LVCMOS33]),
    PortCapability("J18", [OUTPUT], [IO.LVCMOS33]),
    PortCapability("T9" , [OUTPUT], [IO.LVCMOS33]),
    PortCapability("J14", [OUTPUT], [IO.LVCMOS33]),
    PortCapability("P14", [OUTPUT], [IO.LVCMOS33]),
    PortCapability("T14", [OUTPUT], [IO.LVCMOS33]),
    PortCapability("K2" , [OUTPUT], [IO.LVCMOS33]),
    PortCapability("U13", [OUTPUT], [IO.LVCMOS33]),

    # reset button
    PortCapability("C12", [INPUT], [IO.LVCMOS33]),

    # buttons
    PortCapability("N17", [INPUT], [IO.LVCMOS33]),
    PortCapability("M18", [INPUT], [IO.LVCMOS33]),
    PortCapability("P17", [INPUT], [IO.LVCMOS33]),
    PortCapability("M17", [INPUT], [IO.LVCMOS33]),
    PortCapability("P18", [INPUT], [IO.LVCMOS33]),

    # uart
    PortCapability("C4", [INPUT] , [IO.LVCMOS33]),
    PortCapability("D4", [OUTPUT], [IO.LVCMOS33]),
    #uart_cts     = PortConfiguration("D3", OUTPUT, IO.LVCMOS33)
    #uart_rts     = PortConfiguration("E5", INPUT , IO.LVCMOS33)

    # vga
    PortCapability("A3", [OUTPUT], [IO.LVCMOS33]),
    PortCapability("B4", [OUTPUT], [IO.LVCMOS33]),
    PortCapability("C5", [OUTPUT], [IO.LVCMOS33]),
    PortCapability("A4", [OUTPUT], [IO.LVCMOS33]),
    PortCapability("C6", [OUTPUT], [IO.LVCMOS33]),
    PortCapability("A5", [OUTPUT], [IO.LVCMOS33]),
    PortCapability("B6", [OUTPUT], [IO.LVCMOS33]),
    PortCapability("A6", [OUTPUT], [IO.LVCMOS33]),
    PortCapability("B7", [OUTPUT], [IO.LVCMOS33]),
    PortCapability("C7", [OUTPUT], [IO.LVCMOS33]),
    PortCapability("D7", [OUTPUT], [IO.LVCMOS33]),
    PortCapability("D8", [OUTPUT], [IO.LVCMOS33]),
    PortCapability("B11", [OUTPUT], [IO.LVCMOS33]),
    PortCapability("B12", [OUTPUT], [IO.LVCMOS33]),

    # ps2
    PortCapability("F4", [INOUT], [IO.LVCMOS33]),
    PortCapability("B2", [INOUT], [IO.LVCMOS33]),

    # PMOD

    *_pmod_capability("C17","D18","E18","G17","D17","E17","F18","G18"),
    *_pmod_capability("D14","F16","G16","H14","E16","F13","G13","H16"),

    # clock
    PortCapability("E3", [INPUT], [IO.LVCMOS33])
])

# fmt: on


class Artix7(Fpga):
    ports = PORTS

    def __init__(self, build_dir, *, top_entity="Artix7_TopEntity"):
        PART_ID = "xc7a100tcsg324-1"
        super().__init__(build_dir, part_id=PART_ID, top_entity=top_entity)
