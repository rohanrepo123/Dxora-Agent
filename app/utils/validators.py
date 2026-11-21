"""URL validation and bounded, public-only HTML fetching."""

import ipaddress
import socket
import time
from urllib.parse import urljoin, urlsplit

import certifi
import urllib3
from fastapi import HTTPException
from pydantic import HttpUrl, ValidationError


def fetch_html(url: str) -> tuple[str, bytes]:
    """Fetch a public HTTP(S) page while validating each redirect target."""
    for _ in range(5):
        try:
            checked = HttpUrl(url)
            parts = urlsplit(str(checked))
            host = parts.hostname
            port = parts.port or (443 if parts.scheme == "https" else 80)
            if parts.username or parts.password or port not in (80, 443):
                raise HTTPException(422, "Use a public HTTP(S) URL on a standard port.")

            # Pin the connection to a checked IP to prevent DNS rebinding.
            addresses = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
            ips = [ipaddress.ip_address(item[4][0]) for item in addresses]
            if not ips or any(not ip.is_global for ip in ips):
                raise HTTPException(422, "The website must use public network addresses.")
            if parts.scheme == "https":
                pool = urllib3.HTTPSConnectionPool(
                    str(ips[0]), port, server_hostname=host, assert_hostname=host,
                    cert_reqs="CERT_REQUIRED", ca_certs=certifi.where(),
                )
            else:
                pool = urllib3.HTTPConnectionPool(str(ips[0]), port)

            path = parts.path or "/"
            if parts.query:
                path += "?" + parts.query
            with pool:
                with pool.urlopen(
                    "GET", path,
                    headers={"Host": parts.netloc, "User-Agent": "WebsiteLinkAnalysis/1.0",
                             "Accept-Encoding": "identity"},
                    timeout=urllib3.Timeout(connect=4, read=5), retries=False,
                    redirect=False, preload_content=False,
                ) as response:
                    if response.status in (301, 302, 303, 307, 308):
                        location = response.headers.get("Location")
                        if not location:
                            raise HTTPException(502, "Website returned an incomplete redirect.")
                        url = urljoin(str(checked), location)
                        continue
                    if response.status != 200:
                        raise HTTPException(502, f"Website returned HTTP {response.status}.")
                    mime = response.headers.get("Content-Type", "").split(";")[0].lower()
                    if mime not in ("text/html", "application/xhtml+xml"):
                        raise HTTPException(422, "The submitted page must contain HTML.")
                    if response.headers.get("Content-Encoding", "identity").lower() != "identity":
                        raise HTTPException(422, "Website uses unsupported compressed transfer.")
                    body = bytearray()
                    deadline = time.monotonic() + 10
                    while chunk := response.read1(65536, decode_content=False):
                        body.extend(chunk)
                        if len(body) > 1_500_000:
                            raise HTTPException(422, "Website page exceeds the size limit.")
                        if time.monotonic() > deadline:
                            raise HTTPException(504, "Website transfer timed out.")
                    return str(checked), bytes(body)
        except (ValidationError, ValueError) as exc:
            raise HTTPException(422, "Invalid website or redirect URL.") from exc
        except (OSError, urllib3.exceptions.HTTPError) as exc:
            raise HTTPException(502, "Could not connect to the website securely.") from exc
    raise HTTPException(502, "Website exceeded the redirect limit.")

