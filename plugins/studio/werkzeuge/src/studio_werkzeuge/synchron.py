# SPDX-License-Identifier: MIT
"""Reine Rechenfunktionen für das Zwei-Kamera-Paar (kein Dateizugriff).

OBS startet die Source-Record-Ausgaben zweier Kameras nacheinander: Kamera B beginnt einige Bilder nach Kamera A,
je Take anders. Der Ton (beide Dateien tragen dieselbe Mikrofonspur) misst diesen Versatz im OBS-Takt. Laufen die
Kameras frei (ohne Genlock), wandert ihre Phase gegenüber dem OBS-Takt; dieselbe Bewegung liegt dann 0 oder 1 Bild
neben dem Ton-Versatz. Darum:

* Bewegung eindeutig → ausgerichtet nach dem Bild, der Ton ist die Gegenprobe (höchstens ±1,5 Bilder).
* Bewegung nicht eindeutig (kurzer oder ruhiger Take) → nach dem Ton, Genauigkeit ±1 Bild.
* Reicht auch der Ton nicht, die Bildzahl (OBS stoppt beide Ausgaben im selben Moment).

Schwellen: eigene Messung, Methode in docs/messungen/studio-zwei-kamera.md.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.signal import correlate

from studio_werkzeuge.fehler import KeinTon, StudioFehler, ZuKurzeUeberlappung

AAC_BLOCK_S = 1024 / 48_000       # OBS setzt den Tonanfang einer Datei nur auf ganze AAC-Blöcke genau
MAX_BLOECKE = 2                   # Suchraum der Zerlegung
M0_TOLERANZ_S = 0.002             # ein reiner Bild-Versatz gewinnt, solange sein Rest unter 2 ms liegt
REST_WARNUNG_S = 0.004            # größerer Rest: der Ton passt zu keinem Bildraster
DRIFT_WARNUNG_S = 0.005
STILLE_RMS = 1e-4                 # darunter gilt ein Signal als stumm
NEBENMAX_ABSTAND_S = 0.1          # Nebenmaximum: alles außerhalb ±0,1 s um das Hauptmaximum
KONFIDENZ_WARNUNG = 0.3           # normierte Korrelation darunter = Zweifel
MAX_AUFFUELLEN = 3                # mehr geklonte Endbilder hieße: die Dateien gehören nicht zusammen
BEWEGUNG_MIN_BILDER = 250         # unter 10 s (bei 25 fps) ist die Bewegung zu kurz für eine Messung
BILDZAHL_LUECKE_MAX = 25          # eigene Messung: B startete 3–18 Bilder nach A (studio-zwei-kamera.md)
BEWEGUNG_GIPFEL_MIN = 0.25        # eigene Messung: echte Treffer 0,30–0,79, Fehlalarme 0,14–0,28
BEWEGUNG_NEBEN_MAX = 0.7          # zweitbester Gipfel relativ zum besten; darüber mehrdeutig
MAX_PHASE_BILDER = 1.5            # Bild gegen Ton: mehr kann die Kamera-Phase nicht erklären
STANDBILD_SCHWELLE = 0.05         # mittlere Graustufen-Differenz, darunter gilt ein Bild als unbewegt
STANDBILD_ANTEIL = 0.95           # so viele unbewegte Bilder = Standbild (Kamera aus, kein Signal?)


@dataclass(frozen=True)
class Versatz:
    """Wo ein Muster in der Referenz beginnt (Sekunden), wie sauber (0..1) und wie eindeutig (Nebenmaximum 0..1)."""

    lag_s: float
    konfidenz: float
    nebenmaximum: float


@dataclass(frozen=True)
class Zerlegung:
    """Ton-Versatz d = bilder/fps + bloecke·AAC-Block + rest_s. ``bilder`` > 0: Kamera B startete später."""

    bilder: int
    bloecke: int
    rest_s: float


@dataclass(frozen=True)
class Plan:
    """Kamera A bleibt (Stream-Copy, ``bilder`` = ihre Bildzahl); B wird neu kodiert und auf A gelegt: ``vorne`` > 0
    Standbilder davor, < 0 so viele Bilder vorne weg; ``auffuellen`` Endbilder geklont. ``frueh``: wer früher lief."""

    frueh: str
    vorne: int
    bilder: int
    auffuellen: int


@dataclass(frozen=True)
class Bewegung:
    """Ergebnis der Bewegungs-Korrelation: Lage (Bilder), Gipfel (0..1), Nebenmaximum relativ zum Gipfel, Bildzahl."""

    lage: float | None
    gipfel: float
    neben: float
    bilder: int

    @property
    def aussagekraeftig(self) -> bool:
        return (self.lage is not None and self.gipfel >= BEWEGUNG_GIPFEL_MIN and self.neben <= BEWEGUNG_NEBEN_MAX
                and self.bilder >= BEWEGUNG_MIN_BILDER)


@dataclass(frozen=True)
class Entscheidung:
    """Die Lücke in Bildern, woher sie kommt (bild/ton/bildzahl), ob das Paar rot ist, und warum."""

    bilder: int
    quelle: str
    rot: bool
    warnungen: tuple[str, ...]
    hinweise: tuple[str, ...]


def _rms(x: np.ndarray) -> float:
    return float(np.sqrt(np.mean(np.square(x, dtype=np.float64)))) if x.size else 0.0


def versatz_finden(referenz: np.ndarray, muster: np.ndarray, rate_hz: int, min_ueberlappung_s: float = 3.0,
                   min_lag_s: float | None = None) -> Versatz:
    """Wo beginnt ``muster`` in ``referenz``? Kreuzkorrelation (FFT) über alle Lagen mit mindestens
    ``min_ueberlappung_s`` Überlappung. Negative Lage: das Muster beginnt vor der Referenz."""
    ref = np.asarray(referenz, dtype=np.float32)
    seg = np.asarray(muster, dtype=np.float32)
    if ref.ndim != 1 or seg.ndim != 1:
        raise ValueError("Referenz und Muster müssen eindimensional (mono) sein.")
    if rate_hz <= 0:
        raise ValueError("rate_hz muss positiv sein.")
    min_ov = int(round(min_ueberlappung_s * rate_hz))
    if min_ov < 1:
        raise ValueError("min_ueberlappung_s muss mindestens einen Abtastwert ergeben.")
    if len(seg) < min_ov or len(ref) < min_ov:
        raise ZuKurzeUeberlappung(f"Zu wenig Ton zum Vergleichen: Referenz {len(ref) / rate_hz:.2f} s, Muster "
                                  f"{len(seg) / rate_hz:.2f} s, nötig sind {min_ueberlappung_s:.1f} s.")
    if _rms(ref) < STILLE_RMS:
        raise KeinTon("Die Referenz ist stumm.")
    if _rms(seg) < STILLE_RMS:
        raise KeinTon("Das Muster ist stumm.")
    ref_n = ref - np.float32(ref.mean())
    seg_n = seg - np.float32(seg.mean())
    corr = correlate(ref_n, seg_n, mode="full", method="fft")
    lag_lo, lag_hi = min_ov - len(seg), len(ref) - min_ov
    if min_lag_s is not None:
        lag_lo = max(lag_lo, int(round(min_lag_s * rate_hz)))
    if lag_lo > lag_hi:
        raise ZuKurzeUeberlappung("Keine zulässige Lage mit genug Überlappung.")
    versatz_i = len(seg) - 1
    betrag = np.abs(corr[lag_lo + versatz_i: lag_hi + versatz_i + 1])
    best_i = int(np.argmax(betrag))
    lag = lag_lo + best_i
    a0, a1 = max(lag, 0), min(lag + len(seg), len(ref))
    a, b = ref_n[a0:a1], seg_n[a0 - lag:a1 - lag]
    nenner = float(np.linalg.norm(a)) * float(np.linalg.norm(b))
    konfidenz = abs(float(np.dot(a, b)) / nenner) if nenner > 0 else 0.0
    abstand = int(round(NEBENMAX_ABSTAND_S * rate_hz))
    maske = np.ones(len(betrag), dtype=bool)
    maske[max(0, best_i - abstand): best_i + abstand + 1] = False
    haupt = float(betrag[best_i])
    nebenmaximum = float(betrag[maske].max() / haupt) if maske.any() and haupt > 0 else 0.0
    return Versatz(lag / rate_hz, konfidenz, nebenmaximum)


def versatz_zerlegen(d_s: float, fps: float, max_bloecke: int = MAX_BLOECKE) -> Zerlegung:
    """Den Ton-Versatz in ganze Bilder plus AAC-Blöcke zerlegen. Ein reiner Bild-Versatz hat Vorrang, solange sein
    Rest unter ``M0_TOLERANZ_S`` liegt; sonst gewinnt der kleinste Rest (bei Gleichstand weniger Blöcke)."""
    if fps <= 0:
        raise ValueError("fps muss positiv sein.")
    bild_s = 1.0 / fps
    kandidaten = []
    for m in range(-max_bloecke, max_bloecke + 1):
        k = round((d_s - m * AAC_BLOCK_S) / bild_s)
        kandidaten.append(Zerlegung(k, m, d_s - m * AAC_BLOCK_S - k * bild_s))
    rein = next(z for z in kandidaten if z.bloecke == 0)
    if abs(rein.rest_s) <= M0_TOLERANZ_S:
        return rein
    return min(kandidaten, key=lambda z: (abs(z.rest_s), abs(z.bloecke)))


def plan_bauen(k: int, bilder_a: int, bilder_b: int) -> Plan:
    """Schnittplan aus der Lücke k (Bild i von B zeigt denselben Moment wie Bild i+k von A)."""
    if bilder_a <= 0 or bilder_b <= 0:
        raise StudioFehler("Eine der beiden Dateien enthält keine Bilder.")
    verfuegbar = bilder_b + k
    auffuellen = max(0, bilder_a - verfuegbar)
    if verfuegbar <= 0 or auffuellen > MAX_AUFFUELLEN:
        raise StudioFehler(f"Die Dateien passen nicht zusammen: A {bilder_a} Bilder, B {bilder_b} Bilder, Lücke {k} "
                           f"Bilder (es fehlten {auffuellen} Bilder am Ende).")
    return Plan("A" if k >= 0 else "B", k, bilder_a, auffuellen)


def bild_lage(ma: np.ndarray, mb: np.ndarray, lo: int, hi: int) -> Bewegung:
    """λ mit mb[i] ≈ ma[i+λ]. Bewegungsreihen werden von langsamer Drift befreit und normiert; Unterbild-Genauigkeit
    per Parabel; dazu das Nebenmaximum (zweitbester Wert außerhalb ±2 Bilder, relativ zum besten)."""
    n = min(len(ma), len(mb))
    if n < 50:
        return Bewegung(None, 0.0, 1.0, n)

    def norm(x: np.ndarray) -> np.ndarray | None:
        x = x - np.convolve(x, np.ones(15) / 15, mode="same")
        s = float(x.std())
        return (x - x.mean()) / s if s > 1e-6 else None

    a, b = norm(np.asarray(ma[:n], dtype=np.float64)), norm(np.asarray(mb[:n], dtype=np.float64))
    if a is None or b is None:
        return Bewegung(None, 0.0, 1.0, n)
    c = correlate(a, b, mode="full", method="fft") / n
    lo, hi = max(lo, -(n - 1)), min(hi, n - 1)
    werte = c[n - 1 + lo: n - 1 + hi + 1]
    i = int(np.argmax(werte))
    lam = float(lo + i)
    if 0 < i < len(werte) - 1:
        y0, y1, y2 = werte[i - 1], werte[i], werte[i + 1]
        nenner = y0 - 2 * y1 + y2
        if nenner != 0:
            lam += 0.5 * (y0 - y2) / nenner
    gipfel = float(werte[i])
    rest = np.delete(werte, np.arange(max(0, i - 2), min(len(werte), i + 3)))
    neben = float(rest.max() / gipfel) if rest.size and gipfel > 0 else 1.0
    return Bewegung(lam, gipfel, neben, n)


def _ton_zweifel(z: Zerlegung, konfidenz: float, drift_s: float) -> list[str]:
    zweifel = []
    if konfidenz < KONFIDENZ_WARNUNG:
        zweifel.append(f"Ton-Konfidenz {konfidenz:.2f} niedrig")
    if abs(z.rest_s) > REST_WARNUNG_S:
        zweifel.append(f"Ton-Versatz passt zu keinem Bildraster (Rest {z.rest_s * 1000:.1f} ms)")
    if abs(drift_s) > DRIFT_WARNUNG_S:
        zweifel.append(f"Ton-Versatz ändert sich im Take um {drift_s * 1000:.1f} ms (Tonsprung in einer Datei)")
    if abs(z.bloecke) >= MAX_BLOECKE:
        zweifel.append(f"Tonanfang um {z.bloecke:+d} AAC-Blöcke verschoben (ungewöhnlich)")
    return zweifel


def luecke_entscheiden(zerlegung: Zerlegung | None, konfidenz: float, drift_s: float, bew: Bewegung,
                       bilder_ab: tuple[int, int] | None = None) -> Entscheidung:
    """Eindeutige Bewegung richtet aus, der Ton ist die Gegenprobe; sonst der Ton (±1 Bild); reicht auch der nicht,
    die Bildzahl ``bilder_ab`` = (Bilder A, Bilder B), Lücke = A − B. Grün über die Bildzahl nur für kurze Takes mit
    plausibler Lücke. Rot: Bild und Ton weiter auseinander als die Phase erklärt, zweifelhafter Ton ohne Bestätigung,
    kein brauchbarer Ton, oder nur die Bildzahl bei langem Take bzw. unplausibler Lücke."""
    zweifel = _ton_zweifel(zerlegung, konfidenz, drift_s) if zerlegung is not None else []
    if bew.aussagekraeftig:
        k_bild = int(round(bew.lage))
        if zerlegung is None:
            return Entscheidung(k_bild, "bild", True,
                                ("Kein brauchbarer Ton: Lücke nur aus der Bewegung, Tonspur prüfen.",), ())
        k_ton = zerlegung.bilder
        if abs(bew.lage - k_ton) > MAX_PHASE_BILDER:
            return Entscheidung(k_bild, "bild", True,
                                (f"Bild und Ton liegen {bew.lage - k_ton:+.2f} Bilder auseinander (Ton {k_ton}, "
                                 f"Bewegung {bew.lage:.2f}): mehr als die Kamera-Phase erklärt. Beide Kameras gleich "
                                 "eingestellt?",), tuple(zweifel))
        hinweise = [f"Kamera-Phase: die Bilder liegen {k_bild - k_ton:+d} Bild neben dem OBS-Takt (Ton {k_ton}, "
                    f"Bewegung {bew.lage:.2f}); ausgerichtet nach dem Bild."] if k_bild != k_ton else []
        return Entscheidung(k_bild, "bild", False, (), (*hinweise, *zweifel))
    if zerlegung is None:
        if bilder_ab is None:
            raise StudioFehler("Weder Ton noch Bewegung reichen, um die Lücke zu bestimmen.")
        a, b = bilder_ab
        k = a - b
        if not 0 <= k <= BILDZAHL_LUECKE_MAX:
            return Entscheidung(k, "bildzahl", True,
                                (f"Weder Ton noch Bewegung reichen, und die Bildzahl ergibt eine unplausible Lücke von "
                                 f"{k} Bildern (A {a}, B {b}): Bilder verloren oder falsches Paar?",), ())
        if max(a, b) < BEWEGUNG_MIN_BILDER:
            return Entscheidung(k, "bildzahl", False, (),
                                (f"Take zu kurz für Ton und Bewegung ({max(a, b)} Bilder): ausgerichtet nach der "
                                 "Bildzahl (A minus B), Genauigkeit ±1 Bild.",))
        return Entscheidung(k, "bildzahl", True,
                            ("Weder Ton noch Bewegung reichen: Lücke nur aus der Bildzahl (±1 Bild), Take prüfen.",),
                            ())
    hinweis = (f"Bewegung nicht eindeutig (Gipfel {bew.gipfel:.2f}, Nebenmaximum {bew.neben:.2f}, {bew.bilder} "
               "Bilder): ausgerichtet nach dem Ton, Genauigkeit ±1 Bild (Kamera-Phase).")
    return Entscheidung(zerlegung.bilder, "ton", bool(zweifel), tuple(zweifel), (hinweis,))


def standbild_anteil(m: np.ndarray) -> float:
    return float(np.mean(m < STANDBILD_SCHWELLE)) if len(m) else 1.0


def ton_wahl(klicks: dict[str, int], fest: str) -> str:
    """Die Tonspur mit den wenigsten Klicks; bei Gleichstand die der Zeitachsen-Kamera."""
    andere = "B" if fest == "A" else "A"
    return andere if klicks[andere] < klicks[fest] else fest
