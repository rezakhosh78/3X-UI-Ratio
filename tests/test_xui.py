import httpx
import pytest

from app.xui import (
    XUIClient,
    candidate_api_roots,
    fetch_subscription_usage,
    fetch_subscription_usage_from_candidates,
    parse_subscription_userinfo,
    render_subscription_url,
    subscription_url_candidates,
)


def test_parse_userinfo():
    usage = parse_subscription_userinfo("upload=10; download=20; total=100; expire=1700000000")
    assert usage.used == 30
    assert usage.total == 100


def test_render_legacy_subscription_template():
    url = render_subscription_url("{panel_url}/sub/{sub_id}", "https://x.test/path/", "a b", "u")
    assert url == "https://x.test/path/sub/a%20b"


def test_render_subscription_base_appends_subid():
    url = render_subscription_url(
        "https://subscription.example.com/sub",
        "https://panel.test/reza",
        "client sub/id",
        "alice",
    )
    assert url == "https://subscription.example.com/sub/client%20sub%2Fid"


def test_render_subscription_base_avoids_double_slash():
    url = render_subscription_url("https://sub.test/sub/", "https://panel.test", "abc", "alice")
    assert url == "https://sub.test/sub/abc"


def test_api_roots_accept_browser_panel_url():
    roots = candidate_api_roots("https://x.test:2053/secret/panel")
    assert "https://x.test:2053/secret/panel/api" in roots
    assert "https://x.test:2053/secret/panel/panel/api" not in roots


def test_api_roots_reduce_pasted_endpoint():
    roots = candidate_api_roots("https://x.test/secret/panel/api/openapi.json")
    assert roots[0] == "https://x.test/secret/panel/api"


def test_legacy_inbounds_include_client_stats():
    clients = XUIClient._clients_from_inbounds(
        [
            {
                "settings": {"clients": [{"email": "alice", "enable": True}]},
                "clientStats": [{"email": "alice", "subId": "sub-1", "enable": False}],
            }
        ]
    )
    assert len(clients) == 1
    assert clients[0].email == "alice"
    assert clients[0].sub_id == "sub-1"
    assert clients[0].enabled is False


def test_headers_identify_ajax_requests_for_auth_errors():
    client = XUIClient("https://x.test/secret", "token")
    headers = client._headers()
    assert headers["Authorization"] == "Bearer token"
    assert headers["X-Requested-With"] == "XMLHttpRequest"
    assert headers["User-Agent"] == "3X-UI-Ratio/0.1.10"


@pytest.mark.asyncio
async def test_subscription_base64_body_is_ignored_and_header_is_used(monkeypatch):
    async def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == "https://sub.test/sub/abc"
        return httpx.Response(
            200,
            headers={"Subscription-Userinfo": "upload=12; download=34; total=100"},
            content=b"dmxlc3M6Ly9leGFtcGxlLWJhc2U2NC1jb25maWc=",
        )

    transport = httpx.MockTransport(handler)
    original = httpx.AsyncClient

    def client_factory(*args, **kwargs):
        kwargs["transport"] = transport
        return original(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", client_factory)
    usage = await fetch_subscription_usage("https://sub.test/sub/abc")
    assert usage.upload == 12
    assert usage.download == 34
    assert usage.used == 46


def test_subscription_candidates_include_preferred_configured_and_fallbacks():
    urls = subscription_url_candidates(
        "https://sub.example.com/sub",
        "https://panel.example.com/reza",
        "abc",
        "alice",
        "https://working.example.com/sub/abc",
    )
    assert urls[0] == "https://working.example.com/sub/abc"
    assert "https://sub.example.com/sub/abc" in urls
    assert "https://panel.example.com/sub/abc" in urls
    assert "https://panel.example.com/reza/sub/abc" in urls


@pytest.mark.asyncio
async def test_subscription_candidate_reader_falls_back_after_404(monkeypatch):
    async def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url) == "https://bad.test/sub/abc":
            return httpx.Response(404)
        return httpx.Response(
            200,
            headers={"Subscription-Userinfo": "upload=7; download=9; total=100"},
        )

    transport = httpx.MockTransport(handler)
    original = httpx.AsyncClient

    def client_factory(*args, **kwargs):
        kwargs["transport"] = transport
        return original(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", client_factory)
    usage, working_url = await fetch_subscription_usage_from_candidates(
        ["https://bad.test/sub/abc", "https://good.test/sub/abc"]
    )
    assert working_url == "https://good.test/sub/abc"
    assert usage.used == 16


def test_subscription_candidates_resolve_relative_api_url():
    urls = subscription_url_candidates(
        "https://sub.example.com/sub",
        "https://panel.example.com/reza",
        "abc",
        "alice",
        "/sub/abc",
    )
    assert urls[0] == "https://panel.example.com/sub/abc"

