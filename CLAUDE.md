# Notes for Claude

- Follow `CONTRIBUTING.md`: it is the source of truth for style, typing, error handling, logging, tests and git workflow.
- Before every commit: `uv run ruff format && uv run ruff check && uv run mypy && uv run pytest --cov`. All must pass.
- Unit tests never need hardware; extend `tests/emulator/fake_elm.py` when a new device behaviour must be simulated.
- Keep the public surface in `src/elm327/__init__.py` (`__all__`) deliberate; anything else is private.
- Commit in small, logical Conventional Commits.
