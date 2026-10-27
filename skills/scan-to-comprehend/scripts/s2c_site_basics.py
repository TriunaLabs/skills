#!/usr/bin/env python3
"""Bounded public-page performance, link, and information checks for S2C."""

from __future__ import annotations

from datetime import datetime, timezone
import http.client
import ipaddress
import re
import socket
import ssl
from urllib.parse import unquote, urljoin, urlsplit


MAX_LINK_PROBES = 8
LINK_TIMEOUT_SECONDS = 3


class PinnedHTTPSConnection(http.client.HTTPSConnection):
    """Keep DNS validation and the TLS connection on the same public address."""

    def __init__(self, host: str, address: str, port: int):
        super().__init__(host, port=port, timeout=LINK_TIMEOUT_SECONDS, context=ssl.create_default_context())
        self.address = address

    def connect(self) -> None:
        self.sock = socket.create_connection((self.address, self.port), self.timeout)
        self.sock = self._context.wrap_socket(self.sock, server_hostname=self.host)


def same_origin(base: str, candidate: str) -> bool:
    try:
        left, right = urlsplit(base), urlsplit(candidate)
        return (left.scheme, left.hostname, left.port or (443 if left.scheme == "https" else 80)) == (
            right.scheme, right.hostname, right.port or (443 if right.scheme == "https" else 80))
    except ValueError:
        return False


def candidate_links(frame: dict, max_links: int = MAX_LINK_PROBES) -> list[str]:
    """Select a small, repeatable sample of ordinary same-origin page links."""
    base = frame.get("url") or ""
    seen, result = set(), []
    for node in frame.get("nodes", []):
        if node.get("tag") != "a" or not node.get("visible"):
            continue
        href = str(node.get("href") or "").strip()
        if not href or href.startswith(("#", "mailto:", "tel:", "javascript:", "data:")):
            continue
        url = urljoin(base, href)
        parsed = urlsplit(url)
        if (parsed.scheme not in ("http", "https") or parsed.username or parsed.password or parsed.query
                or not same_origin(base, url)):
            continue
        clean = parsed._replace(fragment="").geturl()
        if clean not in seen:
            seen.add(clean)
            result.append(clean)
        if len(result) >= max_links:
            break
    return result


