from __future__ import annotations

from fastapi.testclient import TestClient

from tests.conftest import candidate_payload


def create_candidate(client: TestClient, **overrides: object) -> dict:
    response = client.post("/api/v1/candidates", json=candidate_payload(**overrides))
    assert response.status_code == 201, response.text
    return response.json()


def test_health_and_reference_catalog(client: TestClient) -> None:
    assert client.get("/api/v1/health").json() == {"status": "ok", "database": "ok"}
    catalog = client.get("/api/v1/options").json()
    assert {item["value"] for item in catalog["tracks"]} >= {"Frontend", "Backend"}


def test_web_shell_has_security_headers_and_same_origin_assets(client: TestClient) -> None:
    page = client.get("/")
    assert page.status_code == 200
    assert page.headers["Cache-Control"] == "no-store"
    assert "Content-Security-Policy" in page.headers
    assert page.headers["X-Content-Type-Options"] == "nosniff"
    assert "'unsafe-inline'" not in page.headers["Content-Security-Policy"]
    docs = client.get("/api/docs")
    assert docs.status_code == 200
    assert "https://cdn.jsdelivr.net" in docs.headers["Content-Security-Policy"]
    assert client.get("/assets/app.js").status_code == 200
    assert client.get("/assets/styles.css").status_code == 200


def test_create_candidate_returns_server_scored_profile(client: TestClient) -> None:
    candidate = create_candidate(client)
    assert candidate["name"] == "Camille Exemple"
    assert candidate["status"] == "new"
    assert candidate["score"]["skill_score"] == 30
    assert candidate["score"]["final_score"] is None
    assert candidate["score"]["priority_code"] == "high"


def test_email_is_unique_case_insensitively(client: TestClient) -> None:
    create_candidate(client, email="Camille@Example.test")
    duplicate = client.post(
        "/api/v1/candidates",
        json=candidate_payload(email="camille@example.test", name="Another Example"),
    )
    assert duplicate.status_code == 409
    assert "déjà" in duplicate.json()["detail"]


def test_input_validation_rejects_short_motivation_and_unsafe_url(client: TestClient) -> None:
    short_response = client.post(
        "/api/v1/candidates", json=candidate_payload(motivation="Trop court.")
    )
    assert short_response.status_code == 422

    unsafe_response = client.post(
        "/api/v1/candidates",
        json=candidate_payload(portfolio_url="javascript:alert(1)"),
    )
    assert unsafe_response.status_code == 422


def test_review_produces_final_score_and_updates_status(client: TestClient) -> None:
    candidate = create_candidate(client)
    response = client.patch(
        f"/api/v1/candidates/{candidate['id']}/review",
        json={
            "review_project": 20,
            "review_motivation": 15,
            "review_learning": 10,
            "review_notes": "Contribution vérifiée en entretien.",
            "status": "shortlisted",
        },
    )
    assert response.status_code == 200, response.text
    updated = response.json()
    assert updated["score"]["final_score"] == 75
    assert updated["score"]["review_complete"] is True
    assert updated["status"] == "shortlisted"


def test_review_score_is_bounded_by_schema(client: TestClient) -> None:
    candidate = create_candidate(client)
    response = client.patch(
        f"/api/v1/candidates/{candidate['id']}/review",
        json={"review_project": 26},
    )
    assert response.status_code == 422

    boolean_response = client.patch(
        f"/api/v1/candidates/{candidate['id']}/review",
        json={"review_project": True},
    )
    assert boolean_response.status_code == 422


def test_list_search_filter_and_pagination(client: TestClient) -> None:
    create_candidate(client)
    create_candidate(
        client,
        name="Yanis Exemple",
        email="yanis@example.test",
        track="Backend",
        skills=["Python", "SQL"],
    )
    create_candidate(
        client,
        name="Aïcha Exemple",
        email="aicha@example.test",
        track="Data / IA",
        skills=["Python", "SQL"],
    )

    page = client.get("/api/v1/candidates?page=2&page_size=1").json()
    assert page["total"] == 3
    assert page["page"] == 2
    assert len(page["items"]) == 1
    assert page["pages"] == 3

    backend = client.get("/api/v1/candidates?track=Backend").json()
    assert backend["total"] == 1
    assert backend["items"][0]["name"] == "Yanis Exemple"

    search = client.get("/api/v1/candidates?q=aïcha").json()
    assert search["total"] == 1
    assert search["items"][0]["name"] == "Aïcha Exemple"


def test_update_profile_preserves_review_and_status(client: TestClient) -> None:
    candidate = create_candidate(client)
    client.patch(
        f"/api/v1/candidates/{candidate['id']}/review",
        json={"review_project": 19, "status": "reviewing"},
    )
    update = candidate_payload(name="Camille Exemple Modifiée")
    response = client.put(f"/api/v1/candidates/{candidate['id']}", json=update)
    assert response.status_code == 200
    changed = response.json()
    assert changed["name"] == "Camille Exemple Modifiée"
    assert changed["review_project"] == 19
    assert changed["status"] == "reviewing"


def test_closed_candidate_is_excluded_from_open_work_metrics(client: TestClient) -> None:
    candidate = create_candidate(client)
    before = client.get("/api/v1/stats").json()
    assert before["priority"] == 1
    assert before["pending_review"] == 1

    response = client.patch(
        f"/api/v1/candidates/{candidate['id']}/review",
        json={"status": "closed"},
    )
    assert response.status_code == 200
    after = client.get("/api/v1/stats").json()
    assert after["total"] == 1
    assert after["priority"] == 0
    assert after["pending_review"] == 0


def test_delete_and_csv_export(client: TestClient) -> None:
    candidate = create_candidate(client, name='=HYPERLINK("https://example.test")')
    csv_response = client.get("/api/v1/candidates/export.csv")
    assert csv_response.status_code == 200
    assert "text/csv" in csv_response.headers["content-type"]
    assert "'=HYPERLINK" in csv_response.text

    deleted = client.delete(f"/api/v1/candidates/{candidate['id']}")
    assert deleted.status_code == 204
    assert client.get(f"/api/v1/candidates/{candidate['id']}").status_code == 404
