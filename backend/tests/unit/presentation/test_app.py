"""Level 3: application factory, lifespan and static file serving.

These are the parts a conventional suite forgets and that a container then
surprises you with: start-up, shut-down, and "is the compiled UI really served?".
"""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from tv_insight.infrastructure.config import Settings
from tv_insight.presentation import app as app_module
from tv_insight.presentation import main as main_module
from tv_insight.presentation.app import create_app, resolve_static_dir

SETTINGS = Settings(app_env="test")


class StubContainer:
    """Stands in for the real graph so the lifespan can be tested in isolation."""

    def __init__(self) -> None:
        self.shutdown_calls = 0

    async def shutdown(self) -> None:
        self.shutdown_calls += 1


def client_for(directory: Path) -> httpx.AsyncClient:
    """An in-process client for an app whose UI lives in ``directory``."""
    app = create_app(Settings(app_env="test", static_dir=str(directory)))
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://testserver"
    )


class TestLifespan:
    async def test_an_injected_container_is_used_and_not_owned(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        injected = StubContainer()
        built = StubContainer()
        monkeypatch.setattr(
            app_module.Container, "build", classmethod(lambda _cls, _settings: built)
        )

        app = create_app(SETTINGS, injected)  # type: ignore[arg-type]
        async with app.router.lifespan_context(app):
            assert app.state.container is injected

        # An injected container belongs to the caller: the app must not shut it down.
        assert built.shutdown_calls == 0
        assert injected.shutdown_calls == 0

    async def test_an_owned_container_is_built_and_shut_down(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        built = StubContainer()
        monkeypatch.setattr(
            app_module.Container, "build", classmethod(lambda _cls, _settings: built)
        )

        app = create_app(SETTINGS)
        async with app.router.lifespan_context(app):
            assert app.state.container is built

        assert built.shutdown_calls == 1

    async def test_the_container_is_shut_down_even_when_startup_fails(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        built = StubContainer()
        monkeypatch.setattr(
            app_module.Container, "build", classmethod(lambda _cls, _settings: built)
        )
        app = create_app(SETTINGS)

        with pytest.raises(RuntimeError):
            async with app.router.lifespan_context(app):
                raise RuntimeError("boom")

        assert built.shutdown_calls == 1


class TestStaticResolution:
    def test_the_package_directory_is_the_default(self) -> None:
        # `static_dir=""` is passed explicitly so the assertion does not depend on
        # a STATIC_DIR variable that the container sets: init kwargs win over the
        # environment, which keeps the test hermetic wherever it runs.
        assert resolve_static_dir(Settings(app_env="test", static_dir="")) == (
            app_module.STATIC_DIR
        )

    def test_an_explicit_directory_wins(self, tmp_path: Path) -> None:
        resolved = resolve_static_dir(
            Settings(app_env="test", static_dir=str(tmp_path))
        )
        assert resolved == tmp_path.resolve()


class TestServingTheSpa:
    async def test_index_html_is_served_for_client_routes(self, tmp_path: Path) -> None:
        (tmp_path / "index.html").write_text("<html><body>app</body></html>")

        async with client_for(tmp_path) as http:
            root = await http.get("/")
            deep = await http.get("/series/169/episodes/12192")

        assert root.status_code == 200
        assert "app" in root.text
        assert deep.status_code == 200

    async def test_assets_are_mounted_when_present(self, tmp_path: Path) -> None:
        (tmp_path / "index.html").write_text("<html></html>")
        assets = tmp_path / "assets"
        assets.mkdir()
        (assets / "app.js").write_text("console.log(1)")

        async with client_for(tmp_path) as http:
            response = await http.get("/assets/app.js")

        assert response.status_code == 200
        assert "console" in response.text

    async def test_a_missing_build_explains_itself_instead_of_a_bare_404(
        self, tmp_path: Path
    ) -> None:
        empty = tmp_path / "not-built"
        empty.mkdir()

        async with client_for(empty) as http:
            response = await http.get("/series/1")

        assert response.status_code == 404
        assert response.json()["error"] == "FrontendNotBuilt"

    async def test_unknown_api_paths_never_return_html(self, tmp_path: Path) -> None:
        (tmp_path / "index.html").write_text("<html></html>")

        async with client_for(tmp_path) as http:
            response = await http.get("/api/nope")

        assert response.status_code == 404
        assert response.json()["error"] == "NotFound"


class TestMainEntryPoint:
    def test_run_starts_uvicorn_on_the_configured_port(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        captured: dict[str, object] = {}

        def fake_run(app: object, **kwargs: object) -> None:
            captured["app"] = app
            captured.update(kwargs)

        monkeypatch.setattr(main_module.uvicorn, "run", fake_run)

        main_module.run()

        assert captured["host"] == "0.0.0.0"  # noqa: S104 - asserted on purpose
        assert captured["port"] == 7777
        assert captured["log_config"] is None
        assert captured["app"] is not None
