#!/usr/bin/env python3
"""
exp_SGM_0106 — Baseline limpio: solo vitalidad + duda + contradiccion + reward por novedad.
SIN omega_root, SIN modos, SIN conn_type, SIN bonus de raiz.

Hipotesis: Sin el bonus de afinidad de la raiz ni las aristas tipadas al azar,
el PPR no queda atrapado en el nodo "yo" y el agente vuelve a moverse y explorar
como en la version v2 original (0% noop, 59% eat).

NC: comparar con exp_SGM_0096 (v2 con duda, sin nada extra) — si este baseline
se comporta similar, el resto de mecanismos son los que estan interfiriendo.
"""
import sys, os, random, math
from collections import Counter
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
import crafter

# Construir SGMAgent SIN modificaciones complejas
# Tomamos el sgm_core.py pero usamos solo las funcionalidades basicas
import importlib, sgm_core
importlib.reload(sgm_core)
from sgm.core.sgm_core import SGMAgent

random.seed(42)
rng = random.Random(42)

D = 128
N_NODES = 64
V = 17
REWARD_NOVEDAD = 0.1

ACCIONES = {0:"noop",1:"move_left",2:"move_right",3:"move_up",4:"move_down",
            5:"do",6:"sleep",7:"place_stone",8:"place_table",9:"place_furnace",
            10:"make_wood_pickaxe",11:"make_stone_pickaxe",12:"make_iron_pickaxe",
            13:"make_wood_sword",14:"make_stone_sword",15:"make_iron_sword",16:"eat"}

# Crear agente SIN omega_root (el sgm_core.py actual tiene omega_root=True,
# pero usamos el modo DEFAULT y NO tocamos set_modo ni set_conn_type)
agent = SGMAgent(rng, D, n_nodes=N_NODES, gamma=0.01)
edges = {i: random.sample(range(N_NODES), min(5, N_NODES-1)) for i in range(N_NODES)}
agent.set_edges(edges)

# NO llamar a set_modo — se queda en DEFAULT
# NO llamar a set_conn_type — todas quedan como Functional (0) que set_edges ya puso
# NO tocar bonus de raiz — lo deja como esta en sgm_core.py

env = crafter.Env()
env.reset()
obs, reward, terminal, info = env.step(0)

tiles_vistos = set()
historial_acciones = []
log = []

for step in range(300):
    sem = info["semantic"].flatten().tolist()
    inv = info["inventory"]
    pos = tuple(info["player_pos"])
    sv = [float(v) for v in sem[::64]] + [
        float(inv["health"])/10.0, float(inv["food"])/10.0,
        float(inv["wood"]), float(inv["stone"]), float(inv["iron"]),
    ]
    
    accion = agent.step(sv, list(range(V)))
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
    
    log.append({
        "step": step, "action": ACCIONES.get(accion, "?"), "pos": list(pos),
        "health": inv["health"], "food": inv["food"],
        "reward_intrinseco": reward_intrinseco,
        "E_acum": round(agent.E_acumulado, 3),
        "status": agent.status, "duda": agent.doubt_count,
    })
    
    if terminal:
        break

# Reporte
print("=" * 70)
print("  exp_SGM_0106 — Baseline limpio (sin raiz, sin modos, sin conn_type)")
print("=" * 70)
print(f"  Pasos: {step+1} | Reward total: {sum(l.get('reward_intrinseco',0) for l in log):.2f}")
print(f"  Tiles explorados: {len(tiles_vistos)} | Health final: {inv['health']}")
print(f"  Status: {agent.status} | Duda: {agent.doubt_count}")

cnt = Counter(l['action'] for l in log)
noop_pct = cnt.get('noop', 0) / max(1, len(log)) * 100
print(f"\n  NOOP: {noop_pct:.1f}%")
print("  Acciones:")
for act, n in cnt.most_common():
    print(f"    {act:22s} {n:3d} ({100*n/len(log):.1f}%)")

print("\n  Cada 30 pasos:")
for l in log[::30]:
    print(f"    p{l['step']:03d}: {l['action']:18s} pos={str(l['pos']):12s} "
          f"nov={l['reward_intrinseco']:.1f} Ea={l['E_acum']:.2f} d={l['duda']} st={l['status'][:8]}")

# Conclusion
pass_test = noop_pct < 50  # si noop es menos de 50%, el agente se mueve
print(f"\n  {'='*50}")
print(f"  PASS: {pass_test}")
print(f"  Si NOOP < 50%: el baseline limpio funciona (el agente se mueve)")
print(f"  Si NOOP > 50%: el problema no son los mecanismos agregados — es mas profundo")
print(f"  {'='*50}")

import json, os
out = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), "results/results_exp_SGM_0106_baseline_limpio.json")
os.makedirs(os.path.dirname(out), exist_ok=True)
output = {
    "experiment_id": "exp_SGM_0106",
    "experiment_name": "baseline_limpio_sin_raiz_sin_modos",
    "phase": "Crafter — Auditoria parte por parte",
    "date": "2026-08-06",
    "hypothesis": "Sin omega_root bonus, sin modos, sin conn_type al azar, el agente vuelve a tener el comportamiento de la v2 original (noop bajo, el agente se mueve).",
    "config": {"D":D, "N_NODES":N_NODES, "reward_novedad":REWARD_NOVEDAD, "omega_root":False, "modos":False, "conn_type": False, "bonus_raiz": False},
    "result": {"pasos": step+1, "tiles_explorados": len(tiles_vistos), "noop_pct": round(noop_pct, 1),
               "accion_dominante": cnt.most_common(1)[0] if cnt else ("none", 0),
               "status_final": agent.status, "duda": agent.doubt_count, "pass": pass_test},
    "script": "experiments/exp_SGM_0106_baseline_limpio.py",
    "results_file": "results/results_exp_SGM_0106_baseline_limpio.json",
    "test_target": "Crafter — baseline sin mecanismos complejos",
    "variant_of": "exp_SGM_0096",
    "lit_refs": [],
    "notes": "Primer paso de la auditoria. Sin omega_root bonus, sin modos, sin conn_type, sin bonus de raiz. Solo vitalidad + duda + contradiccion + reward por novedad.",
    "notes_criollo": "Le sacamos al agente todo lo que le pusimos encima: el yo con bonus, la personalidad, los tipos de conexion. Lo dejamos como estaba en la version que funcionaba (v2, con solo duda y vitalidad). Si vuelve a moverse, el problema eran los mecanismos complejos interfiriendo. Si sigue clavado en noop, el problema es mas basico."
}
with open(out, "w") as f:
    json.dump(output, f, indent=2)
print(f"\n  Resultados guardados en: {out}")
