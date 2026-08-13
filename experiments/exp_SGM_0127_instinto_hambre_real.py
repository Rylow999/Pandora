#!/usr/bin/env python3
"""exp_SGM_0127 — Dinamica NATIVA de Crafter completa + Hebbian fix + Kuramoto.

DECISION 2026-08-11 (Luciano): dejar de simular food decay en el SCRIPT. La dinamica
de Crafter YA tiene homeostasis nativa completa (objetos.py: _hunger baja food cada
~25 ticks, _degen_or_regen_health vincula food/drink/energy con health, reward
nativo -0.1 por health perdida). No se modifica ni se fuerza nada del entorno.

HIPOTESIS (falsable): con la dinamica nativa, el agente con instinto + consolidacion
Hebbiana (co-ocurrencia comida-mejora) + Kuramoto (relevancia sincronizada) aprendera
que comer restaura la homeostasis. Al consolidarse eat->nodo0, el instinto se apaga y
el agente come por PREDICCION. Prediccion: off_step<150, inst pequeno, pred>0,
cielos de hunger reales (food baje y suba), no obsesion (dom<50%).
SI FALSA: inst=grandes, pred=0, off_step=None (igual que 0124/0125).

Protocolo: se evalua A(inst+Hebb+Kuramoto), B(inst+Hebb sin Kuramoto), NC(PPR puro).
Periodo de vida completo: se corre hasta muerte natural o max_pasos (500).

LITERATURA: Kuramoto 1975; Ec.3/Ec.7 diseno Arquitectura_Pure_L2_Pandora; Hebb 1949
(co-ocurrencia actividad-resultado); Gallistel 1990 (habituacion por conocimiento);
Crafter Hafner 2022 (homeostasis nativa).
"""
import sys, os, random, math, json
from collections import Counter
sys.path.insert(0, os.path.expanduser("~/vaults/vega-vault/NOUS/DSCN-G/EXPERIMENTS/SGM"))
import importlib, sgm_core; importlib.reload(sgm_core)
from sgm_core import SGMAgent
import crafter
import numpy as np

D = 128; N_NODES = 64
ACC = {0:"noop",1:"move_left",2:"move_right",3:"move_up",4:"move_down",
       5:"do",6:"sleep",7:"place_stone",8:"place_table",9:"place_furnace",
       10:"make_wood_pickaxe",11:"make_stone_pickaxe",12:"make_iron_pickaxe",
       13:"make_wood_sword",14:"make_stone_sword",15:"make_iron_sword",16:"eat"}
MOV = {1,2,3,4}
FOOD = {13, 17}  # cow, plant (restauran food en Crafter nativo)
UMBRAL_EAT = 2.0  # strength eat->nodo0: conexion consolidada -> instinto OFF


def gradiente(sem, px, py, radio=5):
    mejor, bd = (0, 0), radio * radio + 1
    for dy in range(-radio, radio + 1):
        for dx in range(-radio, radio + 1):
            if dx == 0 and dy == 0:
                continue
            x, y = px + dx, py + dy
            if 0 <= x < sem.shape[1] and 0 <= y < sem.shape[0]:
                if sem[y, x] in FOOD:
                    d = abs(dx) + abs(dy)
                    if d < bd:
                        bd, mejor = d, (dx, dy)
    return mejor, bd


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


def instinto_eat(agent, usar_consolidacion, food_nivel=None):
    """Compuerta de habituacion + anclaje a HAMBRE REAL de food (0127).
    FIX: antes se gatillaba por V_grafo<0.3 (malestar AGREGADO de health/food/energia/
    fatiga por moverse), lo que hacia comer ante cualquier actividad, no ante hambre.
    Ahora la pulsion a comer se dispara por food BAJO (hambre especifica), disponible
    en la percepcion del cuerpo. Autolimitativo: al comer, food sube y la pulsion cesa.
    Instinto OFF si conexion eat->nodo0 consolidada (o strength >= umbral): habituacion.
    """
    if food_nivel is None:
        # fallback: si no hay senal de food, no activa (evita el bug de V_grafo)
        return 0.0
    hambre_real = food_nivel < agent.umbral_hambre_food
    if not hambre_real:
        return 0.0  # no hay hambre de comida -> sin pulsion a comer
    conn = agent.conn_type.get((agent.instinto_alimentacion, 0))
    strength = conn.get("strength", 0) if conn else 0
    consolidada = (agent.instinto_alimentacion, 0) in getattr(agent, 'consolidadas', set())
    if usar_consolidacion:
        if consolidada or strength >= UMBRAL_EAT:
            return 0.0
    else:
        if strength >= UMBRAL_EAT:
            return 0.0
    # fuerza modulada por QUE TAN hambriento (food bajo => mas pulsion), no por V_grafo
    carencia_food = max(0.0, agent.umbral_hambre_food - food_nivel)
    return agent.instinto_fuerza_base * (carencia_food / agent.umbral_hambre_food)


