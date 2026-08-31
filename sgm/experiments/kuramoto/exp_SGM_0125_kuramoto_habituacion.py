#!/usr/bin/env python3
"""exp_SGM_0125 — Kuramoto como senal de relevancia sincronizada -> consolidacion -> habituacion.

CONTEXTO: en 0124 el instinto nunca aprendio (inst=141, pred=0, instinto_off_step=None):
la poda a tasa de vitalidad (1%/step, ~93% en 265 pasos) aniquilaba la acumulacion del
strength eat->nodo0. El conocimiento nunca persistia, el instinto nunca se hacia redundante.

HIPOTESIS (falsable, pre-registrada): Kuramoto (Eq.3 del diseno arquitectonico) da una
senal de RELEVANCIA SINCRONIZADA: cuando una accion ayuda a la homeostasis (food sube =>
sign(o)=+1), la fase del nodo sincroniza hacia la raiz. Si cos(phi_i - phi_root) > umbral
(Eq.7 interferencia), la conexion accion->nodo0 se CONSOLIDA (no-podable, persiste).

Con eso: el instinto de alimentacion se apaga permanentemente en el PRIMER ciclo de
refuerzo porque el conocimiento ya persiste -> el agente come despues por PREDICCION
(eat->nodo0 consolidado), no por reflejo.

SI hipotesis CIERTA:  inst=1..3, pred>0, instinto_off_step<60, accion dominante<50%.
SI hipotesis FALSA:    inst~141, pred=0, instinto_off_step=None (igual que 0124).

Protocolo:
  A:  instinto + Kuramoto (opcion B signo: +1 si food sube) -> CONSOLIDA.
  B:  instinto SIN Kuramoto (strength a gamma_conocimiento pero sin consolidar). Baseline 0124.
  NC: PPR puro, sin instintos.

Metricas clave: instinto_off_step, eat_instinto vs eat_prediccion, ciclos, dominante,
numero de conexiones consolidadas por sincronizacion Kuramoto.

LITERATURA: Kuramoto 1975 (osciladores de fase acoplados), Eq.3/Eq.7 del diseno
Arquitectura_Pure_L2_Pandora; Gallistel 1990 (habituacion por conocimiento);
Berridge & Robinson 1998 (wanting operante no permanente). Revive la base Kuramoto
del diseno que se habia pausado en la auditoria 0106 (sustrato minimo).
"""
import sys, os, random, math, json
from collections import Counter
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
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
UMBRAL_EAT = 2.0  # strength para que instinto se apague


def gradiente(sem, px, py, radio=5):
    mejor, mejor_d = (0, 0), radio*radio+1
    for dy in range(-radio, radio+1):
        for dx in range(-radio, radio+1):
            if dx == 0 and dy == 0:
                continue
            x, y = px+dx, py+dy
            if 0 <= x < sem.shape[1] and 0 <= y < sem.shape[0]:
                if sem[y, x] in FOOD:
                    d = abs(dx)+abs(dy)
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


def instinto_eat(agent, usar_consolidacion):
    """Compuerta de habituacion. Si usar_consolidacion: el instinto se apaga cuando la
    conexion eat->nodo0 esta CONSOLIDADA (por sincronizacion Kuramoto) O su strength
    cruza el umbral. Si no: solo strength (baseline 0124)."""
    if agent.V_grafo >= agent.instinto_umbral_carencia:
        return 0.0
    conn = agent.conn_type.get((agent.instinto_alimentacion, 0))
    strength = conn.get("strength", 0) if conn else 0
    consolidada = (agent.instinto_alimentacion, 0) in getattr(agent, 'consolidadas', set())
    if usar_consolidacion:
        if consolidada or strength >= UMBRAL_EAT:
            return 0.0  # ya sabe, come por prediccion
    else:
        if strength >= UMBRAL_EAT:
            return 0.0
    return agent.instinto_fuerza_base * (agent.instinto_umbral_carencia - agent.V_grafo)


