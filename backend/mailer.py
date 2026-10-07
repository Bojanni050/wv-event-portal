import asyncio
import ipaddress
import logging
import os
import re
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr, formatdate, make_msgid
from html import escape, unescape
from html.parser import HTMLParser
from urllib.parse import urlparse

import httpx

logger = logging.getLogger(__name__)

# Emergent managed email proxy (constant by design).
EMAIL_BASE_URL = "https://integrations.emergentagent.com"

_SHORTENERS = ("bit.ly", "tinyurl.com", "t.co", "is.gd", "cutt.ly", "goo.gl", "rebrand.ly")
_CRED_ASK = ("reply with your password", "reply with the code", "send your password", "cvv",
             "send us your password", "enter your password below", "confirm your card number",
             "your full card number", "seed phrase", "recovery phrase", "verify your card",
             "social security number", "confirm your bank details")
_HOSTISH = re.compile(r"\b(?:https?://)?((?:[a-z0-9-]+\.)+[a-z]{2,})", re.I)


def _host_ok(host: str) -> bool:
    if not host or "xn--" in host:
        return False
    try:
        ipaddress.ip_address(host)
        return False
    except ValueError:
        pass
    return not any(host == s or host.endswith("." + s) for s in _SHORTENERS)


def _same_site(shown: str, real: str) -> bool:
    return shown == real or real.endswith("." + shown) or shown.endswith("." + real)


