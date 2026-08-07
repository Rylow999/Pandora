#!/usr/bin/env python3
"""
exp_SGM_0105_reward_novedad — reward intrinseco por explorar tiles nuevos + decoder
como detector de loops.

Hipotesis A: Dar reward intrinseco por visitar tiles nuevos rompe el loop de noop,
generando variedad de acciones.

Hipotesis C: El decoder bigrama que predice la siguiente accion, al detectar que
predice siempre lo mismo (noop), genera una senal de "loop detectado" que el agente
usa para forzar exploracion.

Metodo:
  1. SGMAgent completo en Crafter.
  2. Reward intrinseco: +0.1 cada vez que el agente pisa un tile (x,y) nunca antes visitado.
  3. Decoder bigrama online: cada 10 pasos, entrena un bigrama sobre los ultimos 50 pasos.
     Si la prediccion top1 es la misma que la ultima accion real (y es la misma desde hace N pasos),
     se dispara una senal de "loop" que baja la vitalidad del nodo actual.
  4. Medir: variedad de acciones, tiles visitados, y si el decoder detecta loops correctamente.
"""
import sys, os, random, math
from collections import Counter, defaultdict
sys.path.insert(0, os.path.expanduser("~/vaults/vega-vault/NOUS/DSCN-G/EXPERIMENTS/SGM"))
from sgm_core import SGMAgent
import crafter

random.seed(42)
rng = random.Random(42)

D = 128
N_NODES = 64
V = 17
REWARD_NOVEDAD = 0.1
VENTANA_DECODER = 50
CHECK_LOOP_CADA = 10
TOPE_LOOP = 5  # si el decoder predice la misma accion 5 veces seguidas, es loop

ACCIONES = {0:"noop",1:"move_left",2:"move_right",3:"move_up",4:"move_down",
            5:"do",6:"sleep",7:"place_stone",8:"place_table",9:"place_furnace",
            10:"make_wood_pickaxe",11:"make_stone_pickaxe",12:"make_iron_pickaxe",
            13:"make_wood_sword",14:"make_stone_sword",15:"make_iron_sword",16:"eat"}

def entrenar_bigrama(seq, vocab_size=17):
    if len(seq) < 3:
        return None
    counts = {a: {b: 0.0 for b in range(vocab_size)} for a in range(vocab_size)}
    for i in range(len(seq)-1):
        a, b = seq[i], seq[i+1]
        if a in counts and b in counts[a]:
            counts[a][b] += 1.0
    model = {}
    for a in range(vocab_size):
        tot = sum(counts[a].values())
        if tot > 0:
            model[a] = {b: counts[a][b]/tot for b in range(vocab_size)}
        else:
            model[a] = {b: 1.0/vocab_size for b in range(vocab_size)}
    return model

def predecir_top1(model, accion, vocab_size=17):
    if model is None or accion not in model:
        return None, 0.0
    best, bid = -1.0, 0
    for b in range(vocab_size):
        p = model[accion].get(b, 0.0)
        if p > best:
            best, bid = p, b
    return bid, best

# Inicializar
agent = SGMAgent(rng, D, n_nodes=N_NODES, gamma=0.01)
edges = {i: random.sample(range(N_NODES), min(5, N_NODES-1)) for i in range(N_NODES)}
agent.set_edges(edges)
agent.set_modo("RAZONAMIENTO")
ter = {0,1,2,3,4,5,6,7,8,9,16}
for i in range(N_NODES):
    for k in edges.get(i, []):
        agent.set_conn_type(i, k, 4 if k in ter else 0)

env = crafter.Env()
env.reset()
obs, reward, terminal, info = env.step(0)

tiles_vistos = set()
historial_acciones = []
loop_counter = 0
log = []

