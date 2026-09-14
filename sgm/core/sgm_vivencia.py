# -*- coding: utf-8 -*-
"""sgm/core/sgm_vivencia.py — La vivencia espectral del nodo (NOTA 0074).

La "nube de vivencia": la firma de frecuencia de CÓMO se vivió un nodo, separada
de su omega (el núcleo rígido, qué ES). No inventa información: es la huella
afectiva de las activaciones del nodo, en forma de espectro.

Diseño acordado (opción C): la vivencia es una FIRMA DE FRECUENCIA — la magnitud
de la DFT de la historia de (valencia, arousal) del nodo. Puro y sin side-effects
sobre el grafo (mismo principio que el endocrino, Rust-limpio).

La distinción qué-es / cómo-se-vivió es la condición mínima (declarada en la nota)
para que una subjetividad pueda emerger. Honestidad: esto no la produce; la
prepara. El criterio de éxito real es que dos nodos "amor" diverjan en espectro
por haber vivido distinto.
"""

from __future__ import annotations

import math


def _dft_magnitudes(serie):
    """Magnitud de la DFT (transformada discreta de Fourier) de una serie real.

    Devuelve la lista de magnitudes |X_k| para k = 0..len-1. Sin numpy, en stdlib,
    para mantener el módulo Rust-limpio y sin dependencias pesadas. Sufficiente
    para series cortas (K ~ 16-32).
    """
    n = len(serie)
    if n == 0:
        return []
    out = []
    for k in range(n):
        real = 0.0
        imag = 0.0
        for t in range(n):
            ang = 2.0 * math.pi * k * t / n
            real += serie[t] * math.cos(ang)
            imag -= serie[t] * math.sin(ang)
        out.append(math.sqrt(real * real + imag * imag))
    return out


class VivenciaNodo:
    """La nube de vivencia de UN nodo.

    - `historia` (cola acotada): lista de (valencia, arousal) de las últimas K
      activaciones del nodo (cuando fue seed, el presente lo 'vivió').
    - `espectro`: la firma de frecuencia (|DFT| de las valencias, y de los arousal
      por separado). Acotado a K componentes.
    """

    def __init__(self, max_historia=16):
        self.max_historia = max_historia
        self.historia = []   # lista de [valencia, arousal]
        self.espectro_valencia = []
        self.espectro_arousal = []

    def registrar(self, valencia, arousal):
        """Registra una activación: el nodo se 'vivió' con ese afecto."""
        self.historia.append([float(valencia), float(arousal)])
        if len(self.historia) > self.max_historia:
            self.historia = self.historia[-self.max_historia:]
        self._recomputar_espectro()

    def _recomputar_espectro(self):
        v = [h[0] for h in self.historia]
        a = [h[1] for h in self.historia]
        self.espectro_valencia = _dft_magnitudes(v)
        self.espectro_arousal = _dft_magnitudes(a)

    def firma(self):
        """La firma espectral completa: [espectro_valencia | espectro_arousal].
        Es lo que la boca puede expresar como 'cómo me sentí'."""
        return {
            "espectro_valencia": self.espectro_valencia,
            "espectro_arousal": self.espectro_arousal,
            "veces_vivido": len(self.historia),
        }

    def divergencia(self, otra) -> float:
        """Distancia espectral entre dos vivencias (dos nodos 'amor' vividos
        distinto divergen aquí). Usa la distancia L2 sobre el espectro de
        valencias (normalizada por longitud)."""
        a = self.espectro_valencia
        b = getattr(otra, "espectro_valencia", [])
        if not a or not b or len(a) != len(b):
            return 1.0
        d = sum((x - y) ** 2 for x, y in zip(a, b))
        max_d = sum(max(x * x, y * y) for x, y in zip(a, b)) + 1e-9
        return min(1.0, math.sqrt(d / max_d))

    def to_dict(self):
        return {
            "historia": self.historia,
            "espectro_valencia": self.espectro_valencia,
            "espectro_arousal": self.espectro_arousal,
        }

    @classmethod
    def from_dict(cls, d):
        v = cls()
        v.historia = [list(h) for h in d.get("historia", [])]
        v.espectro_valencia = d.get("espectro_valencia", [])
        v.espectro_arousal = d.get("espectro_arousal", [])
        return v


class RegistroVivencia:
    """Colección de vivencias por nodo. Contenedor puro: no toca el grafo."""

    def __init__(self):
        self.nodos = {}  # idx -> VivenciaNodo

    def registrar(self, idx, valencia, arousal):
        v = self.nodos.get(idx)
        if v is None:
            v = VivenciaNodo()
            self.nodos[idx] = v
        v.registrar(valencia, arousal)

    def firma(self, idx):
        v = self.nodos.get(idx)
        return v.firma() if v else None

    def divergencia(self, a, b):
        va = self.nodos.get(a)
        vb = self.nodos.get(b)
        if not va or not vb:
            return 1.0
        return va.divergencia(vb)

    def to_dict(self):
        return {str(k): v.to_dict() for k, v in self.nodos.items()}

    @classmethod
    def from_dict(cls, d):
        reg = cls()
        for k, v in d.items():
            reg.nodos[int(k)] = VivenciaNodo.from_dict(v)
        return reg