def correr(ag, usar_consolidacion, max_p=500):
    """Vida completa en Crafter nativo. SIN food_decay simulado: usa la homeostasis
    que Crafter ya provee (food baja por hunger, health por degen, reward nativo)."""
    env = crafter.Env(); env.reset()
    obs, r, t, info = env.step(0)
    tiles = set(); log = []
    eat_tot = eat_inst = eat_pred = mov = ciclos = hambre_p = 0
    instinto_off_step = None
    comida_flag = False
    food_bajo_flag = False
    # Estimar ciclo: food baja a <3 (hambre) y luego sube (comer) = ciclo completado
    for step in range(max_p):
        sem = info["semantic"]; inv = info["inventory"]
        px, py = int(info["player_pos"][0]), int(info["player_pos"][1])
        sf = sem.flatten().tolist()
        sv = [float(v) for v in sf[::64]] + [float(inv["health"])/10.0,
              float(inv["food"])/10.0, float(inv["wood"]), float(inv["stone"]),
              float(inv["iron"])]
        gd, gd2 = gradiente(sem, px, py, 5)
        hg = gd != (0, 0)
        ag._gradiente_dir = gd; ag._gradiente_dist = gd2; ag._hay_gradiente = hg
        ag._inc_dirs = {a: inc_dir(ag.modelo_mundo, a) for a in MOV}
        ag._config_grad = {"activo": True, "fuerza": 0.5}
        ag._config_curio = {"activo": True, "fuerza": 0.3}
        f_inst = instinto_eat(ag, usar_consolidacion, food_nivel=float(inv["food"]))
        ag._fuerza_instinto_eat_override = f_inst
        a = ag.step(sv, list(range(17)))
        # Ambiente nativo: siguiente observacion + reward propio de Crafter
        obs, r, t, info = env.step(a)
        # Acople directo grafo=cuerpo + Hebb/Kuramoto (en actualizar_homeostasis)
        ag.actualizar_homeostasis(inv["food"], inv["health"])
        # Reward: nativo de Crafter (r ya incluye -0.1 por health perdida, +1 por logro)
        pain = 0.0
        if r < 0:
            pain = abs(r)
        elif inv["health"] < 5:
            pain = 0.1  # pain por estado critico (sin hardcode, es senal del cuerpo)
        ag.reward(max(0.0, r), pain)
        # Novedad de lugar (reward intrinseco de explorar, no es simular homeostasis)
        pos = (px, py)
        if pos not in tiles:
            tiles.add(pos); ag.reward(0.05, 0.0)
        ag.incertidumbre_acum = max(0, ag.incertidumbre_acum - 0.01)
        eq = ag.cuantizar_estado(sv)
        ag.actualizar_modelo_mundo(getattr(ag, 'ultimo_estado_q', eq) or eq, a, eq)
        ag.ultimo_estado_q = eq
        comio = (a == 16)
        comida_flag = comio
        if comio:
            eat_tot += 1
            conn = ag.conn_type.get((16, 0))
            st = conn.get("strength", 0) if conn else 0
            cons = (16, 0) in getattr(ag, 'consolidadas', set())
            if (cons and usar_consolidacion) or st >= UMBRAL_EAT:
                eat_pred += 1
                if instinto_off_step is None:
                    instinto_off_step = step
            else:
                eat_inst += 1
        if inv["food"] < 3:
            hambre_p += 1
            food_bajo_flag = True
        elif food_bajo_flag and inv["food"] >= 7:
            # el food volvio a subir desde hambre -> ciclo completado
            ciclos += 1
            food_bajo_flag = False
        if a in MOV:
            mov += 1
        log.append({"step": step, "a": a, "food": float(inv["food"]),
                     "hp": float(inv["health"]), "Vg": round(ag.V_grafo, 3),
                     "status": ag.status, "hay_grad": hg, "r": float(r)})
        if t:
            break
    muerte = {"step": step, "food": float(inv["food"]), "hp": float(inv["health"]),
              "status": ag.status, "Vg": round(ag.V_grafo, 3)} if t else None
    return {"log": log, "tiles": tiles, "muerte": muerte, "pasos": step + 1,
            "eat": eat_tot, "eat_inst": eat_inst, "eat_pred": eat_pred,
            "mov": mov, "ciclos": ciclos, "hambre_p": hambre_p,
            "instinto_off_step": instinto_off_step,
            "consolidadas": len(getattr(ag, 'consolidadas', set()))}


