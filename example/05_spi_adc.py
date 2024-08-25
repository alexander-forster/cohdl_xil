from cohdl import Unsigned, Null

from cohdl import std

from cohdl_xil.boards.trenz import NexysA7

board = NexysA7("build", top_entity_name="ExampleSpiEntity")


@board.architecture
def architecture():
    ctx = std.SequentialContext(
        clk=board.clock(), reset=std.Reset(board.btn_reset(positive_logic=True))
    )

    led = board.leds()

    acc = board.accelerometer()

    spi = std.spi.SpiMaster(ctx, acc.spi, clk_frequency=std.MHz(1))

    @ctx
    async def proc_acc():
        await std.wait_for(std.ms(500))
        led[7:0] <<= await spi.transaction(Unsigned[16](0x0B00), 8)

        await std.wait_for(std.ms(500))
        led[15:8] <<= await spi.transaction(Unsigned[16](0x0B01), 8)

        await std.wait_for(std.ms(500))
        led.next = Null
