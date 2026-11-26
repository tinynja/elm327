# elm327

A typed, dependency-light Python library to connect to, configure and talk to **ELM327** OBD-II/CAN
adapters over USB, Bluetooth or Wi-Fi.

!!! warning "Pre-alpha"
    The connection, command/response and configuration core is in place. Bus monitoring
    (`ATMA`/`ATMT`/`ATMR`), CAN filters and a python-can interface are next. The API may change
    until 1.0.

## Design

- **Transports only move bytes.** Serial, TCP and an in-memory loopback share one interface, so
  the driver is the same for every adapter type and fully testable without hardware.
- **The driver knows the output format.** It sets echo, linefeeds, spaces and headers itself on
  connect, so replies are always parsed with certainty, even on clones.
- **Errors are exceptions.** Every adapter error reply maps to a specific `ResponseError`
  subclass carrying the command and the raw reply.
- **Everything blocks for a bounded time.** All durations are seconds; nothing waits forever.
