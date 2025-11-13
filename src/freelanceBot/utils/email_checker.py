# email_checker.py
# Robuster E-Mail-Finder für <local>@<domain> auf Websites.
# - Parallele Requests + früher Abbruch
# - Extraktion aus mailto:, Text, JSON-LD, Roh-HTML, Cloudflare-Obfuskation
# - iframes (gleiche registrierbare Domain)
# - Reihenfolge der local_parts wird respektiert (Liste, kein Set!)
# - strict_domain=True: Nur exakte '@<domain>'-Mails zählen

from __future__ import annotations

import re
import html
import json
import binascii
import asyncio
import unicodedata
from typing import Iterable, Optional, Tuple, Set, List, Dict, Any
from urllib.parse import urljoin, urlparse

import aiohttp
from bs4 import BeautifulSoup

# ========================= Konfiguration =====================================

# Beispiel-Default (optional): Reihenfolge = Priorität
EMAIL_PARTS_DEFAULT: List[str] = [
    "info", "kontakt", "contact", "freelancer", "freelance",
    "inbox", "recruiting", "bewerbung", "application", "applications", "projects",
    "hello", "hi", "office", "mail", "post", "team",
    "sales", "vertrieb", "business", "b2b", "partner", "alliances",
    "jobs", "career", "karriere", "hr", "humanresources"
]

HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/124.0 Safari/537.36"),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
}
REQUEST_TIMEOUT_SECONDS = 6      # total Timeout
CONNECT_TIMEOUT_SECONDS = 3
READ_TIMEOUT_SECONDS = 5
MAX_CONCURRENCY = 6              # parallele Requests pro Domain
MAX_BYTES = 900_000              # bis zu 900 KB lesen
MAX_IFRAMES_PER_PAGE = 3         # nur einige iframes verfolgen (gleiche Domain)
DEBUG = False                    # True = Logging

# ========================= Hilfs-Regex/Utils =================================

ANY_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b")
ZERO_WIDTH = ["\u200b", "\u200c", "\u200d", "\u2060", "\ufeff"]
ZW_RE = re.compile("|".join(map(re.escape, ZERO_WIDTH)))
OBFUSCATION_PATTERNS = [
    (re.compile(r"\s*\[\s*at\s*\]\s*", re.I), "@"),
    (re.compile(r"\s*\(\s*at\s*\)\s*", re.I), "@"),
    (re.compile(r"\s+at\s+", re.I), "@"),
    (re.compile(r"\s*\{\s*at\s*\}\s*", re.I), "@"),
    (re.compile(r"\s*\[\s*dot\s*\]\s*", re.I), "."),
    (re.compile(r"\s*\(\s*dot\s*\)\s*", re.I), "."),
    (re.compile(r"\s+dot\s+", re.I), "."),
    (re.compile(r"\s*\{\s*dot\s*\}\s*", re.I), "."),
]

def _normalize_domain(d: str) -> str:
    d = d.strip().lower()
    d = re.sub(r"^https?://", "", d)
    d = re.sub(r"^www\.", "", d)
    return d.split("/")[0]

def _same_reg_domain(url: str, domain: str) -> bool:
    """Erlaubt iframes nur auf gleicher registrierbarer Domain (Subdomains ok)."""
    try:
        host = urlparse(url).hostname or ""
    except Exception:
        return False
    host = host.lower()
    return host == domain or host.endswith("." + domain)

def _candidate_emails(domain: str, local_parts: Iterable[str]) -> List[str]:
    parts = list(local_parts)  # Reihenfolge stabilisieren
    return [f"{lp.strip()}@{domain}".lower() for lp in parts if lp and lp.strip()]

def _decode_cfemail(hex_str: str) -> Optional[str]:
    """Cloudflare E-Mail-Obfuskation: <a class='__cf_email__' data-cfemail='...'>."""
    try:
        data = binascii.unhexlify(hex_str)
    except binascii.Error:
        return None
    if not data:
        return None
    key = data[0]
    decoded = bytes([b ^ key for b in data[1:]])
    s = decoded.decode("utf-8", errors="ignore")
    return s if "@" in s else None

