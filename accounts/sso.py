"""Client CAS 2 minimal untuk SSO UI (tanpa dependency tambahan selain requests)."""
import xml.etree.ElementTree as ET
from urllib.parse import urlencode

import requests
from django.conf import settings

CAS_NS = {"cas": "http://www.yale.edu/tp/cas"}


def get_login_url(service_url: str) -> str:
    return f"{settings.SSO_UI_URL}login?{urlencode({'service': service_url})}"


def validate_ticket(ticket: str, service_url: str):
    """
    Validasi ticket ke SSO UI.
    Return dict {"username": ..., "attributes": {...}} kalau sukses, None kalau gagal.
    Raise requests.RequestException / ET.ParseError kalau server SSO bermasalah.
    """
    resp = requests.get(
        f"{settings.SSO_UI_URL}serviceValidate",
        params={"ticket": ticket, "service": service_url},
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; Pinjemin/1.0)",
            "Accept": "application/xml, text/xml, */*",
        },
        timeout=10,
    )
    resp.raise_for_status()

    root = ET.fromstring(resp.content)
    success = root.find("cas:authenticationSuccess", CAS_NS)
    if success is None:
        return None

    username = success.findtext("cas:user", namespaces=CAS_NS)
    attributes = {}
    attr_node = success.find("cas:attributes", CAS_NS)
    if attr_node is not None:
        for child in attr_node:
            # "{namespace}npm" -> "npm"
            attributes[child.tag.split("}")[-1]] = (child.text or "").strip()

    return {"username": username, "attributes": attributes}
