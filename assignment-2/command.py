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

    def __init__(self, cmd: CommandType, term: int, **kwargs):
        self.cmd = cmd
        self.term = term

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

    def cmd_to_pb2(self) -> str:
        """Command to string. no term"""
        if self.cmd == CommandType.NOOP:
            return f"{self.cmd.value}"
        if self.cmd == CommandType.SET:
            return f"{self.cmd.value} {self.key} {self.value}"
        return ""
    
    @classmethod
    def cmd_from_pb2(cls, msg: str, term: int):
        """Returns command from pb2 message"""
        words = msg.split(" ")
        cmd_type = Command.command_type_from_str(words[0])
        if cmd_type == CommandType.NOOP:
            return Command(cmd_type, term)
        if cmd_type == CommandType.SET:
            return Command(cmd_type, term, key=words[1], value=words[2])
        return None

    @staticmethod
    def command_type_from_str(type_str: str) -> CommandType:
        """Returns CommandType from string"""
        return list(filter(lambda x : x.value == type_str, CommandType))[0]
