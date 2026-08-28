#!/usr/bin/env python3
"""Episodio unico con check_stagnation + doubt integrado. Documentar comportamiento."""
import sys, os
sys.path.insert(0, os.path.expanduser("~/sgm-test"))
from sgm.core.sgm_core import SGMAgent
import crafter, random
from collections import Counter

random.seed(42)
rng = random.Random(42)

D = 128
N_NODES = 64
ACCIONES = {
    0: "noop", 1: "move_left", 2: "move_right", 3: "move_up", 4: "move_down",
    5: "do", 6: "sleep", 7: "place_stone", 8: "place_table", 9: "place_furnace",
    10: "make_wood_pickaxe", 11: "make_stone_pickaxe", 12: "make_iron_pickaxe",
    13: "make_wood_sword", 14: "make_stone_sword", 15: "make_iron_sword", 16: "eat",
}

agent = SGMAgent(rng, D, n_nodes=N_NODES, gamma=0.01)
edges = {i: random.sample(range(N_NODES), min(5, N_NODES - 1)) for i in range(N_NODES)}
agent.set_edges(edges)

env = crafter.Env()
env.reset()
obs, reward, terminal, info = env.step(0)

log = []
for step in range(300):
    semantic = info["semantic"].flatten().tolist()
    inv = info["inventory"]
    sampled = semantic[::64]
    state_vec = [float(v) for v in sampled] + [
        float(inv["health"])/10.0, float(inv["food"])/10.0,
        float(inv["wood"]), float(inv["stone"]), float(inv["iron"]),
    ]
    
    action = agent.step(state_vec, list(range(17)))
    obs, reward, terminal, info = env.step(action)
    
    pain = 0.0
    if reward < 0: pain = abs(reward)
    elif inv["health"] < 5: pain = 0.1 * (5 - inv["health"])
    elif inv["food"] < 3: pain = 0.05
    
    agent.reward(reward, pain)
    
    log.append({
        "step": step, "action": ACCIONES.get(action, "?"), "pos": list(info["player_pos"]),
        "health": inv["health"], "food": inv["food"],
        "E_acum": round(agent.E_acumulado, 3), "status": agent.status,
        "duda": agent.doubt_count, "stag": agent.stagnation_ticks,
        "vital": round(agent.vitalidad[action], 3), "reward": round(reward, 2), "pain": round(pain, 3),
    })
    
    if terminal: break

# Reporte
print("=" * 70)
print("  EPISODIO CON DUDA + CONTRADICCION INTEGRADOS")
print("=" * 70)
print(f"  Pasos: {step+1} | Reward: {sum(l['reward'] for l in log):.2f} | Health final: {inv['health']}")
print(f"  E_acum max: {max(l['E_acum'] for l in log):.3f} | Status final: {agent.status}")
print(f"  Duda count: {agent.doubt_count} | Estancamientos: {sum(1 for l in log if l['stag'] >= 5)}")

# Acciones
cnt = Counter(l['action'] for l in log)
print("\n  Acciones:")
for act, n in cnt.most_common():
    print(f"    {act:20s} {n:3d} veces ({100*n/len(log):.1f}%)")

# Eventos clave
print("\n  Eventos de duda/contradiccion:")
for l in log:
    if l['duda'] > 0 and (l['step'] == 0 or log[log.index(l)-1]['duda'] < l['duda']):
        print(f"    step {l['step']:3d}: duda={l['duda']} status={l['status']} E_acum={l['E_acum']:.3f} accion={l['action']}")
    if l['status'] == 'CONTRADICTORIA' and (l['step'] == 0 or log[log.index(l)-1]['status'] != 'CONTRADICTORIA'):
        print(f"    step {l['step']:3d}: *** CONTRADICTORIA *** E_acum={l['E_acum']:.3f}")

# Cada 20 pasos
print("\n  Cada 20 pasos:")
for l in log[::20]:
    print(f"    p{l['step']:03d}: {l['action']:18s} hp={l['health']} food={l['food']} "
          f"Ea={l['E_acum']:.2f} st={l['status']:14s} d={l['duda']} v={l['vital']:.2f}")