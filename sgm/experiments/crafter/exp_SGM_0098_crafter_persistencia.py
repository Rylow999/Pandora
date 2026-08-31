#!/usr/bin/env python3
"""
Crafter — persistencia entre vidas.
Un solo SGMAgent vive a traves de N episodios.
Al morir, env.reset() resetea el MUNDO, pero el agente conserva:
  - omega (pesos entrenados)
  - vitalidad (decaimiento y revitalizacion)
  - E_acumulado (dolor acumulado, se resetea suavemente entre vidas)
  - historial_acciones (traza de lo que hizo)

Si iterar produce aprendizaje, al 3er o 4to episodio el agente
deberia empezar a craftear ANTES de que la comida se acabe.
"""
import sys, os, random, json
from collections import Counter
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
from sgm.core.sgm_core import SGMAgent
import crafter

random.seed(42)
rng = random.Random(42)

D = 128
N_NODES = 64
MAX_PASOS_POR_VIDA = 300
N_VIDAS = 5  # empezamos con 5

ACCIONES = {
    0: "noop", 1: "move_left", 2: "move_right", 3: "move_up", 4: "move_down",
    5: "do", 6: "sleep", 7: "place_stone", 8: "place_table", 9: "place_furnace",
    10: "make_wood_pickaxe", 11: "make_stone_pickaxe", 12: "make_iron_pickaxe",
    13: "make_wood_sword", 14: "make_stone_sword", 15: "make_iron_sword", 16: "eat",
}

# Crear UN agente que va a vivir todas las vidas
agent = SGMAgent(rng, D, n_nodes=N_NODES, gamma=0.01)
edges = {i: random.sample(range(N_NODES), min(5, N_NODES - 1)) for i in range(N_NODES)}
agent.set_edges(edges)

vidas = []

for vida in range(N_VIDAS):
    env = crafter.Env()
    env.reset()
    obs, reward, terminal, info = env.step(0)
    
    log = []
    for step in range(MAX_PASOS_POR_VIDA):
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
            "step": step, "action": ACCIONES.get(action, "?"),
            "inventory": {"health": inv["health"], "food": inv["food"],
                          "wood": inv["wood"], "stone": inv["stone"], "iron": inv["iron"]},
            "E_acum": round(agent.E_acumulado, 3), "status": agent.status,
            "duda": agent.doubt_count, "stag": agent.stagnation_ticks,
            "vital_act": round(agent.vitalidad[action], 3),
            "reward": round(reward, 2), "pain": round(pain, 3),
        })
        
        if terminal:
            break
    
    # Resumen de la vida
    cnt = Counter(l["action"] for l in log)
    variedad = len(cnt)
    tops = cnt.most_common(5)
    
    vidas.append({
        "vida": vida,
        "pasos": step + 1,
        "reward_total": round(sum(l["reward"] for l in log), 2),
        "health_final": inv["health"],
        "food_final": inv["food"],
        "acciones_unicas": variedad,
        "acciones_top": [(a, n) for a, n in tops],
        "status_final": agent.status,
        "duda_total": agent.doubt_count,
        "E_acum_final": round(agent.E_acumulado, 3),
        "log_cada_30": [l for i, l in enumerate(log) if i % 30 == 0],
    })
    
    # Reporte de la vida
    print("=" * 65)
    print("  VIDA %d — %d pasos | reward %.2f | health %d | variedad %d" % (
        vida, step+1, vidas[-1]["reward_total"], inv["health"], variedad))
    print("  Status: %s | Duda tot: %d | E_acum: %.3f" % (
        agent.status, agent.doubt_count, agent.E_acumulado))
    print("  Top acciones: %s" % ", ".join("%s x%d" % (a, n) for a, n in tops))
    print("  Cada 30 pasos:")
    for l in vidas[-1]["log_cada_30"]:
        inv_s = l["inventory"]
        print("    p%03d: %-18s hp=%d f=%d w=%d s=%d i=%d Ea=%.2f st=%s" % (
            l["step"], l["action"], inv_s["health"], inv_s["food"],
            inv_s["wood"], inv_s["stone"], inv_s["iron"],
            l["E_acum"], l["status"][:6]))
    
    sys.stdout.flush()

# Resumen global
print("\n" + "=" * 65)
print("  RESUMEN %d VIDAS - UN AGENTE PERSISTENTE" % N_VIDAS)
print("=" * 65)

for v in vidas:
    print("  Vida %d: %3d pasos | reward %+.2f | health %d | %d acciones unicas | %s" % (
        v["vida"], v["pasos"], v["reward_total"], v["health_final"],
        v["acciones_unicas"], v["status_final"]))

# Cambios entre vidas
print("\n  Tendencia:")
for i in range(1, len(vidas)):
    prev = vidas[i-1]
    curr = vidas[i]
    diff_pasos = curr["pasos"] - prev["pasos"]
    diff_var = curr["acciones_unicas"] - prev["acciones_unicas"]
    simbolo = "+" if diff_var > 0 else ""
    print("  Vida %d→%d: pasos %+d, variedad %s%d" % (i-1, i, diff_pasos, simbolo, diff_var))

# Guardar
out = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), "results/results_multiples_vidas.json")
with open(out, "w") as f:
    json.dump({"experiment": "crafter_multiples_vidas", "n_vidas": N_VIDAS, "vidas": vidas}, f, indent=2)
print("\n  Resultados guardados en: %s" % out)
