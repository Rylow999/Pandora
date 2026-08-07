# -*- coding: utf-8 -*-
"""
hrr_core.py -- modulo compartido de composicion relacional HRR (Fase 7, validado en 0027/27b/27c/28/29)
Bind = circular convolution (Plate 1995a), signo (i-k) corregido en 0027.
Unbind = circular correlation.
Clean-up memory OBLIGATORIA (VSA survey p.8-10): el unbinding da crosstalk, se busca el mas similar.
Memoria relacional: cada arista (i->k) se guarda como HRR(rol_k, omega_k) en superposicion por nodo.
  rol_k = role_vecs[k]  (rol POR INDICE DE NODO, no por posicion ni por permutacion del mismo rol).
  Esto es lo que aisla niveles de anidamiento (ver 0027c/28/29). Rol fijo o cyclic shift del mismo
  rol NO aislan bajo HRR (hallazgo documentado).

API:
  hrr_bind(a,b), hrr_unbind(a,b)
  rnd_unit(rng,D), cos(a,b), normalize(v)
  build_relational_memory(edges, omega, role_vecs, D) -> rel_mem[i] = superposicion de aristas de i
  recover_target(rel_mem, src, tgt, role_vecs, omega, D) -> indice recuperado de tgt desde src
  recover_chain(rel_mem, src, path, role_vecs, omega, D) -> desanida cadena [src->a->b->...] por roles
Uso en tests: los roles son SIEMPRE role_vecs[indice_nodo]. No usar posiciones. Eso evita el bug de 0029.
"""
import math, random

def hrr_bind(a, b):
    D = len(a)
    c = [0.0]*D
    for k in range(D):
        s = 0.0
        for i in range(D):
            s += a[i]*b[(k-i)%D]
        c[k] = s
    return c

def hrr_unbind(a, b):
    D = len(a)
    c = [0.0]*D
    for k in range(D):
        s = 0.0
        for i in range(D):
            s += a[i]*b[(i-k)%D]
        c[k] = s
    return c

def rnd_unit(rng, D):
    v = [rng.gauss(0,1) for _ in range(D)]
    n = math.sqrt(sum(x*x for x in v)); return [x/n for x in v] if n>0 else v

def cos(a, b):
    s = sum(x*y for x,y in zip(a,b))
    na = math.sqrt(sum(x*x for x in a)); nb = math.sqrt(sum(x*x for x in b))
    return s/(na*nb) if na*nb>0 else 0.0

def normalize(v):
    n = math.sqrt(sum(x*x for x in v)); return [x/n for x in v] if n>0 else v

def cleanup(vec, mem):
    best, bi = -2.0, -1
    for i, m in enumerate(mem):
        c = cos(vec, m)
        if c > best: best, bi = c, i
    return bi

def build_relational_memory(edges, omega, role_vecs, D):
    """rel_mem[i] = normalize( sum_{(k,r) en edges[i]} HRR(role_vecs[k], omega[k]) )."""
    rel_mem = {}
    for i in edges:
        acc = [0.0]*D
        for (k, r) in edges[i]:
            b = hrr_bind(role_vecs[k], omega[k])   # rol = indice del nodo destino k
            acc = [acc[j] + b[j] for j in range(D)]
        rel_mem[i] = normalize(acc)
    return rel_mem

def recover_target(rel_mem, src, tgt, role_vecs, omega, D):
    """Desde src, recuperar el nodo tgt con el que tiene arista (rol = role_vecs[tgt])."""
    rec = hrr_unbind(rel_mem[src], role_vecs[tgt])
    return cleanup(rec, omega)

def recover_chain(rel_mem, src, path, role_vecs, omega, D):
    """Desanidar cadena src->p[0]->p[1]->... usando roles = indices de cada nodo.
    Devuelve True si todos los pasos aciertan el cleanup."""
    cur = src
    for nxt in path:
        bi = recover_target(rel_mem, cur, nxt, role_vecs, omega, D)
        if bi != nxt: return False
        cur = nxt
    return True

def random_roles(rng, n, D):
    """Genera n role_vecs independientes (rol por indice de nodo)."""
    return [rnd_unit(rng, D) for _ in range(n)]
