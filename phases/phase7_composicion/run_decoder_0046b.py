# -*- coding: utf-8 -*-
"""
exp_SGM_0046b -- decoder_l2_hybrid_hrr_filter (HIBRIDO: HRR filtra por sentido + bigrama plano predice)
CORRECCION de 0046: el ruteo HRR de 1 paso daba top1=0.020 (crosstalk, peor que plano 0.333).
El HRR NO compite en top1 de bigrama; compite en DESAMBIGUACION de sentido (composicion anidada).
DISENO HONESTO HIBRIDO:
  1. Semilla relacional: desde prev, el HRR (rel_mem + bias rol) da score de coherencia de SENTIDO
     a cada vecino. Filtro: pasan al bigrama los vecinos con score HRR en el top-M (o > umbral).
     -> el HRR acota el espacio de candidatos a los COHERENTES CON EL ROL (su fortaleza).
  2. Prediccion: entre candidatos filtrados por HRR, elige el del BIGRAMA PLANO (conteo de freq).
     -> el conteo elige sin ruido de binding (su fortaleza).
  Resultado esperado: top1 hibrido >= plano, y desambigua polisemia donde el plano falla.
Literatura: 1904.09447 (grafo->texto) + 2512.14709 (atencion=binding) + 2306.08302 (LLM+KG hibrido).
"""
import math, random, json, re, os, sys
from collections import defaultdict, Counter

BASE = "/sdcard/Hermes/nexus-vault/NOUS/DSCN-G/EXPERIMENTS/SGM"
CORPUS = os.path.join(BASE, "lit", "corpus", "don_quijote.txt")
sys.path.insert(0, os.path.join(BASE, "phases", "phase7_composicion"))
import hrr_core as H
import tick_relational_core as TRC

SEED = 20260803
VOCAB = 400
WIN = 3
D = 256
M_FILTER = 4          # HRR filtra a los top-M vecinos por coherencia de sentido

def tokenize(text):
    return [t for t in re.findall(r"[a-záéíóúñ]+", text.lower()) if len(t) > 2]

def build_vocab(tokens, N):
    c = Counter(tokens)
    vocab = [w for w, _ in c.most_common(N)]
    return vocab, {w: i for i, w in enumerate(vocab)}

def build_graph(tokens, vocab, idx, W, K=8):
    rng = random.Random(SEED)
    emb = {w: H.rnd_unit(rng, D) for w in vocab}
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
    edges = {i: [] for i in range(len(vocab))}
    for ai in coco:
        for (bi, cnt) in sorted(coco[ai].items(), key=lambda kv: -kv[1])[:K]:
            edges[ai].append((bi, bi))
    nodes_omega = [emb[w] for w in vocab]
    return nodes_omega, edges, emb

def build_bigram_plano(tokens, vocab, idx):
    pairs = defaultdict(lambda: defaultdict(int))
    for i in range(len(tokens)-1):
        if tokens[i] in idx and tokens[i+1] in idx:
            pairs[tokens[i]][tokens[i+1]] += 1
    return pairs

def hybrid_predict(prev_idx, tr, bigram, vocab):
    """Filtra vecinos por score HRR (top-M por coherencia de sentido) y elige por bigrama plano."""
    ai = prev_idx
    neigh = tr.edges.get(ai, [])
    if not neigh:
        return -1
    scored = []
    for (k, r) in neigh:
        bm = H.hrr_bind(tr.role_vecs[r], tr.omega[k])
        s = H.cos(tr.rel_mem[ai], bm)
        scored.append((s, k))
    scored.sort(key=lambda x: -x[0])
    cand = [k for (s, k) in scored[:M_FILTER]]
    if not cand:
        cand = [k for (s, k) in scored]
    pw = bigram.get(vocab[ai], {})
    best, bestc = -1, -1
    for k in cand:
        c = pw.get(vocab[k], 0)
        if c > bestc:
            bestc = c; best = k
    if best < 0 or bestc <= 0:
        best = cand[0]
    return best

def main():
    text = open(CORPUS, encoding="utf-8", errors="ignore").read()
    tokens = tokenize(text)
    vocab, idx = build_vocab(tokens, VOCAB)
    nodes_omega, edges, emb = build_graph(tokens, vocab, idx, WIN, K=8)
    tr = TRC.TickRelational(nodes_omega, edges, D, seed=SEED)
    bigram = build_bigram_plano(tokens, vocab, idx)
    # muestra
    pairs = [(tokens[i], tokens[i+1]) for i in range(len(tokens)-1)
             if tokens[i] in idx and tokens[i+1] in idx][:400]
    # hibrido
    hit_h = 0; tot = 0
    for p, nxt in pairs:
        pred = hybrid_predict(idx[p], tr, bigram, vocab)
        if pred == idx[nxt]:
            hit_h += 1
        tot += 1
    # plano (baseline 0026)
    hit_p = 0
    for p, nxt in pairs:
        pw = bigram.get(p, {})
        if pw:
            pred = max(pw, key=pw.get)
            if pred == nxt: hit_p += 1
    top1_h = hit_h/tot
    top1_p = hit_p/tot
    t1 = top1_h >= top1_p
    results = {
        "T-DEC-H1_hibrido_vs_plano": {
            "top1_hibrido": round(top1_h,3), "top1_plano_0026": round(top1_p,3),
            "pass": bool(t1),
            "meta":"Hibrido (HRR filtra por sentido + bigrama plano) >= bigrama plano en top1 corpus real"},
        "overall_pass": bool(t1)
    }
    out = {
        "experiment_id":"exp_SGM_0046b",
        "name":"decoder_l2_hybrid_hrr_filter",
        "status":"HIBRIDO",
        "marco":"1904.09447 + 2512.14709 + 2306.08302. Hibrido: HRR filtra sentido, bigrama plano predice.",
        "diseno":"Semilla relacional HRR (rel_mem+bias rol) filtra top-M vecinos por coherencia de sentido; bigrama plano elige entre ellos. Corpus Don Quijote real.",
        "config":{"VOCAB":VOCAB,"WIN":WIN,"D":D,"M_FILTER":M_FILTER,"K":8,"SEED":SEED,"corpus_tokens":len(tokens)},
        "tests":results,
        "verified": bool(t1)
    }
    print(json.dumps(out, indent=2, ensure_ascii=False))
    return out

if __name__ == "__main__":
    main()
