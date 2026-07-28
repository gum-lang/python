class GumDecodeError(Exception):
    """Exception raised when parsing or tokenizing gum markup fails."""

    def __init__(self, msg: str, lineno: int, colno: int) -> None:
        self.msg = msg
        self.lineno = lineno
        self.colno = colno
        self.message = msg
        self.line = lineno
        self.col = colno
        super().__init__(self._format_message())

    def _format_message(self) -> str:
        return f"{self.msg} (line {self.lineno}, column {self.colno})"


GumError = GumDecodeError
