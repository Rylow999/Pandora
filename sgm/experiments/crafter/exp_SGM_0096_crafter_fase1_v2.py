#!/usr/bin/env python3
"""
Crafter Fase 1 — Baseline descriptivo.
Log por paso: accion, posicion, cambio de pos, repeticion, inventario.
Objetivo: entender QUÉ hace el agente antes de morir.
"""
import sys, os, random, math, json
sys.path.insert(0, os.path.expanduser("~/sgm-test"))
from sgm.core.sgm_core import SGMAgent, HDC, HRR
import crafter

random.seed(42)
rng = random.Random(42)

N_ACTIONS = 17
D = 128
N_NODES = 64

# Acciones de Crafter con nombre
ACCIONES = {
    0: "noop", 1: "move_left", 2: "move_right", 3: "move_up", 4: "move_down",
    5: "do", 6: "sleep", 7: "place_stone", 8: "place_table", 9: "place_furnace",
    10: "make_wood_pickaxe", 11: "make_stone_pickaxe", 12: "make_iron_pickaxe",
    13: "make_wood_sword", 14: "make_stone_sword", 15: "make_iron_sword",
    16: "eat",
}

# Acciones de movimiento
MOVES = {1, 2, 3, 4}

def describir_patron(hist_actions, ventana=10):
    """Describe el patron de comportamiento reciente."""
    if len(hist_actions) < ventana:
        recientes = hist_actions
    else:
        recientes = hist_actions[-ventana:]
    
    if not recientes:
        return "iniciando"
    
    # Cuantas acciones unicas en ventana
    unicas = len(set(recientes))
    total = len(recientes)
    
    # Si hace siempre lo mismo
    if unicas == 1:
        if recientes[0] in MOVES:
            return "CAMINA EN LINEA RECTA"
        elif recientes[0] == 0:
            return "QUIETO (noop repetido)"
        else:
            return "REPITE ACCION: %s" % ACCIONES.get(recientes[0], str(recientes[0]))
    
    # Si alterna entre dos movimientos opuestos (zigzag / circulo)
    if set(recientes).issubset({1, 2, 3, 4}):
        pares = list(zip(recientes[:-1], recientes[1:]))
        pares_opuestos = sum(1 for a, b in pares if {a, b} in [{1, 2}, {3, 4}])
        if pares_opuestos > len(pares) * 0.6:
            return "ZIGZAG/CIRCULO (va y viene)"
    
    # Si mezcla movimiento con acciones
    mov_count = sum(1 for a in recientes if a in MOVES)
    action_count = total - mov_count
    if mov_count > action_count:
        return "EXPLORA (mov %d, act %d)" % (mov_count, action_count)
    else:
        return "INTENTA ACCIONES (mov %d, act %d)" % (mov_count, action_count)


def run_episode(env, agent, max_steps=500, ep_id=0):
    """Corre un episodio con log descriptivo paso a paso."""
    env.reset()
    total_reward = 0.0
    pain_events = 0
    steps = 0
    hist_actions = []
    hist_positions = []
    log = []
    
    # Primer step
    obs, reward, terminal, info = env.step(0)
    hist_positions.append(tuple(info["player_pos"]))
    
    for step in range(max_steps):
        semantic_flat = info["semantic"].flatten().tolist()
        inventory = info["inventory"]
        pos = tuple(info["player_pos"])
        
        sampled = semantic_flat[::64]
        state_vec = [float(v) for v in sampled] + [
            float(inventory["health"]) / 10.0,
            float(inventory["food"]) / 10.0,
            float(inventory["wood"]),
            float(inventory["stone"]),
            float(inventory["iron"]),
        ]
        
        valid_actions = list(range(N_ACTIONS))
        # SGMAgent decide
        action = agent.step(state_vec, valid_actions)

        # Ejecutar
        obs, reward, terminal, info = env.step(action)

        new_pos = tuple(info["player_pos"])
        hist_actions.append(action)
        hist_positions.append(new_pos)

        # Dolor: reward negativo o perdida de health
        pain = 0.0
        if reward < 0:
            pain = abs(reward)
            pain_events += 1
        elif info["inventory"]["health"] < 5:
            # Perder salud duele aunque reward sea 0
            pain = 0.1 * (5 - info["inventory"]["health"])
        elif info["inventory"]["food"] < 3:
            # Hambre duele un poco
            pain = 0.05
        
        agent.reward(reward, pain)
        total_reward += reward
        steps += 1
        
        # Log cada paso con descripcion
        entry = {
            "step": step,
            "action": int(action),
            "action_name": ACCIONES.get(action, "?"),
            "pos": [int(new_pos[0]), int(new_pos[1])],
            "movio": 1 if new_pos != pos else 0,
            "reward": round(reward, 2),
            "pain": round(pain, 3),
            "health": info["inventory"]["health"],
            "food": info["inventory"]["food"],
            "wood": info["inventory"]["wood"],
            "stone": info["inventory"]["stone"],
            "E": round(agent.E, 3),
            "patron": describir_patron(hist_actions, 10),
        }
        log.append(entry)
        
        if terminal:
            break
    
    return {
        "episode": ep_id,
        "steps": steps,
        "total_reward": round(total_reward, 2),
        "pain_events": pain_events,
        "final_health": info["inventory"]["health"],
        "final_food": info["inventory"]["food"],
        "final_wood": info["inventory"]["wood"],
        "achievements": {k: v for k, v in info["achievements"].items() if v},
        "log": log,
    }


