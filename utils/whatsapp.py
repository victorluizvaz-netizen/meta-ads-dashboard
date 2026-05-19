"""
Envio de mensagens via Evolution API (WhatsApp).
"""
import base64
import requests


def send_message(base_url: str, instance: str, apikey: str, number: str, text: str) -> bool:
    """Envia mensagem de texto. number sem '+', ex: '5511999999999'."""
    url = f"{base_url.rstrip('/')}/message/sendText/{instance}"
    headers = {"apikey": apikey, "Content-Type": "application/json"}
    try:
        r = requests.post(url, json={"number": number, "text": text}, headers=headers, timeout=15)
        if r.status_code not in (200, 201):
            print(f"[WhatsApp] HTTP {r.status_code} — {r.text[:200]}")
        return r.status_code in (200, 201)
    except Exception as e:
        print(f"[WhatsApp] Falha ao enviar para {url}: {e}")
        return False


def send_document(base_url: str, instance: str, apikey: str, number: str,
                  pdf_bytes: bytes, filename: str, caption: str = "") -> bool:
    """Envia documento PDF via Evolution API (base64)."""
    url = f"{base_url.rstrip('/')}/message/sendMedia/{instance}"
    headers = {"apikey": apikey, "Content-Type": "application/json"}
    payload = {
        "number":    number,
        "mediatype": "document",
        "mimetype":  "application/pdf",
        "media":     base64.b64encode(pdf_bytes).decode(),
        "fileName":  filename,
        "caption":   caption,
    }
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=30)
        if r.status_code not in (200, 201):
            print(f"[WhatsApp] HTTP {r.status_code} — {r.text[:200]}")
        return r.status_code in (200, 201)
    except Exception as e:
        print(f"[WhatsApp] Falha ao enviar documento para {url}: {e}")
        return False
