#!/usr/bin/env python3
"""
exp_SGM_0104_decoder_auto_narrativa — ¿el decoder L2 (bigrama) puede describir
la propia trayectoria del agente en Crafter?

Hipotesis: El bigrama entrenado en la secuencia de acciones del agente (lo que hizo,
no texto en español) predice la proxima accion mejor que azar. Si el decoder
aprende la estructura del comportamiento del agente, entonces genera descripciones
de la trayectoria mas precisas que una generada al azar.

Metodo:
  1. Correr un episodio en Crafter con SGMAgent completo.
  2. Registrar la secuencia de acciones como tokens (0-16).
  3. Entrenar un bigrama sobre esa secuencia (como el 0022).
  4. Test: predecir holdout de acciones. Si top1 > azar (1/17 ≈ 0.059), el decoder
     capta estructura del comportamiento. Si NO, el comportamiento es ruido.

NC: barajar las etiquetas de accion y ver que el bigrama NO aprenda nada (top1 ~ azar).
"""
import sys, os, random, math, json
from collections import Counter
sys.path.insert(0, os.path.expanduser("~/vaults/vega-vault/NOUS/DSCN-G/EXPERIMENTS/SGM"))
from sgm_core import SGMAgent
import crafter

random.seed(42)
rng = random.Random(42)

D = 128
N_NODES = 64
N_EPISODIOS = 5
MAX_PASOS = 300
V = 17  # 17 acciones de Crafter

ACCIONES = {
    0: "noop", 1: "move_left", 2: "move_right", 3: "move_up", 4: "move_down",
    5: "do", 6: "sleep", 7: "place_stone", 8: "place_table", 9: "place_furnace",
    10: "make_wood_pickaxe", 11: "make_stone_pickaxe", 12: "make_iron_pickaxe",
    13: "make_wood_sword", 14: "make_stone_sword", 15: "make_iron_sword", 16: "eat",
}
# Bigrama: contar transiciones accion -> accion
def train_bigram(secuencia):
    counts = {a: {b: 0.0 for b in range(V)} for a in range(V)}
    for i in range(len(secuencia)-1):
        a, b = secuencia[i], secuencia[i+1]
        if a in counts and b in counts[a]:
            counts[a][b] += 1.0
    model = {}
    for a in range(V):
        tot = sum(counts[a].values())
        if tot > 0:
            model[a] = {b: counts[a][b]/tot for b in range(V)}
        else:
            model[a] = {b: 1.0/V for b in range(V)}
    return model

def top1_accuracy(model, test_seq):
    aciertos = 0
    total = 0
    for i in range(len(test_seq)-1):
        a = test_seq[i]
        b_real = test_seq[i+1]
        if a in model:
            best, bid = -1.0, 0
            for b in range(V):
                p = model[a].get(b, 0.0)
                if p > best:
                    best, bid = p, b
            if bid == b_real:
                aciertos += 1
            total += 1
    return aciertos / max(1, total)

# 1. Correr episodios y registrar secuencias
print("=" * 65)
print("  exp_SGM_0104 — Decoder auto-narrativa (bigrama sobre agente)")
print("=" * 65)

agent = SGMAgent(rng, D, n_nodes=N_NODES, gamma=0.01)
edges = {i: random.sample(range(N_NODES), min(5, N_NODES-1)) for i in range(N_NODES)}
agent.set_edges(edges)

# conn_type: Terminal para acciones directas, Functional para crafting
ter = {0,1,2,3,4,5,6,7,8,9,16}
for i in range(N_NODES):
    for k in edges.get(i, []):
        agent.set_conn_type(i, k, 4 if k in ter else 0)

toda_la_secuencia = []

for ep in range(N_EPISODIOS):
    env = crafter.Env()
    env.reset()
    obs, reward, terminal, info = env.step(0)
    ep_seq = []
    for step in range(MAX_PASOS):
        sem = info["semantic"].flatten().tolist()
        inv = info["inventory"]
        sv = [float(v) for v in sem[::64]] + [
            float(inv["health"])/10.0, float(inv["food"])/10.0,
            float(inv["wood"]), float(inv["stone"]), float(inv["iron"]),
        ]
        accion = agent.step(sv, list(range(V)), modo="RAZONAMIENTO")
        obs, reward, terminal, info = env.step(accion)
        pain = 0.0
        if reward < 0: pain = abs(reward)
        elif inv["health"] < 5: pain = 0.1*(5-inv["health"])
        elif inv["food"] < 3: pain = 0.05
        agent.reward(reward, pain)
        if step % 5 == 0:
            agent.actualizar_interocepcion(inv["health"]/10.0, inv["food"]/10.0)
        ep_seq.append(accion)
        if terminal:
            break
    toda_la_secuencia.extend(ep_seq)
    print("  Episodio %d: %d pasos, %d acciones" % (ep, step+1, len(ep_seq)))