def food_decay(inv, moved):
    inv["food"] = max(0.0, inv["food"] - 0.02 - (0.03 if moved else 0.0))


def correr(ag, usar_consolidacion, inst_al=True, ic=True, ides=True, max_p=300):
    env = crafter.Env(); env.reset()
    obs, r, t, info = env.step(0)
    tiles = set();  log = []
    eat_tot = eat_inst = eat_pred = mov = ciclos = hambre_p = 0
    instinto_off_step = None
    comida_flag = False
    n_consolidadas = 0
    for step in range(max_p):
        sem = info["semantic"]; inv = info["inventory"]
        px, py = int(info["player_pos"][0]), int(info["player_pos"][1])
        sf = sem.flatten().tolist()
        sv = [float(v) for v in sf[::64]] + [float(inv["health"])/10.0,
              float(inv["food"])/10.0, float(inv["wood"]), float(inv["stone"]),
              float(inv["iron"])]
        gd, gdist = gradiente(sem, px, py, 5)
        hay_g = gd != (0, 0)
        inc = {a: inc_dir(ag.modelo_mundo, a) for a in MOV}
        ag._gradiente_dir = gd; ag._gradiente_dist = gdist
        ag._hay_gradiente = hay_g; ag._inc_dirs = inc
        ag._config_grad = {"activo": ides, "fuerza": 0.5}
        ag._config_curio = {"activo": ic and hay_g, "fuerza": 0.3}
        f_inst = instinto_eat(ag, usar_consolidacion) if inst_al else 0.0
        ag._fuerza_instinto_eat_override = f_inst if inst_al else 0.0
        a = ag.step(sv, list(range(17)))
        obs, r, t, info = env.step(a)
        # ACOPLE DIRECTO + KURAMOTO (dentro de actualizar_homeostasis)
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
        eq = ag.cuantizar_estado(sv)
        ag.actualizar_modelo_mundo(getattr(ag, 'ultimo_estado_q', eq) or eq, a, eq)
        ag.ultimo_estado_q = eq
        comio = (a == 16)
        if comio:
            eat_tot += 1
            conn = ag.conn_type.get((16, 0))
            st = conn.get("strength", 0) if conn else 0
            cons = (16, 0) in getattr(ag, 'consolidadas', set())
            if (cons or st >= UMBRAL_EAT) and usar_consolidacion:
                eat_pred += 1
                if instinto_off_step is None:
                    instinto_off_step = step
            elif st >= UMBRAL_EAT:
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
        n_consolidadas = len(getattr(ag, 'consolidadas', set()))
        log.append({"step": step, "a": a, "food": float(inv["food"]),
                     "hp": float(inv["health"]), "Vg": round(ag.V_grafo, 3),
                     "status": ag.status, "hay_grad": hay_g})
        if t:
            break
    muerte = {"step": step, "food": float(inv["food"]), "hp": float(inv["health"]),
              "status": ag.status, "Vg": round(ag.V_grafo, 3)} if t else None
    return {"log": log, "tiles": tiles, "muerte": muerte, "pasos": step+1,
            "eat": eat_tot, "eat_inst": eat_inst, "eat_pred": eat_pred,
            "mov": mov, "ciclos": ciclos, "hambre_p": hambre_p,
            "instinto_off_step": instinto_off_step, "consolidadas": n_consolidadas}


def mk(seed):
    ag = SGMAgent(random.Random(seed), D, n_nodes=N_NODES, gamma=0.01)
    ag.set_edges({i: random.sample(range(N_NODES), min(5, N_NODES-1))
                  for i in range(N_NODES)})
    return ag


print("=" * 70)
print(" exp_SGM_0125 — Kuramoto: relevancia sincronizada -> consolidacion -> habituacion")
print("=" * 70)

