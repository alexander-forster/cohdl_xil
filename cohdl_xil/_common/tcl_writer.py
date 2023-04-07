class TclWriter:
    def __init__(self):
        self.lines = []

    def write_comment(self, comment: str):
        self.lines.append(f"# {comment}")

    def write_line(self, line: str = ""):
        self.lines.append(line)

    def write_cmd(self, command: str, *args, **kwargs):
        self.lines.append(
            " ".join(
                [
                    command,
                    *args,
                    *[f"-{name} {value}" for name, value in kwargs.items()],
                ]
            )
            + ";"
        )

    def print(self, file=None):
        for line in self.lines:
            print(line, file=file)

    def write_string(self) -> str:
        return "\n".join(self.lines)
