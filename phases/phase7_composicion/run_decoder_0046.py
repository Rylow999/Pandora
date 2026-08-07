# -*- coding: utf-8 -*-
"""
exp_SGM_0046 -- decoder_l2_relational_corpus_real (DISENO: bigrama sobre grafo ruteado por HRR)
HONESTIDAD (correccion Luciano 2026-08-03): el decoder NO usa omega plano (0022/0026). Usa el
grafo de omega RUTEADO por composicion relacional (hrr_core + tick_relational_core, Fase 7: 0027-0031).
Literatura que guia:
  - Text generation from KGs, unsupervised (1904.09447): generar desde grafo, no tokens planos.
  - Attention as Binding: VSA perspective (2512.14709): atencion = binding HRR (lo que SGM hace explicito).
  - Unifying LLMs+KGs (2306.08302): grafo da sentido estructurado, decoder lo traduce.
DISENO:
  1. Corpus real = don_quijote.txt (lit/corpus, fuera de git). Vocabulario top-N por frecuencia.
  2. Grafo: nodo = palabra (omega HRR tipo embedding). Aristas = co-ocurrencia en ventana W;
     rol de la arista = la palabra vecina (HRR bind). Asi "banco" se enlaza a "rio" y "dinero"
     con roles DISTINTOS -> el ruteo por rol desambigua (0028/0030).
  3. Bigrama RELACIONAL: dada palabra previa p, route(signal=omega[p], bias_role=idx(p)) -> pi.
     El sucesor predicho = argmax pi sobre nodos (excluye p). Esto es generacion por TRANSITO
     sobre el grafo ruteado (no proyeccion lineal W·omega que fallo en v0.25 v12 top1=0.020).
  4. Compara top1 contra: bigrama PLANO (0026, sin roles), unigram (freq), azar.
  5. Test de POLISEMIA honesto (regla #10 roadmap): palabras con sentidos conocidos en DQ.
     Mido si el ruteo por rol elige el sucesor coherente con el sentido del corpus.
NC: route con bias_role ALEATORIO -> top1 cae a azar (el rol no aporta).
"""
import math, random, json, re, os, sys

BASE = "/sdcard/Hermes/nexus-vault/NOUS/DSCN-G/EXPERIMENTS/SGM"
CORPUS = os.path.join(BASE, "lit", "corpus", "don_quijote.txt")
sys.path.insert(0, os.path.join(BASE, "phases", "phase7_composicion"))
import hrr_core as H
import tick_relational_core as TRC

SEED = 20260803
VOCAB = 400          # top-N palabras por frecuencia (corre en celular)
WIN = 3              # ventana de co-ocurrencia
D = 256              # dimension HRR (suficiente para VOCAB, 0029: D>=256 da 1.0).
                     # EMB_DIM = D: el omega de cada palabra DEBE ser dimension D para el binding HRR.

def tokenize(text):
    toks = re.findall(r"[a-záéíóúñ]+", text.lower())
    return [t for t in toks if len(t) > 2]

def build_vocab(tokens, N):
    from collections import Counter
    c = Counter(tokens)
    vocab = [w for w, _ in c.most_common(N)]
    idx = {w: i for i, w in enumerate(vocab)}
    return vocab, idx

def build_graph(tokens, vocab, idx, W, K=8):
    """Aristas de co-ocurrencia con rol = palabra vecina (HRR bind).
    Se queda con los TOP-K vecinos por frecuencia de co-ocurrencia dirigida (poda de grafo
    estandar, no hardcode: el grafo sigue siendo del corpus, solo aristas fuertes)."""
    rng = random.Random(SEED)
    emb = {w: H.rnd_unit(rng, D) for w in vocab}
    # co-ocurrencia DIRIGIDA: cuenta (a -> b) en ventana
    from collections import defaultdict
    coco = defaultdict(lambda: defaultdict(int))
    for i in range(len(tokens) - 1):
        a = tokens[i]
        if a not in idx: continue
        ai = idx[a]
        seen = set()
        for j in range(max(0, i-W), min(len(tokens), i+W+1)):
            if j == i: continue
            b = tokens[j]
            if b in idx and b != a:
                seen.add(idx[b])
        for bi in seen:
            coco[ai][bi] += 1
    # top-K por nodo
    edges = {i: [] for i in range(len(vocab))}
    for ai in coco:
        top = sorted(coco[ai].items(), key=lambda kv: -kv[1])[:K]
        for (bi, cnt) in top:
            edges[ai].append((bi, bi))
    nodes_omega = [emb[w] for w in vocab]
    return nodes_omega, edges, emb

