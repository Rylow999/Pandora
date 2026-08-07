# -*- coding: utf-8 -*-
"""
exp_SGM_0048 -- decoder_l2_hrr_trained_embeddings (ENTRENAR embeddings HRR desde co-ocurrencia)
RAIZ del fallo en 0047b: emb = rnd_unit (ruido) no codifica co-ocurrencia -> cleanup da ruido.
DISENO HONESTO 0048 (message-passing en espacio HRR, tipo skip-gram sobre HRR):
  Train: emb[w] = normalize(sum_k peso(w,k) * HRR(rol_k, emb_old[k]))  por T iteraciones.
    -> los emb propagan la estructura del grafo: "banco" y "rio" terminan cercanos si co-ocurren.
  Test estructural (regla honestidad): cos(emb[w], emb[n]) para pares CO-OCURRENTES vs RANDOM.
    Si diferencia > 0 -> el HRR YA captura co-ocurrencia (no es ruido).
  Decoder: sucesor = argmax_k mean_i cos(emb[ctx_i], emb[k]) entre vecinos de la ultima palabra.
    NC: contexto aleatorio de la ventana -> top1 cae a azar.
"""
import math, random, json, re, os, sys
from collections import defaultdict, Counter

BASE = "/sdcard/Hermes/nexus-vault/NOUS/DSCN-G/EXPERIMENTS/SGM"
CORPUS = os.path.join(BASE, "lit", "corpus", "don_quijote.txt")
sys.path.insert(0, os.path.join(BASE, "phases", "phase7_composicion"))
import hrr_core as H

SEED = 20260803
VOCAB = 400
WIN = 3
D = 128
T_ITER = 2          # iteraciones de message-passing (reducido para velocidad en celular)

def tokenize(text):
    return [t for t in re.findall(r"[a-záéíóúñ]+", text.lower()) if len(t) > 2]

def build_vocab(tokens, N):
    c = Counter(tokens)
    return [w for w, _ in c.most_common(N)], {w: i for i, w in enumerate([w for w, _ in c.most_common(N)])}

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
    wsum = {}
    for ai in coco:
        tot = float(sum(coco[ai].values()))
        for (bi, cnt) in sorted(coco[ai].items(), key=lambda kv: -kv[1])[:K]:
            edges[ai].append((bi, bi, cnt/tot))
        wsum[ai] = tot
    return emb, role_vecs, edges

def train_embeddings(emb, role_vecs, edges, vocab, T):
    """Message-passing en espacio HRR: cada nodo absorbe a sus vecinos ponderados."""
    cur = {w: emb[w][:] for w in vocab}
    for it in range(T):
        nxt = {}
        for i, w in enumerate(vocab):
            acc = [0.0]*D
            for (k, r, p) in edges.get(i, []):
                bnd = H.hrr_bind(role_vecs[r], cur[vocab[k]])
                for j in range(D): acc[j] += p * bnd[j]
            # mantener traza propia para no perder identidad
            for j in range(D): acc[j] += 0.3 * cur[w][j]
            nxt[w] = H.normalize(acc) if any(acc) else cur[w]
        cur = nxt
    return cur
def build_bigram_plano(tokens, vocab, idx):
    pairs = defaultdict(lambda: defaultdict(int))
    for i in range(len(tokens)-1):
        if tokens[i] in idx and tokens[i+1] in idx:
            pairs[tokens[i]][tokens[i+1]] += 1
    return pairs

def predict(emb, edges, vocab, ctx_words, idx):
    """Sucesor = argmax entre vecinos de la ultima palabra del contexto, por afinidad media al contexto."""
    last = ctx_words[-1]
    if last not in idx: return -1
    cand = [k for (k, r, p) in edges.get(idx[last], [])]
    if not cand: return -1
    best, bestc = -1, -2.0
    for k in cand:
        s = 0.0
        for cw in ctx_words:
            if cw in idx:
                s += H.cos(emb[cw], emb[vocab[k]])
        s /= len(ctx_words)
        if s > bestc:
            bestc = s; best = k
    return best

