# -*- coding: utf-8 -*-
"""sgm_hrr.py — HRR (Holographic Reduced Representation).

Bind/unbind de vectores, memoria relacional, cleanup.
"""
import math


class HRR:
    """Holographic Reduced Representation con roles."""
    
    def __init__(self, D, rng, n_roles):
        self.D = D
        self.roles = [[rng.gauss(0, 1) for _ in range(D)] for _ in range(n_roles)]
        for r in self.roles:
            self._norm(r)
    
    def _norm(self, v):
        n = math.sqrt(sum(x * x for x in v))
        if n > 0:
            for i in range(len(v)):
                v[i] /= n
    
    def role(self, i):
        return self.roles[i]
    
    def bind(self, a, b):
        """Binding por convolución circular."""
        D = self.D
        c = [0.0] * D
        for k in range(D):
            s = 0.0
            for i in range(D):
                s += a[i] * b[(k - i) % D]
            c[k] = s
        return c
    
    def unbind(self, a, b):
        """Unbinding (correlación)."""
        D = self.D
        c = [0.0] * D
        for k in range(D):
            s = 0.0
            for i in range(D):
                s += a[i] * b[(i - k) % D]
            c[k] = s
        return c
    
    def cos(self, a, b):
        """Coseno entre vectores."""
        s = sum(x * y for x, y in zip(a, b))
        na = math.sqrt(sum(x * x for x in a))
        nb = math.sqrt(sum(x * x for x in b))
        return s / (na * nb) if na * nb > 0 else 0.0
    
    def cleanup(self, vec, mem):
        """Devuelve índice del vector más cercano en mem."""
        best, bi = -2.0, -1
        for i, m in enumerate(mem):
            c = self.cos(vec, m)
            if c > best:
                best, bi = c, i
        return bi
    
    def relational_memory(self, edges, omega):
        """Construye memoria relacional por nodo."""
        rel = {}
        for i in edges:
            acc = [0.0] * self.D
            for k in edges[i]:
                b = self.bind(self.role(k), omega[k])
                for j in range(self.D):
                    acc[j] += b[j]
            rel[i] = self._normlist(acc)
        return rel
    
    def _normlist(self, v):
        n = math.sqrt(sum(x * x for x in v))
        return [x / n for x in v] if n > 0 else v
    
    def recover(self, rel_mem, src, tgt, omega):
        """Recupera nodo desde memoria relacional."""
        rec = self.unbind(rel_mem[src], self.role(tgt))
        return self.cleanup(rec, omega)