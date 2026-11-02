from fastapi.testclient import TestClient
from server.app import create_app


def built_web_app(folder):
    """Fills folder the way npm run build would."""
    (folder / "index.html").write_text("<p>The table</p>")
    (folder / "assets").mkdir()
    (folder / "assets" / "app.js").write_text("console.log('dealt')")
    return folder


def test_serves_the_built_web_app(tmp_path):
    client = TestClient(create_app(built_web_app(tmp_path)))
    assert client.get("/").text == "<p>The table</p>"
    assert client.get("/assets/app.js").text == "console.log('dealt')"


def test_the_api_still_answers_next_to_the_web_app(tmp_path):
    client = TestClient(create_app(built_web_app(tmp_path)))
    assert len(client.get("/api/deal").json()["board"]) == 5


def test_says_how_to_build_the_web_app_until_it_is_built(tmp_path):
    client = TestClient(create_app(tmp_path / "dist"))
    response = client.get("/")
    assert response.status_code == 200
    assert "npm run build" in response.text
