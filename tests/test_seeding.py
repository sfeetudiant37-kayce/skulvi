from fastapi.testclient import TestClient

from app.main import create_app


def test_sample_seed_is_fictional_and_idempotent(tmp_path) -> None:
    database_path = tmp_path / "seed.sqlite3"
    app = create_app(database_path, seed_samples=True)
    with TestClient(app) as client:
        response = client.get("/api/v1/candidates?page_size=100")
        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 4
        assert all(item["is_sample"] is True for item in body["items"])
        assert client.get("/api/v1/meta").json()["sample_data"] is True

    second_app = create_app(database_path, seed_samples=True)
    with TestClient(second_app) as second_client:
        assert second_client.get("/api/v1/stats").json()["total"] == 4
