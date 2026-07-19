from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote, urlsplit, urlunsplit

import httpx


@dataclass(frozen=True)
class RemoteClient:
    email: str
    sub_id: str
    enabled: bool
    subscription_url: str = ""


@dataclass(frozen=True)
class SubscriptionUsage:
    upload: int
    download: int
    total: int
    expire: int

    @property
    def used(self) -> int:
        return self.upload + self.download


class XUIError(RuntimeError):
    pass


def normalize_panel_url(value: str) -> str:
    raw = value.strip()
    if not raw:
        raise XUIError("Panel URL is required.")
    parsed = urlsplit(raw)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise XUIError("Panel URL must be a complete http:// or https:// URL.")
    path = re.sub(r"/{2,}", "/", parsed.path or "").rstrip("/")
    return urlunsplit((parsed.scheme, parsed.netloc, path, "", ""))


def candidate_api_roots(panel_url: str) -> list[str]:
    """Return likely base-path-aware 3X-UI API roots in safe priority order."""
    normalized = normalize_panel_url(panel_url)
    parsed = urlsplit(normalized)
    origin = urlunsplit((parsed.scheme, parsed.netloc, "", "", ""))
    path = parsed.path.rstrip("/")
    lower_path = path.lower()
    roots: list[str] = []

    def add(url: str) -> None:
        clean = url.rstrip("/")
        if clean and clean not in roots:
            roots.append(clean)

    marker = "/panel/api"
    marker_index = lower_path.find(marker)
    if marker_index >= 0:
        add(origin + path[: marker_index + len(marker)])
        return roots

    for page_suffix in ("/api-docs", "/login", "/settings", "/clients", "/inbounds"):
        if lower_path.endswith(page_suffix):
            normalized = normalized[: -len(page_suffix)]
            parsed = urlsplit(normalized)
            path = parsed.path.rstrip("/")
            lower_path = path.lower()
            break

    if lower_path.endswith("/panel"):
        add(normalized + "/api")
        panel_root = normalized[: -len("/panel")]
        add(panel_root + "/panel/api")
    else:
        add(normalized + "/panel/api")

    add(normalized + "/api")
    add(origin + "/panel/api")
    return roots


