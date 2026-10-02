# tv-insight — backend

FastAPI service implementing the interactive TV series experience. The overall
architecture is documented in [`../docs/ARCHITECTURE.md`](../docs/ARCHITECTURE.md).

## Layers

| Layer             | Path                       | May import                       |
| ----------------- | -------------------------- | -------------------------------- |
| Domain            | `src/tv_insight/domain`         | standard library only            |
| Application       | `src/tv_insight/application`    | domain                           |
| Infrastructure    | `src/tv_insight/infrastructure` | domain, application, third party |
| Presentation      | `src/tv_insight/presentation`   | application, infrastructure      |

## Local development

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

pytest                 # unit + integration (no network needed)
ruff check .
mypy

uvicorn tv_insight.presentation.app:create_app --factory --port 7777 --reload
```

The database schema is managed with Alembic:

```bash
alembic upgrade head
alembic revision --autogenerate -m "describe the change"
```
