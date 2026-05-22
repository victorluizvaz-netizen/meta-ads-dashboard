from datetime import datetime, timezone, timedelta

_BR = timezone(timedelta(hours=-3))


def now_br() -> datetime:
    """Retorna datetime atual no fuso de Brasília (GMT-3), sem tzinfo."""
    return datetime.now(_BR).replace(tzinfo=None)