ra = correr(mk(42), usar_consolidacion=True)    # A: instinto + Kuramoto
rb = correr(mk(42), usar_consolidacion=False)   # B: instinto sin Kuramoto (0124)
rc = correr(mk(42), usar_consolidacion=False, inst_al=False, ic=False, ides=False)  # NC

cnt_a = Counter(ACC.get(l["a"], "?") for l in ra["log"])
cnt_b = Counter(ACC.get(l["a"], "?") for l in rb["log"])
cnt_c = Counter(ACC.get(l["a"], "?") for l in rc["log"])
dom_a = cnt_a.most_common(1)[0] if cnt_a else ("?", 0)
dom_b = cnt_b.most_common(1)[0] if cnt_b else ("?", 0)
dom_c = cnt_c.most_common(1)[0] if cnt_c else ("?", 0)
pa = 100*dom_a[1]/max(1, len(ra["log"])); pb = 100*dom_b[1]/max(1, len(rb["log"]))
pc = 100*dom_c[1]/max(1, len(rc["log"]))

print(f"\n A (inst+Kuramoto): {ra['pasos']}p {len(ra['tiles'])}tiles "
      f"eat={ra['eat']}(inst={ra['eat_inst']},pred={ra['eat_pred']}) "
      f"mov={ra['mov']} ciclos={ra['ciclos']} consol={ra['consolidadas']} "
      f"off_step={ra['instinto_off_step']} dom={dom_a[0]} {pa:.0f}%")
print(f"   muerte={ra['muerte']}")
print(f" B (inst sin Kuramoto): {rb['pasos']}p {len(rb['tiles'])}tiles "
      f"eat={rb['eat']}(inst={rb['eat_inst']},pred={rb['eat_pred']}) "
      f"off_step={rb['instinto_off_step']} dom={dom_b[0]} {pb:.0f}%")
print(f" NC (PPR puro): {rc['pasos']}p {len(rc['tiles'])}tiles eat={rc['eat']} "
      f"dom={dom_c[0]} {pc:.0f}%")

print("\n" + "=" * 70 + "\n METRICAS (A vs B, hipotesis):")
print("=" * 70)
pass_off = (ra["instinto_off_step"] is not None) and ra["instinto_off_step"] < 60
pass_balance = ra["eat_inst"] >= 1 and ra["eat_inst"] <= 3 and ra["eat_pred"] > 0
pass_no_obs = pa < 50
pass_consolida = ra["consolidadas"] > 0
mejora_vs_B = ra["instinto_off_step"] is not None and rb["instinto_off_step"] is None
print(f" PASS instinto_off<60 (A): {pass_off} ({ra['instinto_off_step']})")
print(f" PASS eat balanceado (inst 1-3, pred>0): {pass_balance} "
      f"(inst={ra['eat_inst']}, pred={ra['eat_pred']})")
print(f" PASS no obsesion (dom<50): {pass_no_obs} ({dom_a[0]} {pa:.0f}%)")
print(f" PASS consolida por Kuramoto: {pass_consolida} ({ra['consolidadas']})")
print(f" PASS mejora vs B (A off, B no): {mejora_vs_B}")
print("=" * 70)

out = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), ""
                         "results/results_exp_SGM_0125_kuramoto_habituacion.json")