for step in range(300):
    sem = info["semantic"].flatten().tolist()
    inv = info["inventory"]
    pos = tuple(info["player_pos"])
    sv = [float(v) for v in sem[::64]] + [
        float(inv["health"])/10.0, float(inv["food"])/10.0,
        float(inv["wood"]), float(inv["stone"]), float(inv["iron"]),
    ]
    
    # Decoder: detectar loops
    senal_loop = False
    if step > 0 and step % CHECK_LOOP_CADA == 0 and len(historial_acciones) >= VENTANA_DECODER:
        ventana = historial_acciones[-VENTANA_DECODER:]
        model = entrenar_bigrama(ventana, V)
        if model:
            ultima = historial_acciones[-1]
            pred, _ = predecir_top1(model, ultima)
            if pred is not None and pred == ultima:
                loop_counter += 1
                if loop_counter >= TOPE_LOOP:
                    senal_loop = True
                    # Bajar vitalidad del nodo actual para forzar exploracion
                    if agent.ultima_accion >= 0:
                        agent.vitalidad[agent.ultima_accion] *= 0.7
                    loop_counter = 0
            else:
                loop_counter = 0
    
    accion = agent.step(sv, list(range(V)), modo="RAZONAMIENTO")
    obs, reward, terminal, info = env.step(accion)
    
    # Reward intrinseco por novedad
    reward_intrinseco = 0.0
    if pos not in tiles_vistos:
        tiles_vistos.add(pos)
        reward_intrinseco = REWARD_NOVEDAD
    
    pain = 0.0
    if reward < 0: pain = abs(reward)
    elif inv["health"] < 5: pain = 0.1*(5-inv["health"])
    elif inv["food"] < 3: pain = 0.05
    
    agent.reward(reward + reward_intrinseco, pain)
    historial_acciones.append(accion)
    
    if step % 5 == 0:
        agent.actualizar_interocepcion(inv["health"]/10.0, inv["food"]/10.0)
    
    log.append({
        "step": step, "action": ACCIONES.get(accion, "?"), "pos": list(pos),
        "health": inv["health"], "food": inv["food"],
        "reward_intrinseco": reward_intrinseco,
        "senal_loop": senal_loop,
        "E_acum": round(agent.E_acumulado, 3),
        "status": agent.status, "duda": agent.doubt_count,
    })
    
    if terminal:
        break

# Reporte
print("=" * 70)
print("  exp_SGM_0105 — Reward novedad + Decoder anti-loop")
print("=" * 70)
print(f"  Pasos: {step+1} | Reward: {sum(l.get('reward_intrinseco', 0) for l in log):.2f}")
print(f"  Tiles explorados: {len(tiles_vistos)} | Health final: {inv['health']}")
print(f"  Status: {agent.status} | Duda: {agent.doubt_count}")

cnt = Counter(l['action'] for l in log)
print("\n  Acciones:")
for act, n in cnt.most_common():
    print(f"    {act:22s} {n:3d} ({100*n/len(log):.1f}%)")

loops = sum(1 for l in log if l['senal_loop'])
print(f"\n  Loops detectados por decoder: {loops}")
print(f"  Recompensas por novedad: {sum(1 for l in log if l['reward_intrinseco'] > 0)}")

# Cada 30 pasos
print("\n  Cada 30 pasos:")
for l in log[::30]:
    print(f"    p{l['step']:03d}: {l['action']:18s} pos={str(l['pos']):12s} "
          f"nov={l['reward_intrinseco']:.1f} loop={l['senal_loop']} Ea={l['E_acum']:.2f} d={l['duda']}")

# Guardar
import json, os
out = os.path.expanduser("~/vaults/vega-vault/NOUS/DSCN-G/EXPERIMENTS/SGM/results/results_exp_SGM_0105_reward_novedad.json")
os.makedirs(os.path.dirname(out), exist_ok=True)
output = {
    "experiment_id": "exp_SGM_0105",
    "experiment_name": "reward_novedad_decoder_antiloop",
    "phase": "Crafter — Reward intrinseco + decoder anti-loop",
    "date": "2026-08-06",
    "hypothesis": "Reward intrinseco por tiles nuevos + decoder que detecta loops y baja vitalidad del nodo repetido rompe el comportamiento monotono (noop) y genera exploracion.",
    "config": {"D":D, "N_NODES":N_NODES, "reward_novedad":REWARD_NOVEDAD, "ventana_decoder":VENTANA_DECODER, "tope_loop":TOPE_LOOP},
    "result": {
        "pasos": step+1, "tiles_explorados": len(tiles_vistos),
        "accion_dominante": cnt.most_common(1)[0] if cnt else ("none", 0),
        "variedad_acciones": len(cnt),
        "loops_detectados": loops,
        "recompensas_novedad": sum(1 for l in log if l['reward_intrinseco'] > 0),
        "status_final": agent.status,
    },
    "script": "experiments/exp_SGM_0105_reward_novedad.py",
    "results_file": "results/results_exp_SGM_0105_reward_novedad.json",
    "test_target": "Crafter — variedad de acciones con reward intrinseco + decoder anti-loop",
    "notes": "Reward intrinseco por tiles nuevos + decoder bigrama que detecta cuando el agente se repite y baja la vitalidad del nodo actual para forzar exploracion.",
    "notes_criollo": "Le dimos dos herramientas al agente para que no se clave: (1) descubrir un lugar nuevo da una pequena recompensa, como la curiosidad de un nino que explora porque es divertido, no porque tenga que hacerlo. (2) Un modelo interno (decoder) que se da cuenta cuando esta haciendo siempre lo mismo y le baja las pilas a esa accion para que pruebe otra. Es como aburrirte de estar sentado y levantarte a hacer otra cosa."
}
with open(out, "w") as f:
    json.dump(output, f, indent=2)
print(f"\n  Resultados guardados en: {out}")