class FontReader:
    def __init__(self, filename, height):
        self.width = 8
        self.height = height

        self.letters = []

        with open(filename, "+rb") as file:
            raw = file.read()
            assert len(raw) == self.height * 256

            def bytes_to_bits(bytes: bytes):
                return "".join(("00000000" + bin(b)[2:])[-8:] for b in bytes)

            self.letters = [
                bytes_to_bits(raw[i * height : i * height + height]) for i in range(256)
            ]

    def array_def(self):
        return [l[::-1] for l in self.letters]

    def show(self, letter: str):
        assert len(letter) == 1
        s = self.letters[ord(letter)]

        for i in range(self.height):
            line = s[i * self.width : i * self.width + self.width]
            print(line)
