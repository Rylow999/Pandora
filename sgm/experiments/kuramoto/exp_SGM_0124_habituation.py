#!/usr/bin/env python3
"""exp_SGM_0124 — Habituacion: instinto -> aprendizaje -> olvido del instinto.

HIPOTESIS: El instinto de alimentacion solo actua mientras NO SABE el resultado.
Cuando eat->nodo0.strength >= umbral, instinto OFF permanente. Come por prediccion.
Mismo para curiosidad. Prediccion: multiples ciclos hambre-comer-saciarse, no obsesion eat.
Lit: Berridge 1998 (wanting como motivacion operante no permanente),
Oudeyer 2007 (IAC), Panksepp 1998 (SEEKING reduce al descubrir), Gallistel 1990 (habituacion).
Protocolo A(inst+curio+despl con compuerta) / B(solo desplaz) / NC(PPR puro).
"""
import sys, os, random, math, json
from collections import Counter
sys.path.insert(0, os.path.expanduser("~/vaults/vega-vault/NOUS/DSCN-G/EXPERIMENTS/SGM"))
import importlib, sgm_core; importlib.reload(sgm_core)
from sgm.core.sgm_core import SGMAgent
import crafter
import numpy as np

D = 128; N_NODES = 64
ACC = {0:"noop",1:"move_left",2:"move_right",3:"move_up",4:"move_down",
       5:"do",6:"sleep",7:"place_stone",8:"place_table",9:"place_furnace",
       10:"make_wood_pickaxe",11:"make_stone_pickaxe",12:"make_iron_pickaxe",
       13:"make_wood_sword",14:"make_stone_sword",15:"make_iron_sword",16:"eat"}
MOV = {1,2,3,4}
FOOD = {13, 17}
UMBRAL_EAT = 2.0  # strength de eat->nodo0 para que el instinto se apague


def gradiente(sem, px, py, radio=5):
    mejor, mejor_d = (0, 0), radio * radio + 1
    for dy in range(-radio, radio + 1):
        for dx in range(-radio, radio + 1):
            if dx == 0 and dy == 0:
                continue
            x, y = px + dx, py + dy
            if 0 <= x < sem.shape[1] and 0 <= y < sem.shape[0]:
                if sem[y, x] in FOOD:
                    d = abs(dx) + abs(dy)
                    if d < mejor_d:
                        mejor_d, mejor = d, (dx, dy)
    return mejor, mejor_d


def inc_dir(modelo, accion):
    if not modelo:
        return 1.0
    tot, nw = 0, 0
    for (e, a), tr in modelo.items():
        if a == accion:
            tot += sum(tr.values())
            for sq, c in tr.items():
                if c <= 1:
                    nw += 1
    return nw / max(1, tot)


def instinto_eat(agent):
    """Compuerta de aprendizaje: si eat->nodo0 consolidado, instinto OFF."""
    if agent.V_grafo >= agent.instinto_umbral_carencia:
        return 0.0
    conn = agent.conn_type.get((agent.instinto_alimentacion, 0))
    strength = conn.get("strength", 0) if conn else 0
    if strength >= UMBRAL_EAT:
        return 0.0  # ya sabe, come por prediccion
    return agent.instinto_fuerza_base * (agent.instinto_umbral_carencia - agent.V_grafo)


def food_decay(inv, moved):
    inv["food"] = max(0.0, inv["food"] - 0.02 - (0.03 if moved else 0.0))