class XUIClient:
    def __init__(self, base_url: str, api_token: str, verify_tls: bool = True, timeout: int = 15):
        self.base_url = normalize_panel_url(base_url)
        self.api_token = api_token.strip()
        self.verify_tls = verify_tls
        self.timeout = max(5, timeout)
        self.api_roots = candidate_api_roots(self.base_url)
        self.discovered_api_root = ""

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_token}",
            "Accept": "application/json",
            "User-Agent": "3X-UI-Ratio/0.1.10",
            "X-Requested-With": "XMLHttpRequest",
        }

    async def list_clients(self) -> list[RemoteClient]:
        attempts: list[str] = []
        async with httpx.AsyncClient(
            verify=self.verify_tls,
            timeout=self.timeout,
            follow_redirects=True,
        ) as client:
            for api_root in self._ordered_roots():
                url = f"{api_root}/clients/list"
                response = await client.get(url, headers=self._headers())
                attempts.append(f"GET {url} -> HTTP {response.status_code}")
                if response.status_code in {401, 403}:
                    self._raise_for_status(response, "List clients", url)
                if response.status_code == 404:
                    continue
                if response.status_code >= 400:
                    continue
                try:
                    payload = self._unwrap(response)
                except XUIError:
                    continue
                rows = payload if isinstance(payload, list) else []
                self.discovered_api_root = api_root
                return self._normalize_clients(rows)

            for api_root in self._ordered_roots():
                url = f"{api_root}/inbounds/list"
                response = await client.get(url, headers=self._headers())
                attempts.append(f"GET {url} -> HTTP {response.status_code}")
                if response.status_code in {401, 403}:
                    self._raise_for_status(response, "List legacy inbounds", url)
                if response.status_code == 404:
                    continue
                if response.status_code >= 400:
                    continue
                try:
                    payload = self._unwrap(response)
                except XUIError:
                    continue
                self.discovered_api_root = api_root
                return self._clients_from_inbounds(payload)

        details = "; ".join(attempts)
        raise XUIError(
            "No compatible 3X-UI API endpoint was found. The URL may be incorrect, a reverse "
            "proxy may not forward /panel/api, or the connected service may not be Sanaei 3X-UI. "
            "Enter the exact browser access URL including WebBasePath. Tried: " + details
        )

    def _ordered_roots(self) -> list[str]:
        if not self.discovered_api_root:
            return self.api_roots
        return [self.discovered_api_root] + [
            root for root in self.api_roots if root != self.discovered_api_root
        ]

    async def set_enabled(self, emails: list[str], enabled: bool) -> dict[str, Any]:
        clean = sorted({email.strip() for email in emails if email.strip()})
        if not clean:
            return {"updated": 0}
        endpoint = "bulkEnable" if enabled else "bulkDisable"
        attempts: list[str] = []
        async with httpx.AsyncClient(
            verify=self.verify_tls,
            timeout=self.timeout,
            follow_redirects=True,
        ) as client:
            for api_root in self._ordered_roots():
                url = f"{api_root}/clients/{endpoint}"
                response = await client.post(
                    url,
                    headers={**self._headers(), "Content-Type": "application/json"},
                    json={"emails": clean},
                )
                attempts.append(f"POST {url} -> HTTP {response.status_code}")
                if response.status_code in {401, 403}:
                    self._raise_for_status(response, "Change client status", url)
                if response.status_code == 404:
                    continue
                self._raise_for_status(response, "Change client status", url)
                payload = self._unwrap(response)
                self.discovered_api_root = api_root
                return payload if isinstance(payload, dict) else {"result": payload}

        raise XUIError(
            "The connected panel does not expose the bulk client enable/disable API required by "
            "3X-UI Ratio. Update 3X-UI and verify the panel URL. Tried: " + "; ".join(attempts)
        )

    @staticmethod
    def _clients_from_inbounds(payload: Any) -> list[RemoteClient]:
        rows: list[dict[str, Any]] = []
        for inbound in payload if isinstance(payload, list) else []:
            if not isinstance(inbound, dict):
                continue
            settings = inbound.get("settings", {})
            if isinstance(settings, str):
                try:
                    settings = json.loads(settings)
                except (TypeError, ValueError):
                    settings = {}
            clients = settings.get("clients", []) if isinstance(settings, dict) else []
            if isinstance(clients, list):
                rows.extend(item for item in clients if isinstance(item, dict))
            client_stats = inbound.get("clientStats", inbound.get("client_stats", []))
            if isinstance(client_stats, list):
                rows.extend(item for item in client_stats if isinstance(item, dict))
        return XUIClient._normalize_clients(rows)

    @staticmethod
    def _raise_for_status(response: httpx.Response, action: str, url: str = "") -> None:
        suffix = f" ({url})" if url else ""
        if response.status_code in {401, 403}:
            raise XUIError(
                f"{action}: authentication failed{suffix}. Create a new API token in "
                "3X-UI Settings → Authentication/API Tokens and paste the plaintext token shown "
                "at creation time. Do not use the masked token value or the panel password."
            )
        if response.status_code >= 400:
            body = response.text[:300].strip()
            raise XUIError(f"{action}: HTTP {response.status_code}{suffix} {body}".strip())

    @staticmethod
    def _unwrap(response: httpx.Response) -> Any:
        try:
            payload = response.json()
        except ValueError as exc:
            raise XUIError("The panel response is not valid JSON.") from exc
        if isinstance(payload, dict):
            if payload.get("success") is False:
                raise XUIError(str(payload.get("msg") or "3X-UI request failed"))
            return payload.get("obj", payload.get("data", payload))
        return payload

    @staticmethod
    def _normalize_clients(rows: list[Any]) -> list[RemoteClient]:
        result: dict[str, RemoteClient] = {}
        for row in rows:
            if not isinstance(row, dict):
                continue
            nested = row.get("client") if isinstance(row.get("client"), dict) else row
            email = str(nested.get("email") or "").strip()
            if not email:
                continue
            sub_id = str(
                nested.get("subId")
                or nested.get("subid")
                or nested.get("sub_id")
                or nested.get("subID")
                or ""
            ).strip()
            enabled_raw = nested.get("enable", nested.get("enabled", True))
            if isinstance(enabled_raw, str):
                enabled = enabled_raw.strip().lower() in {"1", "true", "yes", "on"}
            else:
                enabled = bool(enabled_raw)
            subscription_url = str(
                nested.get("subscriptionUrl")
                or nested.get("subscription_url")
                or nested.get("subUrl")
                or nested.get("sub_url")
                or nested.get("subscription")
                or ""
            ).strip()
            previous = result.get(email)
            if previous and not sub_id:
                sub_id = previous.sub_id
            if previous and not subscription_url:
                subscription_url = previous.subscription_url
            result[email] = RemoteClient(
                email=email,
                sub_id=sub_id,
                enabled=enabled,
                subscription_url=subscription_url,
            )
        return list(result.values())



def _normalize_http_url(value: str) -> str:
    raw = value.strip()
    if not raw:
        return ""
    parsed = urlsplit(raw)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise XUIError("Subscription URL must be a complete http:// or https:// URL.")
    path = re.sub(r"/{2,}", "/", parsed.path or "")
    return urlunsplit((parsed.scheme, parsed.netloc, path, parsed.query, ""))