def structural_test(emb, vocab, edges, idx, rng):
    co = []
    for i in edges:
        for (k, r, p) in edges[i][:2]:
            co.append(H.cos(emb[vocab[i]], emb[vocab[k]]))
    rd = []
    for _ in range(max(1,len(co))):
        a = rng.choice(vocab); b = rng.choice(vocab)
        rd.append(H.cos(emb[a], emb[b]))
    return (sum(co)/len(co)) if co else 0.0, (sum(rd)/len(rd)) if rd else 0.0

def main():
    rng = random.Random(SEED)
    text = open(CORPUS, encoding="utf-8", errors="ignore").read()
    tokens = tokenize(text)
    vocab, idx = build_vocab(tokens, VOCAB)
    emb0, role_vecs, edges = build_graph(tokens, vocab, idx, WIN, K=8)
    emb = train_embeddings(emb0, role_vecs, edges, vocab, T_ITER)
    bigram = build_bigram_plano(tokens, vocab, idx)
    sample = []
    for i in range(WIN, len(tokens)-1):
        if all(tokens[j] in idx for j in range(i-WIN, i+1)) and tokens[i+1] in idx:
            ctx = tokens[i-WIN:i]
            sample.append((ctx, tokens[i], tokens[i+1]))
    sample = sample[:200]
    hit_r = 0
    for ctx, prev, nxt in sample:
        pred = predict(emb, edges, vocab, ctx, idx)
        if pred == idx[nxt]: hit_r += 1
    hit_p = 0
    for ctx, prev, nxt in sample:
        pw = bigram.get(prev, {})
        if pw and max(pw, key=pw.get) == nxt: hit_p += 1
    hit_nc = 0
    for ctx, prev, nxt in sample:
        fake = [rng.choice(vocab) for _ in ctx]
        pred = predict(emb, edges, vocab, fake, idx)
        if pred == idx[nxt]: hit_nc += 1
    co_sim, rd_sim = structural_test(emb, vocab, edges, idx, rng)
    top1_r = hit_r/len(sample); top1_p = hit_p/len(sample); top1_nc = hit_nc/len(sample)
    out = {
        "experiment_id":"exp_SGM_0048",
        "name":"decoder_l2_hrr_trained_embeddings",
        "status":"EMBEDDINGS_ENTRENADOS",
        "marco":"Message-passing HRR (skip-gram sobre HRR). Embeddings propagan co-ocurrencia al omega.",
        "diseno":"Train T_ITER message-passing: emb[w]=normalize(sum vecinos p*HRR(rol,emb)). Test estructural: cos co-ocurrente vs random. Decoder: argmax vecinos por afinidad media al contexto.",
        "config":{"VOCAB":VOCAB,"WIN":WIN,"D":D,"T_ITER":T_ITER,"K":8,"SEED":SEED,"muestra":len(sample)},
        "tests":{
            "T-DEC-S1_estructural":{
                "cos_coocurrente":round(co_sim,3),"cos_random":round(rd_sim,3),
                "captura_coocurrencia":bool(co_sim>rd_sim),
                "meta":"Embeddings HRR entrenados deben dar cos mayor para co-ocurrentes que random."},
            "T-DEC-S2_decoder":{
                "top1_relacional_entrenado":round(top1_r,3),
                "top1_plano_fijo":round(top1_p,3),
                "top1_NC_aleatorio":round(top1_nc,3),
                "pass":bool(top1_r>top1_p),
                "meta":"Embeddings entrenados superan bigrama plano; NC aleatorio cae a azar."}},
        "overall_pass":bool(top1_r>top1_p and co_sim>rd_sim),
        "verified":bool(top1_r>top1_p and co_sim>rd_sim)}
    print(json.dumps(out, indent=2, ensure_ascii=False))
    return out

if __name__ == "__main__":
    main()
