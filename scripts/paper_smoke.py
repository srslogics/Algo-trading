"""Exercise a running local API; creates only a simulated position."""

import os
import uuid

import httpx

base = os.environ.get("OPTIONLAB_SMOKE_URL", "http://127.0.0.1:8000")
token = os.environ.get("OPTIONLAB_API_TOKEN", "")
headers = {"Authorization": "Bearer " + token} if token else {}
with httpx.Client(base_url=base, headers=headers, timeout=30) as client:
    for path, body in [("/api/v1/demo/tick", {}), ("/api/v1/proposals", {})]:
        response = client.post(path, json=body)
        response.raise_for_status()
    proposal = response.json()
    key = str(uuid.uuid4())
    body = {"proposal_id": proposal["id"], "idempotency_key": key}
    fill = client.post("/api/v1/paper/orders", json=body)
    fill.raise_for_status()
    repeated = client.post("/api/v1/paper/orders", json=body)
    assert repeated.json()["order"]["id"] == fill.json()["order"]["id"]
    position_id = fill.json()["order"]["position_id"]
    closed = client.post(
        f"/api/v1/positions/{position_id}/close", json={"idempotency_key": str(uuid.uuid4())}
    )
    closed.raise_for_status()
    print("PASS: snapshot → proposal → risk → paper fill → idempotent retry → exit")