def resumir_episodio(result):
    """Resumen narrativo del episodio."""
    e = result["episode"]
    log = result["log"]
    if not log:
        return "Episodio %d: vacio" % e
    
    # Acciones mas comunes
    from collections import Counter
    action_counts = Counter(l["action_name"] for l in log)
    top_actions = action_counts.most_common(5)
    
    # Secuencia de posiciones para detectar loops
    pos_set = set(tuple(l["pos"]) for l in log)
    pos_list = [tuple(l["pos"]) for l in log]
    
    # Detectar si visito la misma posicion muchas veces
    from collections import defaultdict
    pos_freq = defaultdict(int)
    for p in pos_list:
        pos_freq[p] += 1
    max_visits = max(pos_freq.values()) if pos_freq else 0
    
    # Patrones en el tiempo
    patrones_vistos = list(set(l["patron"] for l in log))
    
    lines = []
    lines.append("Episodio %d — %d pasos, reward %.1f, health final %d" % (
        e, result["steps"], result["total_reward"], result["final_health"]))
    lines.append("  Causa de muerte: health=%d, food=%d, wood=%d" % (
        result["final_health"], result["final_food"], result["final_wood"]))
    lines.append("  Acciones top: %s" % ", ".join("%s x%d" % (a, c) for a, c in top_actions))
    lines.append("  Posiciones distintas visitadas: %d de %d pasos" % (len(pos_set), len(pos_list)))
    lines.append("  Posicion mas visitada: %d veces (loopeo?)" % max_visits)
    lines.append("  Patrones detectados: %s" % ", ".join(patrones_vistos[:5]))
    
    # Si tiene logros
    if result["achievements"]:
        lines.append("  Logros: %s" % ", ".join(result["achievements"].keys()))
    
    # Log cada 10 pasos para no saturar
    lines.append("  Cada 10 pasos:")
    for l in log[::10]:
        lines.append("    p%03d: %-18s pos=%-10s hp=%d food=%d E=%.2f" % (
            l["step"], l["action_name"], str(l["pos"]),
            l["health"], l["food"], l["E"]))
    
    return "\n".join(lines)


def main():
    print("=" * 70)
    print("  Crafter Fase 1 — Baseline descriptivo")
    print("  Observando patrones de comportamiento del agente")
    print("=" * 70)
    
    N_EPISODIOS = 10
    
    agent = SGMAgent(rng, D, n_nodes=N_NODES)
    edges = {i: random.sample(range(N_NODES), min(5, N_NODES - 1))
             for i in range(N_NODES)}
    agent.set_edges(edges)
    
    # Crafter sin ventana (headless)
    env = crafter.Env()
    
    resultados = []
    for ep in range(N_EPISODIOS):
        print("\n" + "-" * 70)
        r = run_episode(env, agent, max_steps=300, ep_id=ep)
        resultados.append(r)
        print(resumir_episodio(r))
        sys.stdout.flush()
    
    # Resumen global
    print("\n" + "=" * 70)
    print("  RESUMEN GLOBAL (%d episodios)" % N_EPISODIOS)
    print("=" * 70)
    
    steps_prom = sum(r["steps"] for r in resultados) / N_EPISODIOS
    rew_prom = sum(r["total_reward"] for r in resultados) / N_EPISODIOS
    health_prom = sum(r["final_health"] for r in resultados) / N_EPISODIOS
    
    print("  Steps promedio: %.1f" % steps_prom)
    print("  Reward promedio: %.2f" % rew_prom)
    print("  Health final promedio: %.1f" % health_prom)
    print("  Logros obtenidos: %d/%d episodios" % (
        sum(1 for r in resultados if r["achievements"]), N_EPISODIOS))
    
    # Analisis de comportamiento global
    from collections import Counter
    all_actions = []
    for r in resultados:
        for l in r["log"]:
            all_actions.append(l["action_name"])
    global_counts = Counter(all_actions)
    print("\n  Acciones globales (top 10):")
    for act, cnt in global_counts.most_common(10):
        print("    %-20s %d veces (%.1f%%)" % (act, cnt, cnt / len(all_actions) * 100))
    
    # Guardar resultados
    out_path = os.path.expanduser("~/sgm-test/results_fase1.json")
    with open(out_path, "w") as f:
        json.dump({
            "experiment": "crafter_fase1_baseline",
            "n_episodios": N_EPISODIOS,
            "resumen": {
                "steps_promedio": round(steps_prom, 1),
                "reward_promedio": round(rew_prom, 2),
                "health_final_promedio": round(health_prom, 1),
                "episodios_con_logros": sum(1 for r in resultados if r["achievements"]),
            },
            "resultados": resultados,
        }, f, indent=2)
    print("\n  Resultados guardados en: %s" % out_path)


if __name__ == "__main__":
    main()