def correr(ag, ia=True, ic=True, ides=True, max_p=300):
    env = crafter.Env(); env.reset()
    obs, r, t, info = env.step(0)
    tiles = set(); log = []
    eat_tot = eat_inst = eat_pred = mov = ciclos = hambre_p = 0
    instinto_off_step = None
    comida_flag = False
    for step in range(max_p):
        sem = info["semantic"]; inv = info["inventory"]
        px, py = int(info["player_pos"][0]), int(info["player_pos"][1])
        sf = sem.flatten().tolist()
        sv = [float(v) for v in sf[::64]] + [float(inv["health"]) / 10.0,
              float(inv["food"]) / 10.0, float(inv["wood"]), float(inv["stone"]),
              float(inv["iron"])]
        gd, gdist = gradiente(sem, px, py, 5)
        hay_g = gd != (0, 0)
        inc = {a: inc_dir(ag.modelo_mundo, a) for a in MOV}
        ag._gradiente_dir = gd; ag._gradiente_dist = gdist
        ag._hay_gradiente = hay_g; ag._inc_dirs = inc
        ag._config_grad = {"activo": ides, "fuerza": 0.5}
        ag._config_curio = {"activo": ic and hay_g, "fuerza": 0.3}
        f_inst = instinto_eat(ag) if ia else 0.0
        ag._fuerza_instinto_eat_override = f_inst if ia else 0.0
        a = ag.step(sv, list(range(17)))
        obs, r, t, info = env.step(a)
        ag.actualizar_homeostasis(inv["food"], inv["health"])
        moved = a in MOV
        food_decay(inv, moved)
        pos = (px, py)
        if pos not in tiles:
            tiles.add(pos); ag.reward(0.05, 0.0)
        pain = 0.0
        if inv["food"] < 3: pain += 0.1
        if inv["health"] < 5: pain += 0.1
        ag.reward(0.0, pain)
        ag.incertidumbre_acum = max(0, ag.incertidumbre_acum - 0.01)
        # Actualizar modelo del mundo
        eq = ag.cuantizar_estado(sv)
        ag.actualizar_modelo_mundo(getattr(ag, 'ultimo_estado_q', eq) or eq, a, eq)
        ag.ultimo_estado_q = eq
        comio = (a == 16)
        if comio:
            eat_tot += 1
            conn = ag.conn_type.get((16, 0))
            st = conn.get("strength", 0) if conn else 0
            if st >= UMBRAL_EAT:
                eat_pred += 1
                if instinto_off_step is None:
                    instinto_off_step = step
            else:
                eat_inst += 1
            if inv["food"] < 3 and not comida_flag:
                ciclos += 1
            comida_flag = True
        else:
            comida_flag = False
        if inv["food"] < 3:
            hambre_p += 1
        if a in MOV:
            mov += 1
        log.append({"step": step, "a": a, "food": float(inv["food"]),
                     "hp": float(inv["health"]), "Vg": round(ag.V_grafo, 3),
                     "status": ag.status, "hay_grad": hay_g})
        if t:
            break
    muerte = {"step": step, "food": float(inv["food"]), "hp": float(inv["health"]),
              "status": ag.status, "Vg": round(ag.V_grafo, 3)} if t else None
    return {"log": log, "tiles": tiles, "muerte": muerte, "pasos": step + 1,
            "eat": eat_tot, "eat_inst": eat_inst, "eat_pred": eat_pred,
            "mov": mov, "ciclos": ciclos, "hambre_p": hambre_p,
            "instinto_off_step": instinto_off_step}


def mk(seed):
    ag = SGMAgent(random.Random(seed), D, n_nodes=N_NODES, gamma=0.01)
    ag.set_edges({i: random.sample(range(N_NODES), min(5, N_NODES - 1))
                  for i in range(N_NODES)})
    return ag


print("=" * 70)
print(" exp_SGM_0124 — Habituacion: instinto -> aprendizaje -> prediccion")
print("=" * 70)

ra = correr(mk(42), ia=True, ic=True, ides=True)
rb = correr(mk(42), ia=False, ic=False, ides=True)
rc = correr(mk(42), ia=False, ic=False, ides=False)

cnt_a = Counter(ACC.get(l["a"], "?") for l in ra["log"])
cnt_b = Counter(ACC.get(l["a"], "?") for l in rb["log"])
cnt_c = Counter(ACC.get(l["a"], "?") for l in rc["log"])

dom_a = cnt_a.most_common(1)[0] if cnt_a else ("?", 0)
dom_b = cnt_b.most_common(1)[0] if cnt_b else ("?", 0)
dom_c = cnt_c.most_common(1)[0] if cnt_c else ("?", 0)
pct = lambda c, x: 100 * c[1] / max(1, len(x["log"]))
pa, pb, pc = pct(dom_a, ra), pct(dom_b, rb), pct(dom_c, rc)

print(f"\n A (compuerta): {ra['pasos']}p {len(ra['tiles'])}tiles "
      f"eat={ra['eat']}(inst={ra['eat_inst']},pred={ra['eat_pred']}) "
      f"mov={ra['mov']} ciclos={ra['ciclos']} dom={dom_a[0]} {pa:.0f}%")
print(f"   instinto_off_step={ra['instinto_off_step']} muerte={ra['muerte']}")
print(f" B (solo despl): {rb['pasos']}p {len(rb['tiles'])}tiles eat={rb['eat']} "
      f"mov={rb['mov']} dom={dom_b[0]} {pb:.0f}%")
print(f" NC (PPR puro):  {rc['pasos']}p {len(rc['tiles'])}tiles eat={rc['eat']} "
      f"mov={rc['mov']} dom={dom_c[0]} {pc:.0f}%")

