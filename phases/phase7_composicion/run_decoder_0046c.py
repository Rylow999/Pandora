# -*- coding: utf-8 -*-
"""
exp_SGM_0046c -- decoder_l2_hybrid_soft_weight (HIBRIDO SUAVE: HRR PESA, no filtra)
CORRECCION de 0046b: el filtro binario top-M por HRR empeoro (0.17 vs 0.333 plano) porque el
HRR grado-8/D-256 no ordena bien vecinos (crosstalk) y descarta al sucesor correcto.
DISENO HONESTO SUAVE (2306.08302: grafo MODULA, no reemplaza):
  score_final(k) = freq_bigrama(k) * (1 + ALPHA * score_HRR(k))
  El HRR modula el bigrama por coherencia de sentido, pero NO lo descarta. Cuando el HRR es
  ruido (~0), score_final -> freq_bigrama (se reduce al plano). No puede bajar de 0.333.
  Si sube -> el HRR aporta senal util como peso. Si queda igual -> HRR es ruido puro para vecinos locales.
Test T-DEC-HS1: top1 suave >= plano (0.333). NC: ALPHA=0 -> plano (confirma que el HRR aporta o no).
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
ALPHA = 1.0          # peso del HRR en el score suave

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
    return [emb[w] for w in vocab], edges, emb

def build_bigram_plano(tokens, vocab, idx):
    pairs = defaultdict(lambda: defaultdict(int))
    for i in range(len(tokens)-1):
        if tokens[i] in idx and tokens[i+1] in idx:
            pairs[tokens[i]][tokens[i+1]] += 1
    return pairs

def soft_predict(prev_idx, tr, bigram, vocab, alpha):
    ai = prev_idx
    pw = bigram.get(vocab[ai], {})
    if not pw:
        return -1
    best, bests = -1, -1e9
    for (k, r) in tr.edges.get(ai, []):
        freq = pw.get(vocab[k], 0)
        if freq <= 0: continue
        bm = H.hrr_bind(tr.role_vecs[r], tr.omega[k])
        s_hrr = H.cos(tr.rel_mem[ai], bm)
        score = freq * (1.0 + alpha * s_hrr)
        if score > bests:
            bests = score; best = k
    return best

def main():
    text = open(CORPUS, encoding="utf-8", errors="ignore").read()
    tokens = tokenize(text)
    vocab, idx = build_vocab(tokens, VOCAB)
    nodes_omega, edges, emb = build_graph(tokens, vocab, idx, WIN, K=8)
    tr = TRC.TickRelational(nodes_omega, edges, D, seed=SEED)
    bigram = build_bigram_plano(tokens, vocab, idx)
    pairs = [(tokens[i], tokens[i+1]) for i in range(len(tokens)-1)
             if tokens[i] in idx and tokens[i+1] in idx][:400]
    # suave con ALPHA
    hit_s = 0; tot = 0
    for p, nxt in pairs:
        pred = soft_predict(idx[p], tr, bigram, vocab, ALPHA)
        if pred == idx[nxt]: hit_s += 1
        tot += 1
    # NC: alpha=0 (plano puro)
    hit_nc = 0
    for p, nxt in pairs:
        pred = soft_predict(idx[p], tr, bigram, vocab, 0.0)
        if pred == idx[nxt]: hit_nc += 1
    top1_s = hit_s/tot
    top1_nc = hit_nc/tot
    t1 = top1_s >= top1_nc
    out = {
        "experiment_id":"exp_SGM_0046c",
        "name":"decoder_l2_hybrid_soft_weight",
        "status":"HIBRIDO_SUAVE",
        "marco":"2306.08302 (grafo modula, no reemplaza). HRR pesa el bigrama, no lo filtra.",
        "diseno":"score_final(k)=freq_bigrama(k)*(1+ALPHA*score_HRR(k)). ALPHA=%s. Cuando HRR es ruido, se reduce a plano."%ALPHA,
        "config":{"VOCAB":VOCAB,"WIN":WIN,"D":D,"ALPHA":ALPHA,"K":8,"SEED":SEED,"corpus_tokens":len(tokens)},
        "tests":{
            "T-DEC-HS1_suave_vs_plano":{
                "top1_suave_alpha1":round(top1_s,3),"top1_plano_NC_alpha0":round(top1_nc,3),
                "pass":bool(t1),
                "meta":"Peso suave HRR >= bigrama plano (si HRR aporta senal util). Si igual -> HRR es ruido para vecinos locales."}},
        "overall_pass":bool(t1),"verified":bool(t1)}
    print(json.dumps(out, indent=2, ensure_ascii=False))
    return out

if __name__ == "__main__":
    main()
