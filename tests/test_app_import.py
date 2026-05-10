from gateway.app import create_app


def test_app_importable() -> None:
    app = create_app()
    assert app.title == "LightLLM-Gateway"