def _clean_text(t: str) -> str:
    t = html.unescape(t)
    t = ZW_RE.sub("", t)
    t = unicodedata.normalize("NFKC", t)
    for pat, repl in OBFUSCATION_PATTERNS:
        t = pat.sub(repl, t)
    t = re.sub(r"\s+", " ", t)
    return t

# ========================= Extraktion aus HTML ===============================

def _json_splits(s: str) -> List[str]:
    # Primitive Heuristik, falls mehrere JSON-Objekte in einem Script stehen
    items: List[str] = []
    buf = ""
    depth = 0
    for ch in s or "":
        buf += ch
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and buf.strip():
                items.append(buf)
                buf = ""
    if buf.strip():
        items.append(buf)
    return items

def _jsonld_emails(obj: Any) -> Set[str]:
    out: Set[str] = set()
    def walk(v):
        nonlocal out
        if isinstance(v, dict):
            for k, val in v.items():
                if isinstance(val, str):
                    for m in ANY_EMAIL_RE.findall(val):
                        out.add(m.lower())
                if k.lower() in {"email", "e-mail"} and isinstance(val, str) and "@" in val:
                    out.add(val.strip().lower())
                elif k.lower() in {"contactpoint", "contactpoints"}:
                    walk(val)
                else:
                    walk(val)
        elif isinstance(v, list):
            for it in v:
                walk(it)
        elif isinstance(v, str):
            for m in ANY_EMAIL_RE.findall(v):
                out.add(m.lower())
    walk(obj)
    return out

def _extract_emails_from_jsonld(soup: BeautifulSoup) -> Set[str]:
    out: Set[str] = set()
    for tag in soup.find_all("script", type=lambda v: v and "ld+json" in v):
        try:
            payload = tag.string or ""
            for chunk in _json_splits(payload):
                data = json.loads(chunk)
                out |= _jsonld_emails(data)
        except Exception:
            continue
    return out

def _extract_emails_from_html(
    html_str: str,
    base_url: str,
    domain: str,
    *,
    strict_domain: bool = True
) -> Tuple[Set[str], List[str], Dict[str, Any]]:
    """
    Liefert (emails_set, iframe_urls, debug_info).
    Verbesserungen:
      - sichere Erkennung von mailto:, auch bei verschachtelten <a>-Tags
      - JSON-LD-Scan
      - Fallback: Suche direkt im Roh-HTML nach mailto: und E-Mails
      - priorisiert E-Mails der exakt gleichen Domain (strict_domain=True)
    """
    out: Set[str] = set()
    iframe_urls: List[str] = []
    soup = BeautifulSoup(html_str, "html.parser")

    # Cloudflare data-cfemail
    for el in soup.select("a.__cf_email__, span.__cf_email__"):
        hex_str = el.get("data-cfemail")
        if hex_str:
            decoded = _decode_cfemail(hex_str.strip())
            if decoded:
                out.add(decoded.lower())

    # Alle <a> (Wix kann verschachtelte <a>-Tags erzeugen)
    for a in soup.find_all("a"):
        href = a.get("href", "") or ""
        if href.lower().startswith("mailto:"):
            mail = href.split("mailto:", 1)[-1].split("?", 1)[0].strip()
            if mail:
                out.add(html.unescape(mail).lower())

    # JSON-LD
    out |= _extract_emails_from_jsonld(soup)

    # Reiner Text (bereinigt)
    text = _clean_text(soup.get_text(separator=" ", strip=True))
    out.update(m.lower() for m in ANY_EMAIL_RE.findall(text))

    # Labels (reduziert False-Positives in Kontaktbereichen)
    for lbl in soup.find_all(string=re.compile(r"e-?mail|kontakt|contact|impressum", re.I)):
        try:
            seg = _clean_text(lbl.parent.get_text(" ", strip=True))
            out.update(m.lower() for m in ANY_EMAIL_RE.findall(seg))
        except Exception:
            pass

    # iframes (gleiche registrierbare Domain) limitieren
    for ifr in soup.find_all("iframe"):
        src = (ifr.get("src") or "").strip()
        if not src:
            continue
        full = urljoin(base_url, src)
        if _same_reg_domain(full, domain):
            iframe_urls.append(full)
            if len(iframe_urls) >= MAX_IFRAMES_PER_PAGE:
                break

    # Fallback direkt auf dem Roh-HTML (wichtig für Builder-Seiten)
    # mailto:
    for m in re.findall(r'(?i)href\s*=\s*"(?:mailto:)\s*([^"?"]+)"', html_str):
        out.add(html.unescape(m).strip().lower())
    for m in re.findall(r"(?i)href\s*=\s*'(?:mailto:)\s*([^'?']+)'", html_str):
        out.add(html.unescape(m).strip().lower())
    # generische E-Mails
    out.update(m.lower() for m in ANY_EMAIL_RE.findall(html_str))

    # Domain-Priorisierung
    if strict_domain:
        same = {e for e in out if e.endswith(f"@{domain}")}
        if same:
            out = same

    dbg = {
        "base_url": base_url,
        "emails_extracted": sorted(out),
        "iframe_candidates": iframe_urls[:],
        "text_len": len(text),
    }
    return out, iframe_urls, dbg

