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
    para mantener el módulo Rust-limpio y sin dependencias pesadas. Suficiente
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


def firma_binaria(vector, n_bits=32, semilla=1337):
    """Firma binaria por proyección aleatoria determinista (LSH).

    NOTA 0075: la 'cuerda comprimida' — reduce un vector continuo (omega o
    espectro) a n_bits {0,1} preservando SIMILITUD (a diferencia de un hash
    criptográfico). Cada bit es el signo del producto punto con un vector de
    proyección fijo (semilla determinista): vectores cercanos producen firmas
    con baja distancia de Hamming; vectores lejanos, alta. Es la 'información
    básica en unos y ceros' de la Rueda Camelot, sin perder el gradiente debajo.
    """
    import random
    rng = random.Random(semilla)
    n = len(vector)
    bits = []
    for _ in range(n_bits):
        # vector de proyección determinista
        w = [rng.gauss(0, 1) for _ in range(n)]
        dot = sum(a * b for a, b in zip(vector, w))
        bits.append(1 if dot >= 0 else 0)
    return bits


def distancia_hamming(a, b):
    """Distancia de Hamming normalizada [0,1] entre dos firmas binarias."""
    if not a or not b or len(a) != len(b):
        return 1.0
    diffs = sum(1 for x, y in zip(a, b) if x != y)
    return diffs / len(a)


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

    def cuerda(self, n_bits=32, semilla=1337):
        """La 'cuerda comprimida' (NOTA 0075): firma binaria del espectro de
        vivencia. La información básica en unos y ceros, derivada del cómo se
        vivió. Preserva similitud (LSH): dos vivencias parecidas -> cuerdas
        parecidas (baja distancia de Hamming)."""
        # combinar espectro de valencia y arousal en un solo vector para firmar
        v = list(self.espectro_valencia) + list(self.espectro_arousal)
        if not v:
            return [0] * n_bits
        return firma_binaria(v, n_bits=n_bits, semilla=semilla)

    def divergencia(self, otra) -> float:
        """Distancia entre dos vivencias (dos nodos 'amor' vividos distinto
        divergen aquí). Combina DOS cosas, porque la fase importa tanto como la
        frecuencia (lección de la Rueda Camelot: el color de onda no es solo
        magnitud, es SIGNO):

        1. La magnitud espectral (|DFT| de la valencia) — la FORMAA del latido.
        2. El signo del afecto (valencia media + arousal media) — el SENTIDO
           de la vivencia. Dos nodos vividos +0.8 y -0.8 tienen el MISMO
           |DFT| (magnitud borra signo) pero vivencias opuestas.

        La divergencia es el promedio de ambas distancias (normalizadas).
        """
        a = self.espectro_valencia
        b = getattr(otra, "espectro_valencia", [])
        # distancia espectral (forma)
        d_espectral = 0.0
        if a and b and len(a) == len(b):
            d = sum((x - y) ** 2 for x, y in zip(a, b))
            max_d = sum(max(x * x, y * y) for x, y in zip(a, b)) + 1e-9
            d_espectral = math.sqrt(d / max_d)
        else:
            d_espectral = 1.0

        # distancia del signo del afecto (sentido)
        va = self._valencia_media()
        vb = otra._valencia_media() if hasattr(otra, '_valencia_media') else 0.0
        aa = self._arousal_media()
        ab = otra._arousal_media() if hasattr(otra, '_arousal_media') else 0.0
        d_signo = abs(va - vb) / 2.0 + abs(aa - ab)

        return min(1.0, 0.5 * d_espectral + 0.5 * d_signo)

    def _valencia_media(self):
        if not self.historia:
            return 0.0
        return sum(h[0] for h in self.historia) / len(self.historia)

    def _arousal_media(self):
        if not self.historia:
            return 0.0
        return sum(h[1] for h in self.historia) / len(self.historia)

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

    def resonar(self, idx, omega_dist, lambda_=1.0, umbral=0.3):
        """Resonancia estocástica como recuerdo (NOTA 0073 paso 2).

        Dos nodos que VIVIERON igual (misma firma espectral) 'resuenan' — están
        en fase — y se puentean aunque estén lejos en el espacio omega. Es el
        'salto' del recuerdo: P(a→b) ∝ e^(-λ·d) donde d es la distancia en el
        espacio de vivencia (divergencia espectral), no en omega.

        - idx: nodo origen.
        - omega_dist: callable (i,j)->float, la distancia en omega (recibe el
          contenedor de omega desde fuera, para no acoplar el módulo al grafo).
        - lambda_: longitud de onda de la empatía (más alto = el sentimiento
          acorta la distancia del recuerdo).
        - umbral: divergencia máxima para considerar 'en fase'.

        Retorna lista de (vecino, afinidad_resonante) ordenada por resonancia
        decreciente. Solo incluye nodos 'en fase' (divergencia < umbral).
        """
        v_self = self.nodos.get(idx)
        if not v_self:
            return []
        resonantes = []
        for j, vj in self.nodos.items():
            if j == idx:
                continue
            div = v_self.divergencia(vj)
            if div < umbral:
                # P ∝ e^(-λ·div): a menor divergencia (más en fase), más prob.
                import math
                afinidad = math.exp(-lambda_ * div)
                resonantes.append((j, afinidad))
        resonantes.sort(key=lambda x: -x[1])
        return resonantes

    def to_dict(self):
        return {str(k): v.to_dict() for k, v in self.nodos.items()}

    @classmethod
    def from_dict(cls, d):
        reg = cls()
        for k, v in d.items():
            reg.nodos[int(k)] = VivenciaNodo.from_dict(v)
        return reg