def head_status(url: str) -> int:
    """HEAD only; reject private DNS answers and never follow redirects."""
    parsed = urlsplit(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("unsupported link URL")
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    if port not in (80, 443):
        raise ValueError("link port is outside the public-page scope")
    addresses = socket.getaddrinfo(parsed.hostname, port, type=socket.SOCK_STREAM)
    ips = [item[4][0] for item in addresses]
    if not ips or any(not ipaddress.ip_address(ip).is_global for ip in ips):
        raise ValueError("link host did not resolve only to public addresses")
    if parsed.scheme == "https":
        connection = PinnedHTTPSConnection(parsed.hostname, ips[0], port)
    else:
        connection = http.client.HTTPConnection(ips[0], port=port, timeout=LINK_TIMEOUT_SECONDS)
    try:
        target = parsed.path or "/"
        if parsed.query:
            target += "?" + parsed.query
        connection.request("HEAD", target, headers={"Host": parsed.hostname,
                                                    "User-Agent": "S2C-SiteBasics/1.0"})
        return connection.getresponse().status
    finally:
        connection.close()


def get_public(url: str, max_bytes: int = 65536, timeout: int = LINK_TIMEOUT_SECONDS) -> tuple[int, dict[str, str], bytes]:
    """Fetch one public URL with pinned DNS, a byte cap, and no redirects."""
    parsed = urlsplit(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("unsupported public URL")
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    if port not in (80, 443):
        raise ValueError("port is outside the public-page scope")
    answers = socket.getaddrinfo(parsed.hostname, port, type=socket.SOCK_STREAM)
    ips = [answer[4][0] for answer in answers]
    if not ips or any(not ipaddress.ip_address(ip).is_global for ip in ips):
        raise ValueError("host did not resolve only to public addresses")
    connection = (PinnedHTTPSConnection(parsed.hostname, ips[0], port) if parsed.scheme == "https"
                  else http.client.HTTPConnection(ips[0], port=port, timeout=timeout))
    connection.timeout = timeout
    try:
        target = parsed.path or "/"
        if parsed.query:
            target += "?" + parsed.query
        host = parsed.hostname if port in (80, 443) else f"{parsed.hostname}:{port}"
        connection.request("GET", target, headers={"Host": host, "User-Agent": "S2C-Audit/1.0",
                                                   "Accept-Encoding": "identity"})
        response = connection.getresponse()
        data = response.read(max_bytes + 1)
        if len(data) > max_bytes:
            raise ValueError("response exceeds byte limit")
        return response.status, {name.lower(): value for name, value in response.getheaders()}, data
    finally:
        connection.close()


def status_label(status: int | None) -> str:
    if status in (404, 410):
        return "possible_broken"
    if status is None or status in (403, 405, 429, 501) or status >= 500:
        return "inconclusive"
    if 300 <= status < 400:
        return "redirect"
    if 200 <= status < 300:
        return "reachable"
    return "review"


def probe_links(frame: dict) -> list[dict]:
    checks = []
    for url in candidate_links(frame):
        try:
            status = head_status(url)
            note = "HEAD response; confirm a 404/410 in a browser before fixing"
        except (OSError, ValueError, ssl.SSLError) as exc:
            status = None
            note = f"HEAD unavailable: {type(exc).__name__}"
        checks.append({"url": url, "status": status, "result": status_label(status), "note": note})
    return checks


def project(snapshot: dict, link_probes: list[dict] | None = None) -> dict:
    frames = snapshot.get("frames") or []
    if not frames:
        raise ValueError("Site basics need at least one captured frame")
    frame = next((item for item in frames if item.get("id") == "desktop"), frames[0])
    base = frame.get("url") or snapshot.get("url") or ""
    links = []
    for node in frame.get("nodes", []):
        if node.get("tag") == "a" and node.get("visible"):
            href = str(node.get("href") or "").strip()
            if href:
                links.append({"label": str(node.get("name") or node.get("text") or "").strip()[:120],
                              "href": href})
    def matches(pattern: str) -> list[dict]:
        return [link for link in links if re.search(pattern, link["label"] + " " + link["href"], re.I)]
    emails = [link for link in links if link["href"].lower().startswith("mailto:")]
    phones = [link for link in links if link["href"].lower().startswith("tel:")]
    contact = matches(r"\b(contact|support|get.in.touch|book.a.call)\b")
    privacy = matches(r"\bprivacy\b")
    terms = matches(r"\b(terms|conditions|tos)\b")
    anchors = set(frame.get("anchor_ids") or []) | set(frame.get("anchor_names") or [])
    fragment_checks = []
    for link in links:
        href = link["href"]
        target = urljoin(base, href)
        parsed = urlsplit(target)
        if not parsed.fragment or not same_origin(base, target):
            continue
        if parsed.path != urlsplit(base).path or parsed.query != urlsplit(base).query:
            continue
        name = unquote(parsed.fragment)
        result = "reachable" if name in anchors else ("not_checked" if "anchor_ids" not in frame else "broken_fragment")
        fragment_checks.append({"label": link["label"], "href": href, "result": result})
    checks = [
        {"id": "contact", "label": "Contact route", "status": "found" if emails or phones or contact else "review",
         "detail": f"{len(emails)} email link(s), {len(phones)} phone link(s), {len(contact)} contact route(s)",
         "action": "Add a clear contact route or confirm it exists on another page."},
        {"id": "privacy", "label": "Privacy link", "status": "found" if privacy else "review",
         "detail": "Linked from this captured page" if privacy else "No privacy link found on this captured page",
         "action": "Make the privacy page discoverable where visitors expect it; verify the actual policy separately."},
        {"id": "terms", "label": "Terms link", "status": "found" if terms else "review",
         "detail": "Linked from this captured page" if terms else "No terms link found on this captured page",
         "action": "If the service needs terms, make them discoverable and verify their content separately."},
    ]
    link_probes = link_probes or []
    prototype = snapshot.get("source_kind") == "html"
    capture_network = [{"viewport": item.get("id"), **item["network_guard"]}
                       for item in frames if isinstance(item.get("network_guard"), dict)]
    return {"schema": "s2c-site-basics/v1", "audited_on": snapshot.get("audited_on"), "url": base,
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "scope": ("One offline HTML prototype, three viewport renders; scripts and external requests blocked"
                      if prototype else "One captured page, three viewport navigations, and at most eight same-origin HEAD probes"),
            "source_kind": "html" if prototype else "url",
            "capture_network": capture_network,
            "performance": [{"viewport": item.get("id"), **({} if prototype else (item.get("performance") or {}))} for item in frames],
            "checks": checks, "contact_evidence": (emails + phones + contact)[:10],
            "privacy_evidence": privacy[:5], "terms_evidence": terms[:5],
            "fragment_checks": fragment_checks, "link_probes": link_probes,
            "link_summary": {"sampled": len(link_probes),
                             "possible_broken": sum(x.get("result") == "possible_broken" for x in link_probes),
                             "broken_fragments": sum(x["result"] == "broken_fragment" for x in fragment_checks)},
            "limitations": ["Prototype upload has no live URL timing or HTTP link checks." if prototype else
                            "Navigation timings are one synthetic run, not field Core Web Vitals or a performance grade.",
                            "A missing link on this page does not prove a contact or legal page is absent sitewide.",
                            "HEAD may be blocked or handled differently from GET; 404/410 results need confirmation.",
                            "External links, query-string links, and unsampled same-origin links were not probed."]}