class _EmailScan(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags, self.urls, self.anchors = set(), [], []
        self._href, self._text = None, []

    def handle_starttag(self, tag, attrs):
        self.tags.add(tag.lower())
        self.urls += [v for k, v in attrs if k.lower() in ("href", "src") and v]
        if tag.lower() == "a":
            self._href = dict((k.lower(), v) for k, v in attrs).get("href")
            self._text = []

    def handle_data(self, data):
        if self._href is not None:
            self._text.append(data)

    def handle_endtag(self, tag):
        if tag.lower() == "a" and self._href is not None:
            self.anchors.append((self._href, "".join(self._text)))
            self._href, self._text = None, []


def _assert_safe_email(subject: str, html: str) -> None:
    scan = _EmailScan()
    scan.feed(html)
    if scan.tags & {"form", "input", "textarea", "select"}:
        raise ValueError("No forms or input fields in email (G2)")
    body = f"{subject}\n{html}".lower()
    for p in _CRED_ASK:
        if p in body:
            raise ValueError(f"Email asks the recipient for credentials: {p!r} (G2)")
    for url in scan.urls:
        low = url.strip().lower()
        if low.startswith(("mailto:", "tel:", "cid:", "#")):
            continue
        if not low.startswith("https://"):
            raise ValueError(f"Email links/assets must be absolute https: {url!r} (G3)")
        host = urlparse(low).hostname or ""
        if not _host_ok(host) or urlparse(low).username is not None:
            raise ValueError(f"Shortened, numeric-host or credential-bearing URL: {url!r} (G3)")
    for href, text in scan.anchors:
        real = urlparse(href.strip().lower()).hostname or ""
        if not real:
            continue
        for m in _HOSTISH.finditer(text):
            if not _same_site(m.group(1).lower(), real):
                raise ValueError(f"Anchor text {m.group(1)!r} ≠ real link host {real!r} (G3)")


def _send_smtp(to: str, subject: str, html: str) -> str:
    """Send via SMTP (SMTP_HOST/PORT/USER/PASSWORD/FROM). Port 465 = implicit TLS, else STARTTLS."""
    host = os.environ["SMTP_HOST"]
    port = int(os.environ.get("SMTP_PORT", "587"))
    user = os.environ.get("SMTP_USER", "")
    password = os.environ.get("SMTP_PASSWORD", "")
    sender = os.environ.get("SMTP_FROM") or user

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = formataddr((os.environ["EMAIL_FROM_NAME"], sender))
    msg["To"] = to
    msg["Date"] = formatdate(localtime=True)
    msg["Message-ID"] = make_msgid(domain=sender.split("@")[-1])
    msg.set_content(_html_to_text(html))
    msg.add_alternative(html, subtype="html")

    ctx = ssl.create_default_context()
    if port == 465:
        server = smtplib.SMTP_SSL(host, port, context=ctx, timeout=30)
    else:
        server = smtplib.SMTP(host, port, timeout=30)
        server.starttls(context=ctx)
    with server:
        if user:
            server.login(user, password)
        server.send_message(msg)
    return msg["Message-ID"]


def _html_to_text(html: str) -> str:
    text = re.sub(r"(?is)<(script|style).*?</\1>", "", html)
    text = re.sub(r"(?i)<br\s*/?>|</p>|</h[1-6]>|</tr>", "\n", text)
    text = re.sub(r'(?is)<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', r"\2 (\1)", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = unescape(text)
    return re.sub(r"\n\s*\n+", "\n\n", re.sub(r"[ \t]+", " ", text)).strip()


async def send_email(*, to: str, subject: str, html: str) -> str:
    _assert_safe_email(subject, html)
    if os.environ.get("SMTP_HOST"):
        return await asyncio.to_thread(_send_smtp, to, subject, html)
    # Fallback: Emergent managed email proxy
    payload = {"to": [to], "subject": subject, "html": html, "from_name": os.environ["EMAIL_FROM_NAME"]}
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(f"{EMAIL_BASE_URL}/api/v1/email/send",
                                 headers={"X-Email-Key": os.environ["EMERGENT_EMAIL_KEY"]}, json=payload)
    resp.raise_for_status()
    return resp.json().get("id")


def welcome_email_html(name: str, link: str, event_line: str = "") -> str:
    brand = escape(os.environ["EMAIL_FROM_NAME"])
    event_html = (f'<tr><td style="padding:20px 40px 0"><table role="presentation" cellpadding="0" cellspacing="0" '
                  f'style="border-left:2px solid #D4AF37"><tr><td style="padding:4px 0 4px 16px;font-size:20px;color:#F4F4F5">'
                  f'{escape(event_line)}</td></tr></table></td></tr>') if event_line else ""
    return (
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#09090B;padding:32px 0">'
        '<tr><td align="center"><table role="presentation" width="520" cellpadding="0" cellspacing="0" '
        'style="background:#111114;border:1px solid #27272a;font-family:Georgia,serif;color:#F4F4F5">'
        f'<tr><td style="padding:32px 40px 8px;font-family:Arial,sans-serif;font-size:12px;letter-spacing:6px;color:#D4AF37">{brand.upper()}</td></tr>'
        f'<tr><td style="padding:16px 40px 0;font-size:32px;line-height:1.15">Welkom, {escape(name)}</td></tr>'
        '<tr><td style="padding:16px 40px 0;font-family:Arial,sans-serif;font-size:15px;line-height:1.6;color:#d4d4d8">'
        f'Je persoonlijke event-omgeving bij {brand} staat klaar. Hier bereid je samen met je DJ alles voor: '
        'muziekwensen, het draaischema, je uitnodiging en een directe chat.</td></tr>'
        f'{event_html}'
        '<tr><td style="padding:20px 40px 0;font-family:Arial,sans-serif;font-size:15px;line-height:1.6;color:#d4d4d8">'
        'Kies eerst je eigen wachtwoord via de knop hieronder. De link is 7 dagen geldig en werkt één keer.</td></tr>'
        f'<tr><td style="padding:28px 40px"><a href="{escape(link)}" style="display:inline-block;background:#D4AF37;color:#000;'
        'font-family:Arial,sans-serif;font-weight:bold;font-size:14px;text-decoration:none;padding:14px 28px;border-radius:999px">'
        'Wachtwoord instellen</a></td></tr>'
        '<tr><td style="padding:0 40px 32px;font-family:Arial,sans-serif;font-size:12px;line-height:1.6;color:#71717a">'
        'Link verlopen? Gebruik "Wachtwoord vergeten" op het inlogscherm. '
        f'Verzonden door {brand}. We vragen nooit om je wachtwoord per e-mail.</td></tr>'
        '</table></td></tr></table>'
    )


def reset_email_html(name: str, link: str) -> str:
    brand = escape(os.environ["EMAIL_FROM_NAME"])
    return (
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#09090B;padding:32px 0">'
        '<tr><td align="center"><table role="presentation" width="520" cellpadding="0" cellspacing="0" '
        'style="background:#111114;border:1px solid #27272a;font-family:Georgia,serif;color:#F4F4F5">'
        f'<tr><td style="padding:32px 40px 8px;font-family:Arial,sans-serif;font-size:12px;letter-spacing:6px;color:#D4AF37">{brand.upper()}</td></tr>'
        f'<tr><td style="padding:16px 40px 0;font-size:30px;line-height:1.2">Nieuw wachtwoord instellen</td></tr>'
        f'<tr><td style="padding:16px 40px 0;font-family:Arial,sans-serif;font-size:15px;line-height:1.6;color:#d4d4d8">'
        f'Hoi {escape(name)},<br><br>We kregen een verzoek om het wachtwoord van je {brand}-account opnieuw in te stellen. '
        'Klik op de knop hieronder om een nieuw wachtwoord te kiezen. De link is 1 uur geldig en werkt één keer.</td></tr>'
        f'<tr><td style="padding:28px 40px"><a href="{escape(link)}" style="display:inline-block;background:#D4AF37;color:#000;'
        'font-family:Arial,sans-serif;font-weight:bold;font-size:14px;text-decoration:none;padding:14px 28px;border-radius:999px">'
        'Wachtwoord instellen</a></td></tr>'
        '<tr><td style="padding:0 40px 32px;font-family:Arial,sans-serif;font-size:12px;line-height:1.6;color:#71717a">'
        'Heb je dit niet aangevraagd? Dan kun je deze e-mail negeren; je wachtwoord blijft ongewijzigd. '
        f'Verzonden door {brand}. We vragen nooit om je wachtwoord per e-mail.</td></tr>'
        '</table></td></tr></table>'
    )
