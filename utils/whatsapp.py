"""
Envio de mensagens via Evolution API (WhatsApp).
"""
import requests


def send_message(base_url: str, instance: str, apikey: str, number: str, text: str) -> bool:
    """
    Envia mensagem de texto via Evolution API.
    number: número no formato internacional sem '+', ex: '5511999999999'
    Retorna True se enviado com sucesso.
    """
    url = f"{base_url.rstrip('/')}/message/sendText/{instance}"
    headers = {"apikey": apikey, "Content-Type": "application/json"}
    payload = {"number": number, "text": text}
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=15)
        if r.status_code not in (200, 201):
            print(f"[WhatsApp] HTTP {r.status_code} — URL: {url} — Resposta: {r.text[:200]}")
        return r.status_code in (200, 201)
    except Exception as e:
        print(f"[WhatsApp] Falha ao enviar para {url}: {e}")
        return False