def mk(seed):
    ag = SGMAgent(random.Random(seed), D, n_nodes=N_NODES, gamma=0.01)
    ag.set_edges({i: random.sample(range(N_NODES), min(5, N_NODES - 1))
                  for i in range(N_NODES)})
    return ag


print("=" * 70)
print(" exp_SGM_0127 — Instinto anclado a hambre real de food - vida nativa")
print("=" * 70)

ra = correr(mk(42), usar_consolidacion=True)
rb = correr(mk(42), usar_consolidacion=False)

cnt_a = Counter(ACC.get(l["a"], "?") for l in ra["log"])
cnt_b = Counter(ACC.get(l["a"], "?") for l in rb["log"])
dom_a = cnt_a.most_common(1)[0] if cnt_a else ("?", 0)
dom_b = cnt_b.most_common(1)[0] if cnt_b else ("?", 0)
pa = 100 * dom_a[1] / max(1, len(ra["log"]))
pb = 100 * dom_b[1] / max(1, len(rb["log"]))

print(f"\n A (nat+Hebb+Kuramoto): {ra['pasos']}p {len(ra['tiles'])}tiles "
      f"eat={ra['eat']}(inst={ra['eat_inst']},pred={ra['eat_pred']}) "
      f"mov={ra['mov']} ciclos={ra['ciclos']} consol={ra['consolidadas']} "
      f"off_step={ra['instinto_off_step']} dom={dom_a[0]} {pa:.0f}%")
print(f"   muerte={ra['muerte']}")
print(f" B (nat+Hebb, sin Kuramoto): {rb['pasos']}p {len(rb['tiles'])}tiles "
      f"eat={rb['eat']}(inst={rb['eat_inst']},pred={rb['eat_pred']}) "
      f"off_step={rb['instinto_off_step']} dom={dom_b[0]} {pb:.0f}%")

print("\n" + "=" * 70 + "\n METRICAS (A, hipotesis):")
print("=" * 70)
pass_off = (ra["instinto_off_step"] is not None) and ra["instinto_off_step"] < 150
pass_balance = ra["eat_inst"] >= 1 and ra["eat_inst"] <= 10 and ra["eat_pred"] > 0
pass_no_obs = pa < 50
pass_consolida = ra["consolidadas"] > 0
pass_ciclos = ra["ciclos"] >= 1
mejora_vs_B = ra["instinto_off_step"] is not None and rb["instinto_off_step"] is None
print(f" PASS instinto_off<150 (A): {pass_off} ({ra['instinto_off_step']})")
print(f" PASS eat balanceado (inst 1-10, pred>0): {pass_balance} "
      f"(inst={ra['eat_inst']}, pred={ra['eat_pred']})")
print(f" PASS no obsesion (dom<50): {pass_no_obs} ({dom_a[0]} {pa:.0f}%)")
print(f" PASS consolida por co-ocurrencia+Kuramoto: {pass_consolida} ({ra['consolidadas']})")
print(f" PASS ciclos hunger nativos>=1: {pass_ciclos} ({ra['ciclos']})")
print(f" PASS mejora vs B (A off, B no): {mejora_vs_B}")
print("=" * 70)

out = os.path.expanduser("~/vaults/vega-vault/NOUS/DSCN-G/EXPERIMENTS/SGM/"
                         "results/results_exp_SGM_0127_instinto_hambre_real.json")