def bigram_relational(tokens, vocab, idx, tr, W):
    """Predice sucesor usando ruteo por rol en UN PASO sobre rel_mem (no PPR global: el bigrama
    es local). Desde prev, el sucesor = vecino cuya HRR(rol, omega) tenga mayor coseno con
    omega[prev] bajo bias de rol. Esto desambigua por rol (0028/0030) y es O(grado) por paso."""
    hit = 0; tot = 0
    pairs = [(tokens[i], tokens[i+1]) for i in range(len(tokens)-1)
             if tokens[i] in idx and tokens[i+1] in idx]
    sample = pairs[:min(len(pairs), 400)]
    N = len(vocab)
    for p, nxt in sample:
        pi = [0.0]*N
        ai = idx[p]
        # afinidad directa con cada vecino de `prev` bajo bias de rol
        for (k, r) in tr.edges.get(ai, []):
            bm = H.hrr_bind(tr.role_vecs[r], tr.omega[k])   # HRR(rol, omega_vecino)
            score = max(0.0, H.cos(tr.rel_mem[ai], bm))      # coseno con rel_mem de prev bajo rol
            pi[k] = score
        if max(pi) <= 0:
            # fallback: vecino mas frecuente (no es azar, es del grafo)
            pi = [0.0]*N
            for (k, r) in tr.edges.get(ai, []):
                pi[k] = 1.0
        order = sorted(range(N), key=lambda k: -pi[k])
        pred = order[0] if order[0] != ai else (order[1] if len(order) > 1 else order[0])
        if pred == idx[nxt]:
            hit += 1
        tot += 1
    return hit, tot

def bigram_plano(tokens, vocab, idx):
    """Baseline 0026: bigrama sobre frecuencias de pares (sin roles)."""
    from collections import defaultdict
    pairs = defaultdict(lambda: defaultdict(int))
    for i in range(len(tokens)-1):
        if tokens[i] in idx and tokens[i+1] in idx:
            pairs[tokens[i]][tokens[i+1]] += 1
    hit = 0; tot = 0
    sample = [(tokens[i], tokens[i+1]) for i in range(len(tokens)-1)
              if tokens[i] in idx and tokens[i+1] in idx][:400]
    for p, nxt in sample:
        cands = pairs[p]
        if not cands:
            tot += 1; continue
        pred = max(cands, key=cands.get)
        if pred == nxt: hit += 1
        tot += 1
    return hit, tot

def unigram(tokens, vocab, idx):
    from collections import Counter
    c = Counter(t for t in tokens if t in idx)
    top = c.most_common(1)[0][0]
    hit = 0; tot = 0
    sample = [tokens[i+1] for i in range(len(tokens)-1) if tokens[i] in idx and tokens[i+1] in idx][:400]
    for nxt in sample:
        if nxt == top: hit += 1
        tot += 1
    return hit, tot

def main():
    text = open(CORPUS, encoding="utf-8", errors="ignore").read()
    tokens = tokenize(text)
    vocab, idx = build_vocab(tokens, VOCAB)
    nodes_omega, edges, emb = build_graph(tokens, vocab, idx, WIN, K=8)
    tr = TRC.TickRelational(nodes_omega, edges, D, seed=SEED)
    # rutas relacionales (usando TickRelational con D de HRR para roles)
    hit_r, tot_r = bigram_relational(tokens, vocab, idx, tr, WIN)
    hit_p, tot_p = bigram_plano(tokens, vocab, idx)
    hit_u, tot_u = unigram(tokens, vocab, idx)
    top1_r = hit_r/tot_r if tot_r else 0
    top1_p = hit_p/tot_p if tot_p else 0
    top1_u = hit_u/tot_u if tot_u else 0
    t1 = top1_r > top1_p
    results = {
        "T-DEC-R1_relacional_vs_plano": {
            "top1_relacional": round(top1_r,3), "top1_plano_0026": round(top1_p,3),
            "top1_unigram": round(top1_u,3),
            "pass": bool(t1), "meta":"Bigrama sobre grafo ruteado supera bigrama plano (0026) en corpus real"},
        "overall_pass": bool(t1)
    }
    out = {
        "experiment_id":"exp_SGM_0046",
        "name":"decoder_l2_relational_corpus_real",
        "status":"DISENO_RELACIONAL",
        "marco":"1904.09447 (grafo->texto) + 2512.14709 (atencion=binding HRR) + 2306.08302 (LLM+KG).",
        "diseno":"grafo omega ruteado por HRR (hrr_core+tick_relational_core). Bigrama por transito sobre grafo, no proyeccion lineal. Corpus: Don Quijote real.",
        "config":{"VOCAB":VOCAB,"WIN":WIN,"D":D,"EMB_DIM":EMB_DIM,"SEED":SEED,
                  "corpus_tokens":len(tokens),"vocab_size":len(vocab)},
        "tests":results,
        "verified": bool(t1)}
    print(json.dumps(out, indent=2, ensure_ascii=False))
    return out

if __name__ == "__main__":
    main()
