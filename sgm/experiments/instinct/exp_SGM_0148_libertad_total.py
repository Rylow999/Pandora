#!/usr/bin/env python3
"""exp_SGM_0148 — LIBERTAD TOTAL: el agente actúa libremente en todo Crafter.

MISION (Luciano 2026-08-11): "que pueda actuar libremente sin restricciones en el mundo,
varias seeds, varias vidas, aunque lleve 1 hora, no importa. Ver que hace, que mezcla,
que inventa." MAS interesante que lograr comer.

Esto es EXPLORACION AUTOTELICA PURA sin objetivo impuesto. Le damos TODAS las acciones
(17 de Crafter), SIN prioridad a comer, SIN reward shaping a hitos, SIN forzar navegacion.
Solo el sustrato: curiosidad (PE), drive anti-noop, duda, mapa emergente, modelo de objeto,
red accion->resultado. Y observamos QUE hace, QUE mezcla, QUE inventa.

La clave es que NO hay 'meta' — el comportamiento emerge libre. Registramos por paso:
- accion ejecutada
- recursos acumulados en el invetario
- resultados (que subio/bajo)
- lugar actual, enemigos, comida
para ANALIZAR patrones de comportamiento libre (atractores, secuencias, inventos).

HIPOTESIS DE OBSERVACION (no es falsable forzando, es descubrimiento):
¿El sustrado, al actuar libre, genera SECUENCIAS útiles (madera->crafteo->mina) o cae en
atractores/caos? ¿Aparecen mezclas de acciones que producen resultados? Se observa.

Se corren VARIAS seeds y VARIAS vidas con TIEMPO LARGO (max_p alto). Log detallado.
"""
import sys, os, random, json, hashlib
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
import importlib, sgm_core; importlib.reload(sgm_core)
from sgm.core.sgm_core import SGMAgent
import crafter
import numpy as np

D = 128; N_NODES = 64
ACC = {0:"noop",1:"mv_l",2:"mv_r",3:"mv_u",4:"mv_d",5:"do",6:"sleep",
       7:"p_stone",8:"p_table",9:"p_furnace",10:"p_plant",11:"mk_wood_pick",
       12:"mk_stone_pick",13:"mk_iron_pick",14:"mk_wood_sword",15:"mk_stone_sword",
       16:"mk_iron_sword"}
MOV = {1,2,3,4}
COMIDA = {14, 18}
DO = 5
MOVE_DIR = {1: (-1, 0), 2: (1, 0), 3: (0, -1), 4: (0, 1)}
TODAS_ACCIONES = list(range(17))  # TODO lo disponible en Crafter


def inventario_de(info):
    inv = info['inventory']
    return {k: int(v) for k, v in inv.items() if v > 0}


def inc_dir(m, a):
    if not m:
        return 1.0
    t, nw = 0, 0
    for (e, ac), tr in m.items():
        if ac == a:
            t += sum(tr.values())
            for sq, c in tr.items():
                if c <= 1:
                    nw += 1
    return nw / max(1, t)


def correr_vida(ag, env, vida_i, max_p=1200):
    """Libertad total: el agente elige de TODAS las acciones, sin meta. Log por paso."""
    obs, r, t, info = env.step(0)
    prev_pos = np.array(info["player_pos"], dtype=int); facing = (0, 1)
    prev_hp = 9.0
    log = []
    tiles = set()
    inv_log = inventario_de(info)
    logros = set()
    for step in range(max_p):
        sem = info["semantic"]; inv = info["inventory"]
        px, py = int(info["player_pos"][0]), int(info["player_pos"][1])
        hp = float(inv["health"])
        sv = [float(v) for v in sem.flatten().tolist()[::64]] + \
             [float(inv["health"])/10.0, float(inv["food"])/10.0,
              float(inv["wood"]), float(inv["stone"]), float(inv["iron"])]
        hambre = max(0.0, 1.0 - inv["food"] / 10.0)
        # SUSTRATO LIBRE: curiosidad+drive+duda, SIN meta impuesta, SIN reward shaping a hitos
        ag._hambre_real = min(1.0, hambre)
        ag._amenaza = 0.0
        ag._posicion_actual = (px, py)
        ag._algo_enfrente = 0
        ag._config_grad = {"activo": False, "fuerza": 0.0}
        ag._config_curio = {"activo": True, "fuerza": 0.4}
        ag._inc_dirs = {a: inc_dir(ag.modelo_mundo, a) for a in MOV}
        ag._hay_gradiente = False
        ag.meta_recordada = None

        a = ag.step(sv, TODAS_ACCIONES)  # puede elegir cualquiera de las 17
        food_antes = float(inv["food"])
        obs, r, t, info = env.step(a)
        food_despues = float(inv["food"])
        cur_pos = np.array(info["player_pos"], dtype=int)
        if a in MOV:
            delta = tuple((cur_pos - prev_pos).tolist())
            facing = delta if delta != (0, 0) else MOVE_DIR[a]
        prev_pos = cur_pos
        ag.actualizar_homeostasis(inv["food"], inv["health"])
        # aprender resultado del mundo (red accion->recurso)
        nuevo_inv = inventario_de(info)
        ag._resultado_mundo_prev = inv_log
        ag._resultado_mundo_act = nuevo_inv
        ag._aprender_resultado_mundo(a)
        inv_log = nuevo_inv
        # nuevos logros
        nuevos = [nm for nm, c in info['achievements'].items() if c > 0 and nm not in logros]
        logros |= set(nuevos)
        # reward interno del sustrato (solo dolor, no shaping)
        pain = abs(r) if r < 0 else 0.0
        ag.reward(max(0.0, r), pain)
        pos = (px, py)
        if pos not in tiles:
            tiles.add(pos)
        eq = ag.cuantizar_estado(sv)
        ag.actualizar_modelo_mundo(getattr(ag, 'ultimo_estado_q', eq) or eq, a, eq)
        ag.ultimo_estado_q = eq
        # registro por paso (patrones)
        log.append({"step": step, "acc": a, "acc_nombre": ACC.get(a, "?"),
                    "food": float(inv["food"]), "hp": hp, "hambre": round(hambre, 2),
                    "inv": nuevo_inv, "logros_nuevos": nuevos, "lugar": (px, py),
                    "do_efectivo": a == DO and food_despues > food_antes})
        if t:
            break
    resumen = {"vida": vida_i, "pasos": step+1, "tiles": len(tiles),
               "logros": sorted(logros), "n_logros": len(logros),
               "inv_final": inventario_de(info), "consol": len(ag.consolidadas),
               "n_place": len(ag.place_cells), "n_conn_resultado": len(ag.conn_type)}
    return resumen, log