os.makedirs(os.path.dirname(out), exist_ok=True)
json.dump({
    "experiment_id": "exp_SGM_0125",
    "experiment_name": "kuramoto_habituacion_relevancia",
    "phase": "Fase 8 - Kuramoto: relevancia sincronizada -> consolidacion -> habituacion",
    "date": "2026-08-11",
    "hypothesis": "Kuramoto Eq.3 da senal de relevancia sincronizada: cuando la accion ayuda "
                  "a la homeostasis (food sube => sign=+1), la fase del nodo sincroniza hacia "
                  "la raiz; si cos(phi_i - phi_root) > umbral (Eq.7), la conexion accion->nodo0 "
                  "se consolida (no-podable, persiste). El instinto se apaga en el primer ciclo "
                  "de refuerzo porque el conocimiento persiste; el agente come despues por "
                  "prediccion, no por reflejo. Pred: inst=1-3, pred>0, off_step<60, dom<50%.",
    "config": {"D": D, "N_NODES": N_NODES, "umbral_eat": UMBRAL_EAT,
               "eta_phase": 0.05, "theta_interf": 0.70, "gamma_nodo": 0.01,
               "gamma_conocimiento": 0.001, "signo": "B (+1 si food sube)"},
    "result": {
        "A_inst_kuramoto": {"pasos": ra["pasos"], "tiles": len(ra["tiles"]),
                            "eat": ra["eat"], "eat_instinto": ra["eat_inst"],
                            "eat_prediccion": ra["eat_pred"], "mov": ra["mov"],
                            "ciclos": ra["ciclos"], "consolidadas": ra["consolidadas"],
                            "instinto_off_step": ra["instinto_off_step"],
                            "dominante": f"{dom_a[0]} {pa:.0f}%", "muerte": ra["muerte"]},
        "B_inst_sin_kuramoto": {"pasos": rb["pasos"], "tiles": len(rb["tiles"]),
                                "eat": rb["eat"], "eat_instinto": rb["eat_inst"],
                                "eat_prediccion": rb["eat_pred"],
                                "instinto_off_step": rb["instinto_off_step"],
                                "dominante": f"{dom_b[0]} {pb:.0f}%"},
        "NC_ppr_puro": {"pasos": rc["pasos"], "tiles": len(rc["tiles"]),
                        "eat": rc["eat"], "mov": rc["mov"],
                        "dominante": f"{dom_c[0]} {pc:.0f}%"},
        "pass_instinto_off": pass_off, "pass_balance": pass_balance,
        "pass_no_obsesion": pass_no_obs, "pass_consolida": pass_consolida,
        "pass_mejora_vs_B": mejora_vs_B,
    },
    "script": "experiments/exp_SGM_0125_kuramoto_habituacion.py",
    "results_file": "results/results_exp_SGM_0125_kuramoto_habituacion.json",
    "variant_of": "exp_SGM_0124",
    "lit_refs": ["Kuramoto 1975 - osciladores de fase acoplados",
                 "Arquitectura_Pure_L2_Pandora Eq.3/Eq.7 - dinamicas de fase e interferencia",
                 "Gallistel 1990 - habituacion por conocimiento persistente",
                 "Berridge & Robinson 1998 - wanting operante no permanente"],
    "notes": "Revive la base Kuramoto pausada en la auditoria 0106. Separa 3 escalas: "
             "vitalidad nodo (gamma_nodo efimero), V_grafo (estado cuerpo/homeostasis), "
             "y strength de conocimiento (gamma_conocimiento persistente, consolidable). "
             "En actualizar_homeostasis, food sube => sign=+1 => update_phase(accion,+1) => "
             "si sincroniza con la raiz, la conexion accion->nodo0 se consolida (no podable). "
             "El instinto (compuerta) se apaga si la conexion esta consolidada.",
    "notes_criollo": "Kuramoto es la base que habiamos pausado al limpiar el sustrato. La idea aca "
                     "es que la FASE de un nodo (su 'sincronia' con el ser/raiz) dice si ese nodo "
                     "le importa al sistema AHORA. Cuando comer hace subir el food, la fase del "
                     "nodo 'comer' se alinea con la raiz (es rele%ante), y esa relevancia 'fija' "
                     "el conocimiento: la conexion 'comer->estar bien' se consolida y ya no se "
                     "olvida con la poda. Entonces el instinto (el reflejo de probar de nacimiento) "
                     "ya no hace falta: el agente APRENDIO que comer sirve y lo hace por "
                     "conocimiento, no por reflejo. Eso es la habituacion por relevancia: el "
                     "instinto muere cuando el conocimiento nace.",
}, open(out, "w"), indent=2)
print(f"\n Guardado en: {out}")