os.makedirs(os.path.dirname(out), exist_ok=True)
json.dump({
    "experiment_id": "exp_SGM_0127",
    "experiment_name": "instinto_hambre_real",
    "phase": "Fase 8 - instinto anclado a hambre real de food - vida nativa",
    "date": "2026-08-11",
    "hypothesis": "Con la dinamica nativa de Crafter (homeostasis real de food/health), "
                  "instinto + consolidacion Hebbiana (co-ocurrencia comida-mejora) + Kuramoto "
                  "(relevancia sincronizada) => el agente aprende que comer restaura, el instinto "
                  "se apaga, come por prediccion. Pred: off_step<150, inst pequeno, pred>0, "
                  "ciclos hunger nativos>=1, dom<50%.",
    "config": {"D": D, "N_NODES": N_NODES, "umbral_eat": UMBRAL_EAT, "max_pasos": 500,
               "epsilon_grad": 5, "eta_phase": 0.05, "theta_interf": 0.70,
               "gamma_nodo": 0.01, "gamma_conocimiento": 0.001,
               "homeostasis": "NATIVA Crafter (sin simulacion)", "instinto_signo": "Hebb co-ocurrencia"},
    "result": {
        "A_nativa_hebb_kuramoto": {"pasos": ra["pasos"], "tiles": len(ra["tiles"]),
                                   "eat": ra["eat"], "eat_instinto": ra["eat_inst"],
                                   "eat_prediccion": ra["eat_pred"], "mov": ra["mov"],
                                   "ciclos": ra["ciclos"], "consolidadas": ra["consolidadas"],
                                   "instinto_off_step": ra["instinto_off_step"],
                                   "dominante": f"{dom_a[0]} {pa:.0f}%", "muerte": ra["muerte"]},
        "B_nativa_hebb_sin_kuramoto": {"pasos": rb["pasos"], "tiles": len(rb["tiles"]),
                                       "eat": rb["eat"], "eat_instinto": rb["eat_inst"],
                                       "eat_prediccion": rb["eat_pred"],
                                       "instinto_off_step": rb["instinto_off_step"],
                                       "dominante": f"{dom_b[0]} {pb:.0f}%"},
        "pass_instinto_off": pass_off, "pass_balance": pass_balance,
        "pass_no_obsesion": pass_no_obs, "pass_consolida": pass_consolida,
        "pass_ciclos": pass_ciclos, "pass_mejora_vs_B": mejora_vs_B,
    },
    "script": "experiments/exp_SGM_0127_instinto_hambre_real.py",
    "results_file": "results/results_exp_SGM_0127_instinto_hambre_real.json",
    "variant_of": "exp_SGM_0125",
    "lit_refs": ["Kuramoto 1975 - osciladores de fase acoplados",
                 "Arquitectura_Pure_L2_Pandora Eq.3/Eq.7 - dinamicas de fase e interferencia",
                 "Hebb 1949 - co-ocurrencia actividad-resultado consolida conexion",
                 "Gallistel 1990 - habituacion por conocimiento persistente",
                 "Hafner/Crafter 2022 - homeostasis nativa (food baja por hunger, health por degen)"],
    "notes": "DECISION (Luciano): se elimino el food_decay simulado del script. Crafter YA tiene "
             "homeostasis nativa (objetos.py: _hunger baja food cada ~25 ticks, _degen_or_regen_health "
             "vincula food/drink/energy con health, reward nativo). El core ya tenia la diferenciacion "
             "vitalidad-nodo vs conocimiento (gamma_nodo vs gamma_conocimiento), la compuerta de "
             "habituacion, Kuramoto (update_phase, sincronizacion, consolidar) y el fix Hebbiano "
             "(consolidar co-ocurrencia). Este experimento solo cambia el HARNESS para usar la "
             "dinamica nativa completa, sin forzar el entorno.",
    "notes_criollo": "Basta de andar simulando que la comida baja en el script — Crafter ya lo hace "
                     "solo, nativamente: pasan pasos, te da hambre, y si no comes baja la salud. "
                     "Este experimento deja que el entorno haga su trabajo y mide si el agente, "
                     "con el instinto de probar la primera vez + la regla de que 'lo que co-ocurre "
                     "con mejora se consolida' (Hebb) + la sincronizacion Kuramoto, aprende que "
                     "comer sirve y deja de necesitar el reflejo. Si se apaga el instinto y come "
                     "por conocimiento, logramos la habituacion por relevancia.",
}, open(out, "w"), indent=2)
print(f"\n Guardado en: {out}")