print("\n" + "=" * 70 + "\n METRICAS")
print("=" * 70)
pass_ciclos = ra["ciclos"] >= 1
pass_no_obsesion = pa < 50
pass_compuerta = ra["eat_inst"] <= 3 and ra["eat_pred"] > 0
pass_supervivencia = ra["pasos"] > rb["pasos"]
pass_explora = len(ra["tiles"]) > len(rb["tiles"])
print(f" PASS ciclos>=1:   {pass_ciclos} ({ra['ciclos']})")
print(f" PASS no obs<50%:  {pass_no_obsesion} ({dom_a[0]} {pa:.0f}%)")
print(f" PASS compuerta:   {pass_compuerta} (inst={ra['eat_inst']},pred={ra['eat_pred']})")
print(f" PASS sup A>B:     {pass_supervivencia} ({ra['pasos']} vs {rb['pasos']})")
print(f" PASS explora A>B: {pass_explora} ({len(ra['tiles'])} vs {len(rb['tiles'])})")
print("=" * 70)

out = os.path.expanduser("~/vaults/vega-vault/NOUS/DSCN-G/EXPERIMENTS/SGM/"
                         "results/results_exp_SGM_0124_habituation.json")
os.makedirs(os.path.dirname(out), exist_ok=True)
json.dump({
    "experiment_id": "exp_SGM_0124",
    "experiment_name": "habituation_instinto_aprendizaje",
    "phase": "Fase 8 — habituacion (instinto -> aprendizaje -> prediccion)",
    "date": "2026-08-11",
    "hypothesis": "El instinto de alimentacion solo actua mientras el agente NO SABE el resultado. "
                  "Cuando eat->nodo0.strength >= umbral, instinto OFF permanente; come por prediccion. "
                  "Prediccion: multiples ciclos hambre-comer-saciarse, no obsesion eat, comida balanceada.",
    "config": {"D": D, "N_NODES": N_NODES, "umbral_eat": UMBRAL_EAT, "pasos": 300},
    "result": {
        "A_compuerta": {"pasos": ra["pasos"], "tiles": len(ra["tiles"]),
                        "eat": ra["eat"], "eat_instinto": ra["eat_inst"],
                        "eat_prediccion": ra["eat_pred"], "mov": ra["mov"],
                        "ciclos": ra["ciclos"], "instinto_off_step": ra["instinto_off_step"],
                        "dominante": f"{dom_a[0]} {pa:.0f}%", "muerte": ra["muerte"]},
        "B_solo_desplaz": {"pasos": rb["pasos"], "tiles": len(rb["tiles"]),
                           "eat": rb["eat"], "mov": rb["mov"], "dominante": f"{dom_b[0]} {pb:.0f}%"},
        "NC_ppr_puro": {"pasos": rc["pasos"], "tiles": len(rc["tiles"]),
                        "eat": rc["eat"], "mov": rc["mov"], "dominante": f"{dom_c[0]} {pc:.0f}%"},
        "pass_ciclos": pass_ciclos, "pass_no_obsesion": pass_no_obsesion,
        "pass_compuerta": pass_compuerta, "pass_supervivencia": pass_supervivencia,
        "pass_explora": pass_explora,
    },
    "script": "experiments/exp_SGM_0124_habituation.py",
    "results_file": "results/results_exp_SGM_0124_habituation.json",
    "variant_of": "exp_SGM_0123",
    "lit_refs": ["Berridge & Robinson 1998 - wanting operante, no permanencia",
                 "Oudeyer & Kaplan 2007 - IAC, curiosidad como muestreo inteligente",
                 "Panksepp 1998 - SEEKING reduce al descubrir",
                 "Gallistel 1990 - habituacion por conocimiento"],
    "notes": "El 0123 fallo: el gradiente solo se activaba dentro de necesidad_insatisfecha "
             "y el agente nunca comio -> place_stone 100%. Rediseno: instinto de alimentacion "
             "con compuerta de aprendizaje. La fuerza del instinto solo se aplica mientras "
             "eat->nodo0.strength < umbral (no sabe el resultado). Al consolidarse, come por "
             "prediccion (rank*vitalidad). Gradiente radio 5 + food decay activo para ciclos reales.",
    "notes_criollo": ("La idea es que el agente nazca con la reaccion de probar comida la primera vez, "
                      "cuando no sabe si sirve. Una vez que come y se da cuenta de que alimento le sube "
                      "la vitalidad, ya no necesita ese reflejo: lo aprendio. A partir de ahi come por "
                      "conocimiento, no por instinto. Es como un bebe que mama por reflejo la primera vez "
                      "y despues come porque sabe que lo alimenta. Si esto funciona, el agente deberia "
                      "comer 1-3 veces por instinto y el resto por aprendizaje, sin obsesionarse."),
}, open(out, "w"), indent=2)
print(f"\n Guardado en: {out}")