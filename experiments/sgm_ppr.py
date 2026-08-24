# -*- coding: utf-8 -*-
"""sgm_ppr.py — PPR (Personalized PageRank).

Propagación de información sobre el grafo.
"""


def ppr_route(adj, seed, aff_fn, alpha=0.15, iters=100):
    """
    PageRank personalizado sobre el grafo.
    
    Args:
        adj: dict {nodo: [vecinos]}
        seed: nodo semilla
        aff_fn: función (a, b) -> afinidad
        alpha: probabilidad de volver al seed
        iters: número de iteraciones
    
    Returns:
        dict {nodo: rank}
    """
    nodes = list(adj.keys())
    if seed not in nodes:
        return {}
    
    rank = {n: 0.0 for n in nodes}
    rank[seed] = 1.0
    
    for _ in range(iters):
        nxt = {n: 0.0 for n in nodes}
        for n in nodes:
            if rank[n] == 0:
                continue
            nxt[seed] += alpha * rank[n]
            neigh = adj[n]
            if not neigh:
                continue
            w = [max(0.0, aff_fn(n, k)) for k in neigh]
            s = sum(w)
            if s <= 0:
                continue
            for idx, k in enumerate(neigh):
                nxt[k] += (1 - alpha) * (w[idx] / s) * rank[n]
        rank = nxt
    
    return rank


def ppr_inverso(adj, seed, alpha=0.15, iters=50):
    """PPR inverso: desde el resultado, encontrar causas."""
    # Construir grafo inverso
    inv_adj = {}
    for i in adj:
        for j in adj[i]:
            if j not in inv_adj:
                inv_adj[j] = []
            inv_adj[j].append(i)
    
    return ppr_route(inv_adj, seed, lambda a, b: 1.0, alpha, iters)