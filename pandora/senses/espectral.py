# -*- coding: utf-8 -*-
"""pandora/senses/espectral.py — Análisis de ritmo en numpy puro (sin scipy).

Convierte flujos temporales (historial de CPU, etc.) en patrones de frecuencia,
sin dependencia de scipy. Un Welch simplificado: ventana + FFT + promedio.

El "ritmo del entorno" es el análogo de escuchar, sin pretender que sea el
corazón de Pandora (entorno, no cuerpo; 0066).
"""
import math

import numpy as np


def densidad_espectral_potencia(serie, window=64, fs=1.0):
    """Welch simplificado: devuelve (frecuencias, potencia) de la serie.

    serie: array 1D de muestras temporales.
    window: tamaño de la ventana.
    fs: frecuencia de muestreo (1.0 = una muestra por tick).
    """
    serie = np.asarray(serie, dtype=float)
    if len(serie) < window:
        return np.array([]), np.array([])

    # Centro de la señal (quitar la media para ver el ritmo, no el nivel)
    x = serie[-window:] - serie[-window:].mean()

    # Ventana de Hann suave
    w = 0.5 * (1.0 - np.cos(2.0 * np.pi * np.arange(window) / (window - 1)))
    x = x * w

    # FFT de una ventana (Welch simplificado: una sola ventana)
    espectro = np.fft.rfft(x)
    potencia = (np.abs(espectro) ** 2) / window
    frecuencias = np.fft.rfftfreq(window, d=1.0 / fs)

    return frecuencias, potencia


def frecuencia_dominante(serie, window=64, fs=1.0):
    """Devuelve la frecuencia con más potencia (el 'ritmo' dominante)."""
    freqs, potencia = densidad_espectral_potencia(serie, window, fs)
    if len(freqs) == 0 or len(potencia) == 0:
        return None
    # Ignorar la componente DC (freq == 0)
    idx = np.argmax(potencia[1:] if len(potencia) > 1 else potencia)
    idx = idx + 1 if len(potencia) > 1 else idx
    return float(freqs[idx])


def ritmo_a_vector(frecuencia, amplitud, hrr, D=128):
    """Convierte (frecuencia, amplitud) en un patrón HRR crudo.

    La frecuencia es la 'altura' del ritmo; la amplitud su 'volumen'. Se
    representa como un vector determinista en el espacio del SGM, no como texto.
    """
    if frecuencia is None:
        return [0.0] * D
    import random
    rng = random.Random(int(frecuencia * 1000) % (2**31))
    base = [rng.gauss(0, 1) for _ in range(D)]
    norm = math.sqrt(sum(x * x for x in base))
    base = [x / norm for x in base]
    amp = max(0.0, min(1.0, amplitud))
    return [x * amp for x in base]