"""Public, sanitized error types."""


class PlanSealError(Exception):
    """An expected fail-closed validation error."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code
