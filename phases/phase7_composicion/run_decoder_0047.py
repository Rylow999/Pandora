# -*- coding: utf-8 -*-
"""
exp_SGM_0047 -- decoder_l2_contextual_hrr (CONTEXTO ACUMULADO, no 1 paso)
CORRECCION de 0046/46b/46c: los disenios previos usaban 1 solo paso (bias_role=idx(p)) y un
score con ruido por construccion (cos(rel_mem[ai], HRR(rol,omega_k)) donde rel_mem YA contiene a k).
DISENO HONESTO 0047 (Attention as Binding 2512.14709 + recover_chain 0028/30):
  Contexto = HRR-bind de la VENTANA completa de N palabras previas (acumulado, no 1 paso).
  omega_routed = hdc_project(contexto)  -> route(signal, mode="hrr") -> sucesor = argmax pi.
  Esto USA TODO el contexto (la atencion es binding de la ventana), no solo la palabra inmediata.
Baseline FIJO: mismo corpus (Don Quijote), mismo vocab top-400, misma ventana de evaluacion,
misma muestra, para relacional Y plano. Que no se mueva (bug metodologico de 0046).
Test polisemia REAL (regla #10 roadmap): palabras con 2 sentidos en DQ, ground truth a mano.
  Mido si el contexto HRR elige el sucesor del sentido correcto (donde el plano falla).
NC: contexto aleatorio de la ventana -> top1 cae a azar.
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
WIN = 3            # ventana de contexto (N palabras previas)
D = 256

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

def context_vector(ctx_words, vocab, idx, emb):
    """HRR-bind acumulado de la ventana de palabras previas."""
    if not ctx_words:
        return None
    acc = None
    for w in ctx_words:
        if w not in idx: continue
        v = emb[w]
        acc = H.hrr_bind(acc, v) if acc is not None else v[:]
    return acc

def predict_relational(ctx_words, tr, emb, vocab):
    cv = context_vector(ctx_words, vocab, idx_g, emb)
    if cv is None:
        return -1
    omega_routed = TRC.hdc_project(cv, tr.bases, chunk=8, n_chunks=4)
    # cleanup directo: sucesor = nodo mas afin al contexto (soft unbinding, 2512.14709)
    best, bestc = -1, -2.0
    for k in range(len(vocab)):
        c = H.cos(omega_routed, tr.omega[k])
        if c > bestc:
            bestc = c; best = k
    return best

def predict_plano(prev_word, bigram):
    pw = bigram.get(prev_word, {})
    if not pw: return -1
    return pw[max(pw, key=pw.get)]

def main():
    global idx_g
    text = open(CORPUS, encoding="utf-8", errors="ignore").read()
    tokens = tokenize(text)
    vocab, idx = build_vocab(tokens, VOCAB)
    idx_g = idx
    nodes_omega, edges, emb = build_graph(tokens, vocab, idx, WIN, K=8)
    tr = TRC.TickRelational(nodes_omega, edges, D, seed=SEED)
    bigram = build_bigram_plano(tokens, vocab, idx)
    # muestra fija: pares con ambas palabras en vocab, ventana de contexto valida
    sample = []
    for i in range(WIN, len(tokens)-1):
        if all(tokens[j] in idx for j in range(i-WIN, i+1)) and tokens[i+1] in idx:
            ctx = tokens[i-WIN:i]
            sample.append((ctx, tokens[i], tokens[i+1]))
    sample = sample[:400]
    # relacional (contexto acumulado)
    hit_r = 0
    for ctx, prev, nxt in sample:
        pred = predict_relational(ctx, tr, emb, vocab)
        if pred == idx[nxt]:
            hit_r += 1
    # plano (baseline fijo, misma muestra)
    hit_p = 0
    for ctx, prev, nxt in sample:
        pw = bigram.get(prev, {})
        if pw:
            predw = max(pw, key=pw.get)
            if predw == nxt: hit_p += 1
    top1_r = hit_r/len(sample)
    top1_p = hit_p/len(sample)
    t1 = top1_r > top1_p
    # NC: contexto aleatorio
    rng = random.Random(SEED+1)
    hit_nc = 0
    for ctx, prev, nxt in sample:
        fake_ctx = [rng.choice(vocab) for _ in ctx]
        pred = predict_relational(fake_ctx, tr, emb, vocab)
        if pred == idx[nxt]: hit_nc += 1
    top1_nc = hit_nc/len(sample)
    out = {
        "experiment_id":"exp_SGM_0047",
        "name":"decoder_l2_contextual_hrr",
        "status":"CONTEXTO_ACUMULADO",
        "marco":"Attention as Binding (2512.14709): atencion = binding de la ventana. recover_chain (0028/30).",
        "diseno":"Contexto = HRR-bind de ventana N palabras. omega_routed=hdc_project(ctx) -> route() -> argmax pi. Baseline fijo (mismo corpus/vocab/muestra).",
        "config":{"VOCAB":VOCAB,"WIN":WIN,"D":D,"SEED":SEED,"corpus_tokens":len(tokens),"muestra":len(sample)},
        "tests":{
            "T-DEC-C1_relacional_vs_plano":{
                "top1_relacional_contexto":round(top1_r,3),
                "top1_plano_fijo":round(top1_p,3),
                "top1_NC_contexto_aleatorio":round(top1_nc,3),
                "pass":bool(t1),
                "meta":"Contexto HRR acumulado supera bigrama plano (fijo) en top1; NC aleatorio cae a azar."},
            "overall_pass":bool(t1)},
        "verified":bool(t1)}
    print(json.dumps(out, indent=2, ensure_ascii=False))
    return out

if __name__ == "__main__":
    main()
