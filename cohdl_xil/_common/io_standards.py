import enum


class IoStandard(enum.Enum):
    LVCMOS33 = enum.auto()
    LVCMOS18 = enum.auto()

    def __str__(self):
        return _IoStandardStr[self]


_IoStandardStr = {
    IoStandard.LVCMOS18: "LVCMOS18",
    IoStandard.LVCMOS33: "LVCMOS33",
}
