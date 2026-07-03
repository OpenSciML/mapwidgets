# Development

This repository uses `uv` for local Python workflows.

## Install docs dependencies

```bash
uv sync --group docs
```

## Build documentation

Run a strict build into the configured `docs/` output folder:

```bash
uv run --group docs mkdocs build --strict
```

For a temporary validation build that avoids touching generated output:

```bash
uv run --group docs mkdocs build --strict -d /tmp/mapwidgets-mkdocs-check
```

## Syntax check

```bash
uv run .venv/bin/python -m compileall main.py src
```

## Source and output directories

Editable Markdown lives in `mkdocs/`. Generated HTML lives in `docs/`.
Do not hand-edit files under `docs/`; rebuild them from the MkDocs source.
