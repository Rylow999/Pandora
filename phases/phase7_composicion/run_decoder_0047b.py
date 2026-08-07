# -*- coding: utf-8 -*-
"""
exp_SGM_0047b -- decoder_l2_contextual_hrr_v2 (ESPACIO COHERENTE: omega = rel_mem)
CORRECCION de 0047: 0047 mezclo ESPACIOS (hdc_project de SensorBridge 0019 sobre un HRR-bind de
embeddings de ruido). omega_routed y tr.omega no son comparables -> cleanup da ruido (top1=0.003=NC).
Ademas los embeddings de palabra eran rnd_unit (ruido): el bind de ruido con ruido no codifica sentido.
DISENO HONESTO 0047b (espacio HRR coherente):
  omega[i] = rel_mem[i] = normalize(sum de HRR(rol_k, omega_k) de vecinos de i).
  Es decir: el SENTIDO de una palabra ES su nube relacional (no ruido aleatorio).
  Contexto = HRR-bind de rel_mem de la ventana (todo en el MISMO espacio HRR).
  Prediccion = cleanup(contexto, rel_mem) -> nodo mas afin (co-ocurrencia en espacio HRR).
  Asi "banco" y "rio" tienen rel_mem cercanos porque co-ocurren -> el bind de ambos apunta a la zona.
Baseline fijo. NC: ventana aleatoria -> azar.
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

def tokenize(text):
    return [t for t in re.findall(r"[a-záéíóúñ]+", text.lower()) if len(t) > 2]

def build_vocab(tokens, N):
    c = Counter(tokens)
    vocab = [w for w, _ in c.most_common(N)]
    return vocab, {w: i for i, w in enumerate(vocab)}

def build_graph(tokens, vocab, idx, W, K=8):
    rng = random.Random(SEED)
    emb = {w: H.rnd_unit(rng, D) for w in vocab}
    role_vecs = H.random_roles(rng, len(vocab), D)
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
    return emb, role_vecs, edges

def build_relmem(emb, role_vecs, edges, vocab):
    """omega[i] = rel_mem[i] = nube relacional de i (su sentido)."""
    rel_mem = {}
    for i in range(len(vocab)):
        acc = [0.0]*D
        for (k, r) in edges.get(i, []):
            bnd = H.hrr_bind(role_vecs[r], emb[vocab[k]])   # HRR(rol_r, filler_emb_k)
            for j in range(D): acc[j] += bnd[j]
        rel_mem[i] = H.normalize(acc) if any(acc) else emb[i]
    return rel_mem

def build_bigram_plano(tokens, vocab, idx):
    pairs = defaultdict(lambda: defaultdict(int))
    for i in range(len(tokens)-1):
        if tokens[i] in idx and tokens[i+1] in idx:
            pairs[tokens[i]][tokens[i+1]] += 1
    return pairs

def context_relmem(ctx_idx, rel_mem):
    acc = None
    for i in ctx_idx:
        v = rel_mem[i]
        acc = H.hrr_bind(acc, v) if acc is not None else v[:]
    return acc

def predict_relational(ctx_idx, rel_mem, vocab):
    cv = context_relmem(ctx_idx, rel_mem)
    if cv is None: return -1
    best, bestc = -1, -2.0
    for k in range(len(vocab)):
        c = H.cos(cv, rel_mem[k])
        if c > bestc:
            bestc = c; best = k
    return best

def main():
    text = open(CORPUS, encoding="utf-8", errors="ignore").read()
    tokens = tokenize(text)
    vocab, idx = build_vocab(tokens, VOCAB)
    emb, role_vecs, edges = build_graph(tokens, vocab, idx, WIN, K=8)
    rel_mem = build_relmem(emb, role_vecs, edges, vocab)
    bigram = build_bigram_plano(tokens, vocab, idx)
    sample = []
    for i in range(WIN, len(tokens)-1):
        if all(tokens[j] in idx for j in range(i-WIN, i+1)) and tokens[i+1] in idx:
            ctx = [idx[tokens[j]] for j in range(i-WIN, i)]
            sample.append((ctx, tokens[i], tokens[i+1]))
    sample = sample[:400]
    hit_r = 0
    for ctx, prev, nxt in sample:
        pred = predict_relational(ctx, rel_mem, vocab)
        if pred == idx[nxt]: hit_r += 1
    hit_p = 0
    for ctx, prev, nxt in sample:
        pw = bigram.get(prev, {})
        if pw and pw.get(prev, max(pw, key=pw.get)) == nxt: hit_p += 1
    top1_r = hit_r/len(sample)
    top1_p = hit_p/len(sample)
    rng = random.Random(SEED+1)
    hit_nc = 0
    for ctx, prev, nxt in sample:
        fake = [idx[rng.choice(vocab)] for _ in ctx]
        pred = predict_relational(fake, rel_mem, vocab)
        if pred == idx[nxt]: hit_nc += 1
    top1_nc = hit_nc/len(sample)
    out = {
        "experiment_id":"exp_SGM_0047b",
        "name":"decoder_l2_contextual_hrr_v2",
        "status":"ESPACIO_COHERENTE",
        "marco":"HRR coherente: omega=rel_mem (sentido=nube relacional). Cleanup en mismo espacio.",
        "diseno":"omega[i]=rel_mem[i] (nube de HRR(rol,emb) de vecinos). Contexto=bind de rel_mem ventana. Cleanup contra rel_mem. Sin hdc_project (espacios distintos).",
        "config":{"VOCAB":VOCAB,"WIN":WIN,"D":D,"SEED":SEED,"muestra":len(sample)},
        "tests":{"T-DEC-C2_relacional_v2":{
            "top1_relacional_relmem":round(top1_r,3),
            "top1_plano_fijo":round(top1_p,3),
            "top1_NC_aleatorio":round(top1_nc,3),
            "pass":bool(top1_r>top1_p),
            "meta":"Contexto HRR en espacio coherente supera plano; NC aleatorio cae."}},
        "overall_pass":bool(top1_r>top1_p),"verified":bool(top1_r>top1_p)}
    print(json.dumps(out, indent=2, ensure_ascii=False))
    return out

if __name__ == "__main__":
    main()
