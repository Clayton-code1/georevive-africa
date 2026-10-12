"""Polite HTTP client: identifies itself, obeys robots.txt, rate-limits per host,
backs off on 429/5xx (honouring Retry-After), caches downloads, and records every
URL it tries so the Source Registry can show what was attempted."""

from __future__ import annotations

import time
import urllib.robotparser
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests


class RobotsDisallowed(Exception):
    pass


class PoliteHttp:
    def __init__(self, user_agent: str, timeout: float = 60, min_interval: float = 1.0) -> None:
        self.ua = user_agent
        self.timeout = timeout
        self.min_interval = min_interval
        self.session = requests.Session()
        self.session.headers["User-Agent"] = user_agent
        self._last: dict[str, float] = {}
        self._robots: dict[str, urllib.robotparser.RobotFileParser | None] = {}
        self.log: list[dict[str, str]] = []

    # robots.txt ---------------------------------------------------------------
    def robots_allowed(self, url: str) -> bool:
        p = urlparse(url)
        base = f"{p.scheme}://{p.netloc}"
        if base not in self._robots:
            rp = urllib.robotparser.RobotFileParser()
            try:
                r = self.session.get(base + "/robots.txt", timeout=20)
                if r.status_code in (401, 403):
                    rp.disallow_all = True
                elif r.status_code >= 400:
                    rp.allow_all = True
                else:
                    rp.parse(r.text.splitlines())
                self._robots[base] = rp
            except requests.RequestException:
                # robots.txt unreachable: treat as no robots policy (RFC 9309 s.2.3.1.3 for 4xx;
                # for network errors we proceed but the request itself will most likely fail too)
                self._robots[base] = None
        rp = self._robots[base]
        return True if rp is None else rp.can_fetch(self.ua, url)

    def _wait(self, url: str) -> None:
        host = urlparse(url).netloc
        last = self._last.get(host, 0.0)
        delta = time.monotonic() - last
        if delta < self.min_interval:
            time.sleep(self.min_interval - delta)
        self._last[host] = time.monotonic()

    def note(self, url: str, result: str) -> None:
        self.log.append({"url": url, "result": result})

    # requests -----------------------------------------------------------------
    def request(
        self, method: str, url: str, *, check_robots: bool = True, retries: int = 3, **kw: Any
    ) -> requests.Response:
        if check_robots and not self.robots_allowed(url):
            self.note(url, "skipped: disallowed by robots.txt")
            raise RobotsDisallowed(f"robots.txt disallows {url}")
        kw.setdefault("timeout", self.timeout)
        attempt = 0
        while True:
            self._wait(url)
            try:
                r = self.session.request(method, url, **kw)
            except requests.RequestException as e:
                attempt += 1
                if attempt > retries:
                    self.note(url, f"error: {type(e).__name__}: {e}"[:300])
                    raise
                time.sleep(2**attempt)
                continue
            if r.status_code in (429, 500, 502, 503, 504) and attempt < retries:
                attempt += 1
                ra = r.headers.get("Retry-After")
                delay = float(ra) if ra and ra.isdigit() else 2**attempt * 2
                time.sleep(min(delay, 120))
                continue
            self.note(url, f"HTTP {r.status_code}")
            return r

    def get(self, url: str, **kw: Any) -> requests.Response:
        return self.request("GET", url, **kw)

    def post(self, url: str, **kw: Any) -> requests.Response:
        return self.request("POST", url, **kw)

    def get_json(self, url: str, **kw: Any) -> Any:
        r = self.get(url, **kw)
        r.raise_for_status()
        return r.json()

    def download(
        self,
        url: str,
        dest: Path,
        *,
        force: bool = False,
        max_bytes: int | None = None,
        check_robots: bool = True,
        **kw: Any,
    ) -> Path:
        """Download to dest (cached: skipped if dest already exists and is non-empty)."""
        dest = Path(dest)
        if dest.exists() and dest.stat().st_size > 0 and not force:
            self.note(url, f"cached: {dest.name}")
            return dest
        dest.parent.mkdir(parents=True, exist_ok=True)
        r = self.request("GET", url, stream=True, check_robots=check_robots, **kw)
        r.raise_for_status()
        clen = r.headers.get("Content-Length")
        if max_bytes and clen and int(clen) > max_bytes:
            r.close()
            raise ValueError(f"{url} is {int(clen) / 1e6:.0f} MB, above the {max_bytes / 1e6:.0f} MB limit")
        tmp = dest.with_suffix(dest.suffix + ".part")
        n = 0
        with open(tmp, "wb") as f:
            for chunk in r.iter_content(1 << 16):
                n += len(chunk)
                if max_bytes and n > max_bytes:
                    f.close()
                    tmp.unlink(missing_ok=True)
                    raise ValueError(f"{url} exceeded the {max_bytes / 1e6:.0f} MB limit")
                f.write(chunk)
        tmp.replace(dest)
        return dest