print("=" * 70)
print(" exp_SGM_0148 — LIBERTAD TOTAL: el agente actua libre en todo Crafter")
print("=" * 70)
SEEDS = [42, 7, 2024]
VIDAS = 4
MAXP = 1500
TODOS_RESULT = []
for seed in SEEDS:
    ag = SGMAgent(random.Random(seed), D, n_nodes=N_NODES, gamma=0.01)
    ag.set_edges({i: random.sample(range(N_NODES), min(5, N_NODES - 1)) for i in range(N_NODES)})
    ag.instinto_alimentacion = DO
    env = crafter.Env()
    print(f"\n--- seed {seed} ---")
    for v in range(VIDAS):
        env.reset(); ag.reset_episodio()
        res, log = correr_vida(ag, env, v, max_p=MAXP)
        TODOS_RESULT.append({"seed": seed, **res})
        print(f"  vida {v}: {res['pasos']}p {res['tiles']}tiles logros={res['n_logros']}/{' '.join(res['logros'][:6])}"
              f" consol={res['consol']} place={res['n_place']} conn_res={res['n_conn_resultado']}")

out = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), ""
                         "results/results_exp_SGM_0148_libertad_total.json")
os.makedirs(os.path.dirname(out), exist_ok=True)
json.dump({
    "experiment_id": "exp_SGM_0148",
    "experiment_name": "libertad_total",
    "phase": "Fase 8 - libertad total: el agente actua libre en todo Crafter (observacion)",
    "date": "2026-08-11",
    "mision": "Luciano: actuar libremente sin restricciones, varias seeds/vidas, que haga/mezcle/"
              "invente. Interesa mas la emergencia de comportamiento que 'comer'.",
    "config": {"D": D, "N_NODES": N_NODES, "seeds": SEEDS, "vidas": VIDAS, "max_pasos": MAXP,
               "acciones_disponibles": 17, "objetivo": "ninguno (libertad total)"},
    "result": {"vidas": TODOS_RESULT, "log_detallado": "omitido por tamano (los patrones se analizan aparte)"},
    "script": "experiments/exp_SGM_0148_libertad_total.py",
    "results_file": "results/results_exp_SGM_0148_libertad_total.json",
    "variant_of": "exp_SGM_0145",
    "lit_refs": ["exploracion autotelica (Panksepp SEEKING)", "curiosidad (Oudeyer)",
                 "behavior emergence (no objetivo impuesto)"],
    "notes": "Libertad total con TODO el espacio de acciones de Crafter, sin meta, observando "
             "que emerge. Autotelismo puro + red accion->resultado para que descubra estructura.",
    "notes_criollo": "Le damos al bicho la libertad TOTAL y sin mision: que haga lo que quiera "
                     "en todo el mundo, por horas si hace falta. Vamos a mirar que hace, que "
                     "inventa, si arma secuencias utiles o se queda en vericuetos. Eso es mas "
                     "interesante que obligarlo a comer.",
}, open(out, "w"), indent=2)
print(f"\n Guardado en: {out}")