# Security Policy

## Reporting a Vulnerability

Please do not open a public issue for a vulnerability. Email the maintainer
listed in `pyproject.toml` with a concise description, affected versions or
commits, and reproduction steps.

## Sensitive Data

Do not commit:

- `.env` files or Google Maps API keys
- private map tile URLs or credentials
- generated logs containing local paths or tokens
- private field boundaries, imagery, or location datasets

Use `.env.example` for documented environment variables.
