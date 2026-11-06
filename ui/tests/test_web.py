import pytest
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


@pytest.mark.parametrize("page", ["/", "/watch", "/dev/fixtures"])
def test_every_page_loads_the_web_app(tmp_path, page):
    response = TestClient(create_app(built_web_app(tmp_path))).get(page)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert response.text == "<p>The table</p>"


def test_a_page_can_be_asked_for_with_a_slash_on_the_end(tmp_path):
    client = TestClient(create_app(built_web_app(tmp_path)))
    assert client.get("/dev/fixtures/").text == "<p>The table</p>"


def test_a_browser_can_keep_using_its_saved_copy_of_a_page(tmp_path):
    client = TestClient(create_app(built_web_app(tmp_path)))
    etag = client.get("/dev/fixtures").headers["etag"]
    assert client.get("/dev/fixtures", headers={"if-none-match": etag}).status_code == 304


def test_a_page_is_not_found_while_the_web_app_is_being_rebuilt(tmp_path):
    client = TestClient(create_app(built_web_app(tmp_path)))
    (tmp_path / "index.html").unlink()
    assert client.get("/dev/fixtures").status_code == 404


@pytest.mark.parametrize("address", ["/nonsense", "/dev", "/dev/nonsense", "/dev/fixtures/more",
                                     "/watch/more", "/api/nonsense", "/assets/missing.js"])
def test_any_other_address_is_not_found(tmp_path, address):
    assert TestClient(create_app(built_web_app(tmp_path))).get(address).status_code == 404


def test_the_api_still_answers_next_to_the_web_app(tmp_path):
    client = TestClient(create_app(built_web_app(tmp_path)))
    assert len(client.get("/api/deal").json()["board"]) == 5


@pytest.mark.parametrize("page", ["/", "/watch", "/dev/fixtures"])
def test_says_how_to_build_the_web_app_until_it_is_built(tmp_path, page):
    client = TestClient(create_app(tmp_path / "dist"))
    response = client.get(page)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "npm run build" in response.text
