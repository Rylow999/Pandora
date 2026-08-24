# -*- coding: utf-8 -*-
"""sgm_hdc.py — HDC (Hierarchical Distributed Codings) / SensorBridge.

Proyección de señales a vectores semánticos omega.
"""
import math, random


class HDC:
    """Proyecta señales en vectores D-dimensionales usando HDC."""
    
    def __init__(self, rng, D=256, chunk=8):
        self.D = D
        self.chunk = chunk
        self.n_chunks = D // chunk
        self.bases = []
        for _ in range(self.n_chunks):
            vec = [rng.gauss(0, 1.0) for _ in range(chunk)]
            perm = list(range(chunk))
            rng.shuffle(perm)
            self.bases.append((vec, perm))
    
    def project(self, signal):
        """Proyecta señal → omega [D]."""
        vals = list(signal)[:self.n_chunks * self.chunk]
        while len(vals) < self.n_chunks * self.chunk:
            vals.append(0.0)
        om = [0.0] * self.D
        for c in range(self.n_chunks):
            vec, perm = self.bases[c]
            ch = vals[c * self.chunk:(c + 1) * self.chunk]
            b = [ch[perm[i]] * vec[i] for i in range(self.chunk)]
            for i in range(self.chunk):
                om[c * self.chunk + i] += b[i] / self.n_chunks
        n = math.sqrt(sum(x * x for x in om))
        return [x / n for x in om] if n > 0 else om


class SensorBridge:
    """Convierte percepciones del entorno en vectores semánticos."""
    
    def __init__(self, D=128):
        self.D = D
    
    def percibir(self, percepciones, posicion=None):
        """
        Convierte percepciones a vector semántico.
        percepciones: dict con {tipo: valor}
        posicion: (x, z) opcional
        """
        sv = [0.0] * self.D
        
        if posicion:
            sv[0] = posicion[0] / 50.0
            sv[1] = posicion[1] / 50.0
        
        idx = 2
        for key, val in percepciones.items():
            if idx < self.D:
                sv[idx] = float(val)
                idx += 1
        
        return sv
    
    def estado_interno(self, hambre, amenaza, salud, comida, recurso=0.0):
        """Crea vector de estado interno (18 dims)."""
        return [
            0.0, 0.0,  # posición (placeholder)
            float(hambre),
            float(amenaza),
            float(recurso),
            float(salud) / 20.0,
            float(comida) / 20.0,
            0.0, 0.0, 0.0, 0.0,
            0.0, 0.0, 0.0, 0.0,
            0.0, 0.0, 0.0
        ]