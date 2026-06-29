def test_openapi_exposes_bearer_security_scheme(client) -> None:
    response = client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()

    bearer = schema["components"]["securitySchemes"]["BearerAuth"]
    assert bearer["type"] == "http"
    assert bearer["scheme"] == "bearer"

    shops_get = schema["paths"]["/api/v1/shops"]["get"]
    assert shops_get["security"] == [{"BearerAuth": []}]

    login_post = schema["paths"]["/api/v1/auth/login"]["post"]
    assert login_post["security"] == []


def test_login_token_only_skips_cookies(client, admin_user) -> None:
    response = client.post(
        "/api/v1/auth/login?token_only=true",
        json={"email": "admin@test.com", "password": "password123"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["access_token"]
    assert body["token_type"] == "bearer"
    assert "__Host-modira_access" not in response.cookies

    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"})
    assert me.status_code == 200
    assert me.json()["email"] == "admin@test.com"
