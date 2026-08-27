# Contributing to AccuRad

Thanks for your interest in contributing! This guide will help you get started.

## Development Setup

```bash
# Clone the repo
git clone https://github.com/Clement1211/accurad.git
cd accurad

# Create a virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
.venv\Scripts\activate     # Windows

# Install in development mode
pip install -e ".[dev,bluetooth]"
```

## Quality Checks

All three must pass before submitting a PR:

```bash
# Linter
ruff check accurad/ tests/

# Type checker (strict mode)
mypy --strict accurad/

# Tests
pytest -v
```

## Code Conventions

- **Python 3.10+** — use modern type hints (`X | None` instead of `Optional[X]`)
- **Type hints** on all public methods (enforced by `mypy --strict`)
- **Frozen dataclasses** for models (`@dataclass(frozen=True)`)
- **Google-style docstrings**
- No unnecessary abstractions — keep it simple

## Pull Request Process

1. Fork the repository and create a feature branch from `main`
2. Make your changes, ensuring all quality checks pass
3. Write or update tests for your changes
4. Submit a PR with a clear description of what and why

## Hardware Testing

If your change affects USB or BLE communication, tag your PR with `needs-hardware-test`. These tests require a physical AccuRad PRD device and cannot run in CI.

## Protocol Notes

If you're working on the protocol layer, read `README_DEV.md` for the binary frame format and known gotchas (CRC scope, LEN calculation, BLE timing).

## License

By contributing, you agree that your contributions will be licensed under the [MIT License](LICENSE).