# 2. Entrenar bigrama
SPLIT = int(len(toda_la_secuencia) * 0.8)
train_seq = toda_la_secuencia[:SPLIT]
test_seq = toda_la_secuencia[SPLIT:]
model = train_bigram(train_seq)
acc_real = top1_accuracy(model, test_seq)
azar = 1.0 / V

# 3. NC: barajar etiquetas
test_shuffled = test_seq[:]
random.shuffle(test_shuffled)
model_shuffled = train_bigram(train_seq)  # mismo modelo, test barajado
acc_nc = top1_accuracy(model, test_shuffled)

# 4. Distribucion de acciones
cnt = Counter(toda_la_secuencia)
top = cnt.most_common(5)

print("\n  Acciones totales: %d" % len(toda_la_secuencia))
print("  Acciones mas comunes: %s" % ", ".join("%s x%d" % (ACCIONES.get(a,"?"), n) for a, n in top))
print("  Top1 real: %.4f (azar: %.4f)" % (acc_real, azar))
print("  Top1 NC (shuffle): %.4f" % acc_nc)
print("  Diferencia real-NC: %.4f" % (acc_real - acc_nc))

pass_test = acc_real > azar * 1.5 and (acc_real - acc_nc) > 0.02
print("\n  PASS: %s" % pass_test)

# 5. Guardar resultados
output = {
    "experiment_id": "exp_SGM_0104",
    "experiment_name": "decoder_auto_narrativa",
    "phase": "Fase 5 — Decodificador L2 (bigrama sobre agente Crafter)",
    "date": "2026-08-06",
    "hypothesis": "El bigrama entrenado sobre la secuencia de acciones del agente en Crafter predice la siguiente accion mejor que azar (1/17). Si el decoder capta estructura del comportamiento, top1 > 0.10 y el NC barajado da ~azar.",
    "config": {"D": D, "N_NODES": N_NODES, "N_EPISODIOS": N_EPISODIOS, "V": V, "max_pasos": MAX_PASOS, "camino": "bigrama"},
    "result": {
        "acciones_totales": len(toda_la_secuencia),
        "acciones_unicas": len(cnt),
        "acciones_top": [(int(a), int(n)) for a, n in top],
        "T-DEC-01": {"top1_real": round(acc_real, 4), "umbral_azar": round(azar, 4), "supera_azar": acc_real > azar},
        "T-DEC-02": {"top1_nc_shuffle": round(acc_nc, 4), "diferencia_real_nc": round(acc_real - acc_nc, 4)},
        "pass": pass_test,
    },
    "script": "experiments/exp_SGM_0104_decoder_auto_narrativa.py",
    "results_file": "results/results_exp_SGM_0104_decoder_auto_narrativa.json",
    "test_target": "T-DEC-01: bigrama predice accion mejor que azar en holdout. T-DEC-02: NC barajado no predice.",
    "variant_of": "exp_SGM_0022",
    "lit_refs": ["SGM v1.4 §9 (Decodificador L2, 3 caminos)", "exp_SGM_0022 (bigrama sintetico top1=0.927)"],
    "notes": "Primera prueba del decoder L2 sobre comportamiento real del agente (no corpus sintetico). El bigrama aprende la secuencia de acciones del agente en Crafter. Si la secuencia tiene estructura (el agente no hace todo al azar), el bigrama la capta. Si el agente hace ruido puro, el bigrama da ~azar.",
    "notes_criollo": "El bigrama ya sabia predecir tokens de un lenguaje de juguete (0022). Ahora le damos la secuencia de lo que el agente hizo en Crafter: noop, move_left, make_sword, etc. Si el agente tiene patrones (despues de move_left suele venir move_right), el bigrama los aprende y acierta mejor que casualidad. Si el agente hace cualquier cosa al azar, el bigrama no aprende nada. Es el primer paso para que el sistema pueda 'contar su propia historia': primero tiene que tener una historia que contar."
}
out_path = os.path.expanduser("~/vaults/vega-vault/NOUS/DSCN-G/EXPERIMENTS/SGM/results/results_exp_SGM_0104_decoder_auto_narrativa.json")
os.makedirs(os.path.dirname(out_path), exist_ok=True)
with open(out_path, "w") as f:
    json.dump(output, f, indent=2, ensure_ascii=False)
print("\n  Resultados guardados en: %s" % out_path)