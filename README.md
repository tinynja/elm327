# elm327

A typed, dependency-light Python library to connect to, configure and talk to **ELM327** OBD-II/CAN adapters over USB, Bluetooth or Wi-Fi, with first-class support for bus monitoring (`ATMA`).

> **Status:** pre-alpha. The connection, command/response and configuration core is in place; monitoring and CAN filtering are next. The API may change until 1.0.

## Installation

```bash
pip install elm327
```

Requires Python 3.11+. The only runtime dependency is [pyserial](https://pypi.org/project/pyserial/).

## Quick start

```python
from elm327 import ELM327

# USB / Bluetooth SPP: "/dev/ttyUSB0", "/dev/rfcomm0", "COM3"
# Wi-Fi adapters:      "tcp://192.168.0.10:35000"
with ELM327.open("/dev/ttyUSB0", baudrate=38400) as elm:
    print(elm.version)  # e.g. "1.5"
    print(elm.read_voltage())  # e.g. 12.6
    print(elm.send("0100"))  # raw OBD request -> ["4100BE3EB813"]
```

Errors reported by the adapter become exceptions: `NoDataError`, `UnsupportedCommandError` (`?`), `BufferFullError`, `CanBusError` and more, all deriving from `ELM327Error`.

## Connection URLs

| URL | Transport |
| --- | --- |
| `/dev/ttyUSB0`, `COM3`, `serial:///dev/rfcomm0?baudrate=115200` | Serial port (USB, Bluetooth SPP) |
| any [pyserial URL](https://pyserial.readthedocs.io/en/latest/url_handlers.html), e.g. `rfc2217://host:port` | Serial via pyserial handler |
| `tcp://192.168.0.10:35000` | Wi-Fi adapter (raw TCP) |

## Development

See [CONTRIBUTING.md](CONTRIBUTING.md). In short:

```bash
uv sync
uv run pytest --cov
```

## License

[MIT](LICENSE)