def subscription_url_candidates(
    source: str,
    panel_url: str,
    sub_id: str,
    email: str,
    preferred_url: str = "",
) -> list[str]:
    """Build de-duplicated subscription URL candidates in priority order.

    ``preferred_url`` may be a URL returned by 3X-UI or the last URL that worked
    for the user. It is tried first. The configured subscription base/template
    is tried next, followed by the standard root and WebBasePath subscription
    routes used by common 3X-UI installations.
    """
    if not sub_id.strip():
        raise XUIError("Client has no subId in 3X-UI.")

    normalized_panel = normalize_panel_url(panel_url)
    parsed_panel = urlsplit(normalized_panel)
    origin = urlunsplit((parsed_panel.scheme, parsed_panel.netloc, "", "", ""))
    encoded_sub_id = quote(sub_id.strip(), safe="")
    candidates: list[str] = []

    def add(value: str) -> None:
        if not value:
            return
        value = value.strip()
        if value.startswith("/"):
            value = origin + value
        try:
            normalized = _normalize_http_url(value)
        except XUIError:
            return
        if normalized and normalized not in candidates:
            candidates.append(normalized)

    add(preferred_url)

    if source.strip():
        add(render_subscription_url(source, normalized_panel, sub_id, email))

    add(f"{origin}/sub/{encoded_sub_id}")
    if parsed_panel.path.rstrip("/"):
        add(f"{origin}{parsed_panel.path.rstrip('/')}/sub/{encoded_sub_id}")

    if not candidates:
        raise XUIError("No usable subscription URL could be generated.")
    return candidates


def render_subscription_url(source: str, panel_url: str, sub_id: str, email: str) -> str:
    """Build a client subscription URL.

    The preferred UI value is a base URL such as ``https://sub.example.com/sub``.
    Ratio appends the URL-encoded 3X-UI ``subId`` as the next path segment. Older
    placeholder templates remain supported for backward compatibility.
    """
    raw = source.strip()
    if not raw:
        raise XUIError("Subscription base URL is required.")
    if not sub_id.strip():
        raise XUIError("Client has no subId in 3X-UI.")

    values = {
        "panel_url": normalize_panel_url(panel_url),
        "sub_id": quote(sub_id.strip(), safe=""),
        "subId": quote(sub_id.strip(), safe=""),
        "email": quote(email, safe=""),
    }
    if "{" in raw or "}" in raw:
        try:
            url = raw.format_map(values).strip()
        except KeyError as exc:
            raise XUIError(f"Unknown subscription template variable: {exc.args[0]}") from exc
    else:
        base = urlsplit(raw)
        if base.scheme not in {"http", "https"} or not base.netloc:
            raise XUIError("Subscription URL must be a complete http:// or https:// URL.")
        path = f"{base.path.rstrip('/')}/{values['sub_id']}"
        url = urlunsplit((base.scheme, base.netloc, path, base.query, ""))

    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise XUIError("Subscription URL must be a complete http:// or https:// URL.")
    return urlunsplit((parsed.scheme, parsed.netloc, re.sub(r"/{2,}", "/", parsed.path), parsed.query, ""))


def parse_subscription_userinfo(value: str | None) -> SubscriptionUsage:
    if not value:
        raise XUIError(
            "Subscription response did not include a Subscription-Userinfo header. "
            "The Base64 response body contains client configurations, not traffic counters. "
            "Verify that the Subscription base URL is the exact 3X-UI subscription service URL."
        )
    values: dict[str, int] = {}
    for key, raw in re.findall(r"([A-Za-z]+)\s*=\s*(-?\d+)", value):
        values[key.lower()] = max(0, int(raw))
    if "upload" not in values or "download" not in values:
        raise XUIError("Subscription-Userinfo header is incomplete.")
    return SubscriptionUsage(
        upload=values.get("upload", 0),
        download=values.get("download", 0),
        total=values.get("total", 0),
        expire=values.get("expire", 0),
    )


async def fetch_subscription_usage(
    url: str,
    verify_tls: bool = True,
    timeout: int = 15,
) -> SubscriptionUsage:
    """Read traffic headers from a 3X-UI subscription response.

    3X-UI normally returns a Base64-encoded configuration list in the response
    body. Ratio deliberately does not decode or parse that body; usage is read
    from the HTTP ``Subscription-Userinfo`` response header.
    """
    headers = {
        "User-Agent": "v2rayNG/3X-UI-Ratio-0.1.10",
        "Accept": "*/*",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
    }
    async with httpx.AsyncClient(
        verify=verify_tls,
        timeout=max(5, timeout),
        follow_redirects=True,
    ) as client:
        async with client.stream("GET", url, headers=headers) as response:
            if response.status_code >= 400:
                raise XUIError(f"Subscription URL returned HTTP {response.status_code}: {url}")
            header = response.headers.get("subscription-userinfo") or response.headers.get(
                "x-subscription-userinfo"
            )
            return parse_subscription_userinfo(header)


async def fetch_subscription_usage_from_candidates(
    urls: list[str],
    verify_tls: bool = True,
    timeout: int = 15,
) -> tuple[SubscriptionUsage, str]:
    """Try subscription URLs sequentially and return the first successful one."""
    clean_urls: list[str] = []
    for url in urls:
        normalized = _normalize_http_url(url)
        if normalized not in clean_urls:
            clean_urls.append(normalized)

    if not clean_urls:
        raise XUIError("No subscription URL candidates were provided.")

    errors: list[str] = []
    for url in clean_urls:
        try:
            usage = await fetch_subscription_usage(
                url,
                verify_tls=verify_tls,
                timeout=timeout,
            )
            return usage, url
        except Exception as exc:
            errors.append(f"{url} -> {exc}")

    raise XUIError(
        "All subscription URL candidates failed. Tried: " + "; ".join(errors)
    )

