"""
Command
"""
import enum


class CommandType(enum.Enum):
    """Command Types"""

    NOOP = "NO-OP"
    SET = "SET"


class Command:
    """Command"""

    def __init__(self, cmd: CommandType, **kwargs):
        self.cmd = cmd
        if "term" in kwargs.items():
            self.term = kwargs["term"]

        if self.cmd == CommandType.SET:
            self.key = kwargs["key"]
            self.value = kwargs["value"]

    def set_term(self, term: int):
        """Sets/Updates term number"""
        self.term = term

    def __str__(self):
        if self.cmd == CommandType.NOOP:
            return f"{self.cmd.value} {self.term}"
        if self.cmd == CommandType.SET:
            return f"{self.cmd.value} {self.key} {self.value} {self.term}"
        return ""
