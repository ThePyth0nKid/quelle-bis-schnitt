# SPDX-License-Identifier: MIT
"""Verbindung zu OBS über obs-websocket (Paket ``obsws-python``, Extra ``obs``).

Das Passwort steht nie in der Konfiguration, nur der Name einer Umgebungsvariable (``[obs] passwort_umgebung``).
Der Logger von obsws-python steht auf WARNING: auf INFO schreibt er beim Verbinden das Passwort ins Protokoll.
Alle Anfragen gehen über ``send(name, daten, raw=True)``; Tests ersetzen den Client durch eine Attrappe mit derselben
Methode.
"""
from __future__ import annotations

import logging
import os
from typing import Any, Protocol

from studio_werkzeuge.fehler import StudioFehler
from studio_werkzeuge.konfig import Konfig


class Client(Protocol):
    def send(self, param: str, data: dict | None = None, raw: bool = False) -> Any: ...


def _obsws():
    try:
        import obsws_python
    except ImportError as e:
        raise StudioFehler('obsws-python fehlt. Installieren: pip install "studio-werkzeuge[obs]"') from e
    logging.getLogger("obsws_python").setLevel(logging.WARNING)
    return obsws_python


def zugang(konfig: Konfig) -> dict:
    """Host, Port und Passwort (aus der Umgebungsvariable)."""
    name = str(konfig.wert("obs", "passwort_umgebung", "OBS_WEBSOCKET_PASSWORT"))
    return {"host": str(konfig.wert("obs", "host", "127.0.0.1")), "port": int(konfig.wert("obs", "port", 4455)),
            "password": os.environ.get(name, "")}


def verbinden(konfig: Konfig, timeout: float = 5.0) -> Client:
    obs = _obsws()
    try:
        return obs.ReqClient(**zugang(konfig), timeout=timeout)
    except Exception as e:   # obsws-python wirft je nach Lage verschiedene Fehler
        raise StudioFehler(f"OBS nicht erreichbar ({type(e).__name__}). Läuft OBS, ist der WebSocket-Server an, "
                           "stimmen Port und Passwort-Variable?") from e


def ereignis_client(konfig: Konfig, **kw) -> Any:
    return _obsws().EventClient(**zugang(konfig), **kw)


def nimmt_auf(client: Client) -> bool:
    return bool(client.send("GetRecordStatus", raw=True).get("outputActive"))


def trennen(client: Any) -> None:
    try:
        client.disconnect()
    except Exception:  # noqa: BLE001 - beim Trennen ist jeder Fehler egal
        pass