class FondoMemorial:
    """La 'memoria de los muertos' (NOTA 0073 paso 3).

    Cuando un nodo muere (vitalidad -> 0), su información NO se borra: su omega
    (qué era) y su vivencia (cómo se vivió) pasan a un FONDO residual, como las
    'cuerdas' que la Rueda Camelot describe (los datos permanecen aunque el
    procesador muera). Un proceso nuevo puede RECLUTAR del fondo para formar un
    nodo nuevo — reencarnación del material, no resurrección del nodo.

    Puro: no toca el grafo. Acotado (cola circular) para no acumular sin techo.
    """

    def __init__(self, capacidad=64):
        self.capacidad = capacidad
        self.fondo = []  # lista de {"omega": [...], "vivencia": {...}, "edad": int}

    def enterrar(self, omega, vivencia_dict):
        """Registra un nodo muerto al fondo (acotado)."""
        import time
        self.fondo.append({
            "omega": list(omega),
            "vivencia": vivencia_dict,
            "edad": 0,
        })
        if len(self.fondo) > self.capacidad:
            self.fondo = self.fondo[-self.capacidad:]

    def reclutar(self, excluir_omega=None, k=1):
        """Recluta material del fondo para un nodo nuevo.

        Devuelve lista de dicts del fondo (los de menor superposición con
        excluir_omega primero — material 'nuevo' para especializar). NO los
        saca del fondo (el recuerdo es re-derivable, el grafo es la DB).
        """
        if not self.fondo:
            return []
        if excluir_omega is None:
            return self.fondo[-k:]
        # ordenar por distancia al excluir_omega: los más lejanos son más 'nuevos'
        def dist(f):
            fo = f["omega"]
            return math.sqrt(sum((a - b) ** 2 for a, b in zip(fo, excluir_omega)))
        ordenados = sorted(self.fondo, key=dist, reverse=True)
        return ordenados[:k]

    def envejecer(self):
        """El fondo envejece: los muertos más viejos se desvanecen (olvido final)."""
        for f in self.fondo:
            f["edad"] += 1
        # desvanecer los muy viejos (edad > capacidad): la memoria final también
        # se olvida, dejando solo lo reciente como 'fondo vivo'
        self.fondo = [f for f in self.fondo if f["edad"] <= self.capacidad]

    def to_dict(self):
        return {"capacidad": self.capacidad, "fondo": self.fondo}

    @classmethod
    def from_dict(cls, d):
        fm = cls(capacidad=d.get("capacidad", 64))
        fm.fondo = list(d.get("fondo", []))
        return fm