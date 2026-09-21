from types import SimpleNamespace
from unittest.mock import Mock

import httpx
import pytest

from optionlab.agents.service import OpenAIProvider
from optionlab.brokers.kite import KiteReadOnly
from optionlab.data.demo import demo_candles


def test_kite_quotes_http_contract_and_missing_symbol():
    def handler(request):
        assert request.method == "GET"
        assert request.url.path == "/quote"
        assert request.headers["X-Kite-Version"] == "3"
        assert request.headers["Authorization"] == "token test-key:test-token"
        assert request.url.params.get_list("i") == ["NFO:TEST"]
        return httpx.Response(200, json={"status": "success", "data": {}})

    client = KiteReadOnly("test-key", "test-token", transport=httpx.MockTransport(handler))
    try:
        with pytest.raises(ValueError, match="incomplete"):
            client.quotes(["NFO:TEST"])
    finally:
        client.close()


def test_kite_historical_timezone_and_oi():
    def handler(request):
        assert request.url.path == "/instruments/historical/123/minute"
        assert request.url.params["oi"] == "1"
        return httpx.Response(
            200,
            json={
                "status": "success",
                "data": {"candles": [["2026-09-18T10:00:00+0530", 100, 110, 95, 105, 1000, 2000]]},
            },
        )

    client = KiteReadOnly("test-key", "test-token", transport=httpx.MockTransport(handler))
    try:
        candle = client.history("NFO:TEST", 123, "2026-09-18 09:15:00", "2026-09-18 15:30:00")[0]
        assert candle.oi == 2000
        assert candle.timestamp.utcoffset().total_seconds() == 19800
    finally:
        client.close()


def test_advisory_model_request_has_no_tools_or_execution_scope():
    # Construct without a real SDK client; no credentials or external calls in tests.
    provider = OpenAIProvider.__new__(OpenAIProvider)
    provider.client = Mock()
    provider.model = "configured-model"
    provider.client.responses.create.return_value = SimpleNamespace(
        status="completed", output_text="Advisory explanation"
    )
    result = provider.explain("trading_assistant", {"cash": "500000"}, "Explain my cash")
    request = provider.client.responses.create.call_args.kwargs
    assert request["store"] is False
    assert "tools" not in request
    assert request["model"] == "configured-model"
    assert result["advisory_only"] is True


def test_candle_ingestion_is_repeat_safe_and_rejects_corrections(client):
    candles = [c.model_dump(mode="json") for c in demo_candles()[:3]]
    assert client.post("/api/v1/market/history", json={"candles": candles}).json()["inserted"] == 3
    assert client.post("/api/v1/market/history", json={"candles": candles}).json()["inserted"] == 0
    candles[0]["volume"] += 1
    assert client.post("/api/v1/market/history", json={"candles": candles}).status_code == 422
