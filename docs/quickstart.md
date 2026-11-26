# Quick start

## Install

```bash
pip install elm327
```

## Connect

```python
from elm327 import ELM327

with ELM327.open("/dev/ttyUSB0") as elm:  # or "COM3", "tcp://192.168.0.10:35000"
    print(elm.banner)  # "ELM327 v1.5"
    print(elm.read_voltage())  # 12.6
```

`ELM327.open()` opens the connection, brings the adapter to its prompt (even if a previous program
left it monitoring the bus), resets it with `ATZ` and applies the output [settings](api.md#elm327.Settings).

### Serial speed

Genuine ELM327 chips default to 38400 bit/s. Many clones use 9600 or 115200:

```python
ELM327.open("/dev/ttyUSB0", baudrate=115200)
ELM327.open("serial:///dev/ttyUSB0?baudrate=115200")  # same thing, as a URL
```

## Send commands

```python
elm.send("ATDP")  # ["AUTO, ISO 15765-4 (CAN 11/500)"]
elm.send("0100")  # ["4100BE3EB813"]
```

`send()` returns the reply lines without echo, prompt or `SEARCHING...`.

## Handle errors

```python
from elm327 import ELM327Error, NoDataError

try:
    elm.send("010D")
except NoDataError:
    print("the vehicle did not answer")
except ELM327Error as exc:
    print(f"adapter problem: {exc}")
```

## Debugging

The library logs every line sent and received at `DEBUG` level:

```python
import logging

logging.basicConfig(level=logging.DEBUG)
```
