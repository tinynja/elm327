"""A scriptable, in-memory ELM327 emulator for unit tests.

It runs synchronously: every complete command written by the host is answered immediately, so
tests are deterministic and need no threads or sleeps.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from elm327.transport import LoopbackTransport


@dataclass
class FakeState:
    echo: bool = True
    linefeeds: bool = True
    spaces: bool = True
    headers: bool = False


@dataclass
class FakeELM327:
    """Emulates the command interpreter of an ELM327.

    Attributes:
        version: Reported firmware version.
        voltage: Value returned by ``ATRV``.
        replies: Scripted replies keyed by normalised command (upper case, no spaces). They take
            precedence over the built-in behaviour.
        silent: When true, the device never answers (simulates a wrong port or baud rate).
        monitoring: When true, the device behaves as if running ``ATMA``: the next byte received
            stops it with ``STOPPED`` and is otherwise ignored.
        received: Every complete command received, in order.
    """

    version: str = "v1.5"
    voltage: float = 12.6
    supports_describe: bool = True
    replies: dict[str, list[str]] = field(default_factory=dict)
    silent: bool = False
    monitoring: bool = False
    state: FakeState = field(default_factory=FakeState)
    received: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.transport = LoopbackTransport(on_write=self._on_write)
        self._line = bytearray()
        self._last = ""

    # ------------------------------------------------------------------ host -> device

    def _on_write(self, data: bytes) -> None:
        if self.silent:
            return
        for byte in data:
            if self.monitoring:
                self.monitoring = False
                self._send_reply(["STOPPED"])
                continue
            if byte == ord("\r"):
                command = self._line.decode("ascii")
                self._line.clear()
                self._process(command)
            else:
                self._line.append(byte)

    def _process(self, command: str) -> None:
        self.received.append(command)
        echo = self.state.echo  # captured first: ATE0 itself is still echoed
        lines = self.handle(command)
        self._send_reply(lines, echo=command if echo else None)

    def _send_reply(self, lines: list[str], echo: str | None = None) -> None:
        eol = "\r\n" if self.state.linefeeds else "\r"
        text = "" if echo is None else echo + eol
        text += "".join(line + eol for line in lines) + eol + ">"
        self.transport.feed(text.encode("ascii"))

    # ------------------------------------------------------------------ interpreter

    def handle(self, command: str) -> list[str]:
        key = command.replace(" ", "").upper()
        if not key:
            key = self._last
        self._last = key
        if key in self.replies:
            return self.replies[key]
        if not key.startswith("AT"):
            return ["NO DATA"]
        return self._handle_at(key[2:])

    def _handle_at(self, at: str) -> list[str]:
        if at in {"Z", "WS"}:
            self.state = FakeState()
            return ["", f"ELM327 {self.version}"]
        if at == "I":
            return [f"ELM327 {self.version}"]
        if at == "@1":
            return ["OBDII to RS232 Interpreter"] if self.supports_describe else ["?"]
        if at == "RV":
            return [f"{self.voltage:.1f}V"]
        switches = {"E": "echo", "L": "linefeeds", "S": "spaces", "H": "headers"}
        if len(at) == 2 and at[0] in switches and at[1] in "01":
            setattr(self.state, switches[at[0]], at[1] == "1")
            return ["OK"]
        return ["?"]