# ========================= Networking ========================================

async def _fetch(
    session: aiohttp.ClientSession,
    url: str,
    *,
    referer: Optional[str] = None
) -> Tuple[Optional[str], Dict[str, Any]]:
    meta: Dict[str, Any] = {"url": url}
    try:
        headers = {}
        if referer:
            headers["Referer"] = referer

        async with session.get(url, allow_redirects=True, headers=headers) as r:
            ctype = r.headers.get("Content-Type", "")
            meta.update({
                "status": r.status,
                "content_type": ctype,
            })
            if DEBUG:
                print("GET", url, r.status, ctype)
            if r.status >= 400 or "text/html" not in (ctype or ""):
                return None, meta
            raw = await r.content.read(MAX_BYTES)
            encoding = r.charset or "utf-8"
            try:
                text = raw.decode(encoding, errors="ignore")
            except LookupError:
                text = raw.decode("utf-8", errors="ignore")
            meta["bytes"] = len(raw)
            meta["chars"] = len(text)
            return text, meta
    except (aiohttp.ClientError, asyncio.TimeoutError) as e:
        meta["error"] = repr(e)
        if DEBUG:
            print("ERR", url, repr(e))
        return None, meta

# ========================= Kernlogik (async) =================================

async def find_email_on_website_async(
    domain: str,
    local_parts: Iterable[str],
    *,
    headers: Optional[dict] = None,
    extra_paths: Optional[Iterable[str]] = None,
    strict_domain: bool = True,
    return_debug: bool = False,
) -> Optional[str] | Tuple[Optional[str], List[Dict[str, Any]]]:
    """
    Liefert die erste passende E-Mail aus local_parts@domain (Reihenfolge wird respektiert).
    strict_domain=True  -> Nur E-Mails mit exakt '@<domain>' zählen.
    return_debug=True   -> gibt (result, debug_logs) zurück.
    """
    domain = _normalize_domain(domain)
    if not domain or "." not in domain:
        raise ValueError("Bitte eine gültige Domain wie 'example.com' übergeben.")

    candidates = _candidate_emails(domain, local_parts)
    if not candidates:
        return (None, []) if return_debug else None

    # Kontakt-/Impressum-Pfade (mit/ohne Slash) – priorisiert
    base_paths = [
        "", "kontakt", "kontakt/", "impressum", "impressum/",
        "imprint", "imprint/", "contact", "contact/",
        "about", "team", "datenschutz", "datenschutz/",
        "privacy", "privacy/",
        "de/impressum", "de/impressum/", "de/kontakt", "de/kontakt/",
        "en/contact", "en/contact/", "en/privacy", "en/privacy/",
        "legal-notice", "legal-notice/", "legal", "legal/",
    ]
    if extra_paths:
        seen = set()
        merged: List[str] = []
        for p in [*base_paths, *extra_paths]:
            if p not in seen:
                merged.append(p)
                seen.add(p)
        base_paths = merged

    https_bases = [f"https://{domain}/", f"https://www.{domain}/"]
    http_bases  = [f"http://{domain}/",  f"http://www.{domain}/"]

    timeout_ctx = aiohttp.ClientTimeout(
        total=REQUEST_TIMEOUT_SECONDS,
        sock_connect=CONNECT_TIMEOUT_SECONDS,
        sock_read=READ_TIMEOUT_SECONDS
    )
    session_headers = headers or HEADERS

    debug_logs: List[Dict[str, Any]] = []

    async def _scan_with_bases(bases) -> Optional[str]:
        urls = [urljoin(b, p) for b in bases for p in base_paths]
        urls = list(dict.fromkeys(urls))  # dedupe, Reihenfolge erhalten

        found: Set[str] = set()
        stop_event = asyncio.Event()
        sem = asyncio.Semaphore(MAX_CONCURRENCY)

        async with aiohttp.ClientSession(timeout=timeout_ctx, headers=session_headers, raise_for_status=False) as session:
            async def worker(url: str) -> Tuple[str, Optional[Set[str]]]:
                if stop_event.is_set():
                    return (url, None)
                async with sem:
                    html_str, meta = await _fetch(session, url)
                debug_logs.append({"phase": "page", **meta})
                if not html_str or stop_event.is_set():
                    return (url, None)

                emails, iframes, dbg = _extract_emails_from_html(html_str, url, domain, strict_domain=strict_domain)
                debug_logs.append({"phase": "extract", **dbg})

                # iframes der gleichen Domain nachziehen
                for iframe_url in iframes:
                    if stop_event.is_set():
                        break
                    iframe_html, imeta = await _fetch(session, iframe_url, referer=url)
                    debug_logs.append({"phase": "iframe", **imeta})
                    if not iframe_html:
                        continue
                    iframe_emails, _, idbg = _extract_emails_from_html(iframe_html, iframe_url, domain, strict_domain=strict_domain)
                    debug_logs.append({"phase": "extract_iframe", **idbg})
                    emails |= iframe_emails

                if not emails:
                    return (url, set())
                return (url, emails)

            tasks = [asyncio.create_task(worker(u)) for u in urls]

            try:
                for coro in asyncio.as_completed(tasks):
                    url, emails = await coro
                    if emails is None:
                        continue
                    if emails:
                        found.update(e.lower() for e in emails)
                        # respektiere Kandidaten-Reihenfolge
                        for cand in candidates:
                            if cand in found:
                                if DEBUG:
                                    print("FOUND", cand, "on", url)
                                stop_event.set()
                                for t in tasks:
                                    if not t.done():
                                        t.cancel()
                                return cand
                return None
            finally:
                for t in tasks:
                    if not t.done():
                        t.cancel()
                await asyncio.gather(*tasks, return_exceptions=True)

    # 1) HTTPS bevorzugt
    result = await _scan_with_bases(https_bases)
    if not result:
        # 2) Fallback auf HTTP
        result = await _scan_with_bases(http_bases)

    if return_debug:
        return result, debug_logs
    return result

