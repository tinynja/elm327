# Changelog

All notable changes to this project are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- Project skeleton: packaging, tooling, CI and release workflows, documentation site.
- Transport layer: serial (USB, Bluetooth SPP, pyserial URLs), TCP (Wi-Fi adapters) and in-memory loopback.
- `ELM327` device class: connect/synchronise, reset, command/response handling with error mapping, basic configuration (echo, linefeeds, spaces, headers), identification and battery voltage.
