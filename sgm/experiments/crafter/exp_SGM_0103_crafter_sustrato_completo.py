#!/usr/bin/env python3
"""
Crafter — SGMAgent completo (todos los mecanismos).
Un episodio con el sustrato integrado: omega_root, interocepcion, modos tipados,
conn_type, vitalidad, duda, contradiccion, hibernacion, reset_episodio.
Sin hardcode, sin reward shaping artificial.
"""
import sys, os, random, math
from collections import Counter
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
from sgm.core.sgm_core import SGMAgent
import crafter

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

# Mapa de conn_type: que acciones son "Terminal" (ejecutar accion directa)
# vs "Functional" (transformar recursos) vs "Causal" (causa-efecto)
# 0=Functional, 1=Causal, 2=Temporal, 3=Cognitive, 4=Terminal
# Las acciones de movimiento e interaccion directa son Terminal
# Las de crafteo son Functional
TERMINALES = {0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 16}  # noop, moverse, do, sleep, place, eat
FUNCIONALES = {10, 11, 12, 13, 14, 15}  # make_*

agent = SGMAgent(rng, D, n_nodes=N_NODES, gamma=0.01)
edges = {i: random.sample(range(N_NODES), min(5, N_NODES - 1)) for i in range(N_NODES)}
agent.set_edges(edges)

# Asignar conn_type segun el tipo de accion
for i in range(N_NODES):
    for k in edges.get(i, []):
        if k in TERMINALES:
            agent.set_conn_type(i, k, 4)  # Terminal
        elif k in FUNCIONALES:
            agent.set_conn_type(i, k, 0)  # Functional
        else:
            agent.set_conn_type(i, k, 0)

# Modo RAZONAMIENTO (explora y decide)
agent.set_modo("RAZONAMIENTO")

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
    
    # Determinar modo segun estado interno
    if step > 0 and step % 20 == 0:
        if agent.status == "CONTRADICTORIA" or agent.E_acumulado > 1.0:
            modo_actual = "SENSORIAL"
        elif agent.doubt_count >= 2:
            modo_actual = "PLAN"
        else:
            modo_actual = "RAZONAMIENTO"
    else:
        modo_actual = "RAZONAMIENTO"
    
    action = agent.step(state_vec, list(range(17)), modo=modo_actual)
    obs, reward, terminal, info = env.step(action)
    
    pain = 0.0
    if reward < 0: pain = abs(reward)
    elif inv["health"] < 5: pain = 0.1 * (5 - inv["health"])
    elif inv["food"] < 3: pain = 0.05
    
    agent.reward(reward, pain)
    
    # Interocepcion cada 5 pasos
    if step % 5 == 0:
        agent.actualizar_interocepcion(
            health=inv["health"]/10.0,
            food=inv["food"]/10.0,
            energia=inv.get("energy", 0.5)/10.0,
        )
    
    log.append({
        "step": step,
        "action": ACCIONES.get(action, "?"),
        "pos": [int(info["player_pos"][0]), int(info["player_pos"][1])],
        "health": inv["health"], "food": inv["food"],
        "wood": inv["wood"], "stone": inv["stone"],
        "E_acum": round(agent.E_acumulado, 3),
        "status": agent.status,
        "duda": agent.doubt_count,
        "modo": agent.modo_actual,
        "reward": round(reward, 2), "pain": round(pain, 3),
    })
    
    if terminal:
        break

# Reporte
print("=" * 70)
print("  CRAFTER — SUSTRATO COMPLETO (1 episodio)")
print("=" * 70)
print(f"  Pasos: {step+1} | Reward: {sum(l['reward'] for l in log):.2f} | Health final: {inv['health']}")
print(f"  Modo: {agent.modo_actual} | Status: {agent.status}")
print(f"  Duda count: {agent.doubt_count} | E_acum max: {max(l['E_acum'] for l in log):.3f}")
print(f"  ω_root[0]: {agent.omega[0][0]:.3f}")

cnt = Counter(l['action'] for l in log)
print("\n  Acciones:")
for act, n in cnt.most_common():
    print(f"    {act:22s} {n:3d} ({100*n/len(log):.1f}%)")

# Eventos clave
print("\n  Eventos de duda/contradiccion/cambio de modo:")
for l in log:
    if l['step'] == 0 or l['modo'] != log[max(0,l['step']-1)]['modo']:
        print(f"    step {l['step']:3d}: modo={l['modo']}")
    if l['duda'] > 0 and (l['step'] == 0 or log[l['step']-1]['duda'] < l['duda']):
        print(f"    step {l['step']:3d}: duda={l['duda']} act={l['action']}")
    if l['status'] == 'CONTRADICTORIA' and (l['step'] == 0 or log[l['step']-1]['status'] != 'CONTRADICTORIA'):
        print(f"    step {l['step']:3d}: *** CONTRADICTORIA *** E_acum={l['E_acum']:.2f}")

# Cada 20 pasos
print("\n  Cada 20 pasos:")
for l in log[::20]:
    print(f"    p{l['step']:03d}: {l['action']:18s} hp={l['health']} f={l['food']} "
          f"Ea={l['E_acum']:.2f} st={l['status'][:8]} d={l['duda']} md={l['modo'][:5]}")