# ========================= Sync-Wrapper ======================================

def find_email_on_website(
    domain: str,
    local_parts: Iterable[str],
    **kwargs,
) -> Optional[str]:
    """
    Sync-Wrapper: ruft die async-Variante sicher auf.
    Nutzt asyncio.run, sofern kein Event-Loop läuft.
    """
    try:
        # Wenn ein Loop läuft (Jupyter/Streamlit), erzwingt das hier normalerweise eine Exception,
        # die wir unten abfangen: Dann nutzen wir asyncio.run (kein Loop) oder eine alternative Strategie.
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        # In Umgebungen mit aktivem Event-Loop: Task erstellen und blockierend warten
        # Hinweis: In "normalen" Skripten (Pandas-Batch) gibt es meist KEINEN aktiven Loop.
        return loop.run_until_complete(find_email_on_website_async(domain, local_parts, **kwargs))  # type: ignore[attr-defined]
    else:
        return asyncio.run(find_email_on_website_async(domain, local_parts, **kwargs))

# ========================= CLI / Beispiel ====================================

if __name__ == "__main__":
    # Kurzer Test (Bluechilled-Beispiel – sollte info@bluechilled-group.de finden)
    DEBUG = True
    res, logs = asyncio.run(find_email_on_website_async(
        "bluechilled-group.de",
        local_parts=["info", "kontakt", "contact"],
        extra_paths=["kontakt", "kontakt/", "impressum", "impressum/"],
        strict_domain=True,
        return_debug=True,
    ))
    print("RESULT:", res)
    for entry in logs[:10]:
        print(entry)
