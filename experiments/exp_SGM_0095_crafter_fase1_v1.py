#!/usr/bin/env python3
"""
Crafter Fase 0 — Plomeria: loop tick->percepcion->accion con SGMAgent.
Un solo agente, estado semantico (info['semantic']), sustrato consolidado.
Objetivo: que el episodio no se rompa.
"""
import sys, os, random, math, json
sys.path.insert(0, os.path.expanduser("~/sgm-test"))
from sgm_core import SGMAgent, HDC, HRR

import crafter

random.seed(42)
rng = random.Random(42)

N_ACTIONS = 17
D = 128
N_NODES = 64

def run_episode(env, agent, max_steps=500, record_every=50):
    """Corre un episodio, devuelve stats."""
    obs = env.reset()
    total_reward = 0.0
    steps = 0
    pain_events = 0
    log = []
    # Primer step para obtener info
    obs, reward, terminal, info = env.step(0)

    for step in range(max_steps):
        # Obtener estado semantico
        semantic_flat = info["semantic"].flatten().tolist()  # 64x64 = 4096 ints
        inventory = info["inventory"]
        achievements = info["achievements"]
        pos = info["player_pos"]

        # Construir estado: tiles aplanados normalizados + inventario resumido
        # Muestreamos cada 64 para reducir dimension (64 valores)
        sampled = semantic_flat[::64]  # 64 valores
        state_vec = [float(v) for v in sampled] + [
            float(inventory["health"]) / 10.0,
            float(inventory["food"]) / 10.0,
            float(inventory["wood"]),
            float(inventory["stone"]),
            float(inventory["iron"]),
        ]

        # Acciones validas (todas las 17)
        valid_actions = list(range(N_ACTIONS))

        # SGMAgent decide
        action = agent.step(state_vec, valid_actions)

        # Ejecutar
        obs, reward, terminal, info = env.step(action)

        # Dolor: reward negativo o perdida de health
        pain = 0.0
        if reward < 0:
            pain = abs(reward)
            pain_events += 1
        if info["inventory"]["health"] < 5:
            pain += 0.2

        # SGMAgent aprende
        agent.reward(reward, pain)

        total_reward += reward
        steps += 1

        if step % record_every == 0:
            log.append({
                "step": step,
                "action": action,
                "reward": reward,
                "pain": round(pain, 3),
                "health": inventory["health"],
                "E": round(agent.E, 3),
            })

        if terminal:
            break

    return {
        "steps": steps,
        "total_reward": round(total_reward, 2),
        "pain_events": pain_events,
        "final_health": inventory["health"],
        "achievements": achievements,
        "log": log,
    }


def main():
    print("=" * 60)
    print("  Crafter Fase 0 — Plomeria")
    print("  SGMAgent + Crafter: loop tick->percepcion->accion")
    print("=" * 60)

    # Inicializar
    print("\n[*] Inicializando SGMAgent (D=%d, N=%d)..." % (D, N_NODES))
    agent = SGMAgent(rng, D, n_nodes=N_NODES)

    # Conectar aristas iniciales aleatorias
    edges = {i: random.sample(range(N_NODES), min(5, N_NODES - 1))
             for i in range(N_NODES)}
    agent.set_edges(edges)

    print("[*] Creando entorno Crafter...")
    env = crafter.Env()

    # Episodio de prueba
    print("\n[*] Corriendo episodio (max 200 pasos)...")
    result = run_episode(env, agent, max_steps=200)

    print("\n  Steps: %d" % result["steps"])
    print("  Reward total: %.2f" % result["total_reward"])
    print("  Eventos de dolor: %d" % result["pain_events"])
    print("  Health final: %d" % result["final_health"])
    print("  Logros: %d/22 desbloqueados" % sum(1 for v in result["achievements"].values() if v))
    if result["achievements"]:
        for k, v in sorted(result["achievements"].items()):
            if v:
                print("    ✅ %s" % k)

    print("\n  --- Log parcial ---")
    for entry in result["log"]:
        print("  step=%d act=%d rew=%.1f pain=%.3f hp=%d E=%.3f" % (
            entry["step"], entry["action"], entry["reward"],
            entry["pain"], entry["health"], entry["E"]))

    print("\n" + "=" * 60)
    if result["steps"] > 0 and not result.get("crashed", False):
        print("  ✅ FASE 0 COMPLETADA — loop vivo, no se rompio")
    else:
        print("  ❌ FASE 0 FALLADA — el loop se rompio")
    print("=" * 60)

    return 0 if result["steps"] > 0 else 1


if __name__ == "__main__":
    sys.exit(main())