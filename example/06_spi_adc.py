from cohdl import Signal, Unsigned, Null, BitVector, Bit

from cohdl import std

from cohdl_xil.boards.trenz import NexysA7

board = NexysA7("build", top_entity_name="ExampleSpiEntity")


def seven_seg(inp: Unsigned[4]):
    bv = std.as_bitvector

    return std.reverse_bits(
        ~std.select(
            inp.unsigned,
            {
                0: bv("1111110"),
                1: bv("0110000"),
                2: bv("1101101"),
                3: bv("1111001"),
                4: bv("0110011"),
                5: bv("1011011"),
                6: bv("1011111"),
                7: bv("1110000"),
                8: bv("1111111"),
                9: bv("1111011"),
                10: bv("1110111"),
                11: bv("0011111"),
                12: bv("1001110"),
                13: bv("0111101"),
                14: bv("1001111"),
                15: bv("1000111"),
            },
            default=bv("1111111"),
        )
    )


@board.architecture
def architecture():
    ctx = std.Context(
        clk=board.clock(), reset=std.Reset(board.btn_reset(positive_logic=True))
    )

    led = board.leds()
    acc = board.accelerometer()
    sseg = board.seven_segment()

    spi = std.spi.SpiMaster(ctx, acc.spi, clk_frequency=std.MHz(1))

    acc_data = Signal[BitVector[32]](Null)

    @ctx
    async def proc_disp():
        # load current accelerometer data into a shift register
        shift = std.OutShiftRegister(acc_data)
        anodes = Signal[Unsigned[8]](1)

        while not shift.empty():
            sseg.cathodes <<= Bit(1) @ seven_seg(shift.shift(4))
            sseg.anodes <<= ~anodes
            anodes <<= anodes << 1
            await std.wait_for(std.ms(1))

    @ctx
    async def proc_acc():
        # enable measurement by writing to register
        await spi.transaction(Unsigned[24](0x0A_2D_02))

        # update accelerometer every 100ms
        while True:
            await std.wait_for(std.ms(100))

            # read from measurement registers
            data = await spi.transaction(Unsigned[16](0x0B_08), 24)
            acc_data[23:0] <<= data
            led.next = data[15:0]
