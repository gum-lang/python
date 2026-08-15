class GumDecodeError(Exception):
    """Exception raised when parsing or tokenizing gum markup fails.

    Provides line and column information for error reporting.
    Error messages follow the format: "{message} (line {line}, column {col})"

    Attributes:
        msg: The error message without position information.
        lineno: The line number where the error occurred (1-indexed).
        colno: The column number where the error occurred (1-indexed).
        message: Alias for msg (for backward compatibility).
        line: Alias for lineno (for backward compatibility).
        col: Alias for colno (for backward compatibility).

    Example:
        >>> try:
        ...     gum.loads('key = "unterminated')
        ... except GumDecodeError as e:
        ...     print(f"Error at line {e.line}, column {e.col}: {e.msg}")
    """

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
