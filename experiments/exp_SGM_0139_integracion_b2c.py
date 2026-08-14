#!/usr/bin/env python3
"""exp_SGM_0139 — INTEGRACION B2c COMPLETA + VIDAS COMPLETAS (patrones detallados).

DESPUES de B2c (place cell -> conexion -> accion_que_funciono en actualizar_homeostasis),
se corre la INTEGRACION COMPLETA en el entorno real. Como pidio Luciano:
  - varias seeds DIFFERENTES
  - vida/s COMPLETA/S: se corre hasta MUERTE NATURAL (no corte por paso), o limite alto.
  - registro DETALLADO de patrones por paso (que hace, donde, en que lugar, con que senal)
    para analizar DESPUES: que hace el agente, que no, como y por que.

HIPOTESIS falsable: con B2c (lugar->do aprendido cuando comer funciona), en alguna seed el
agente comera efectivo (comio_efectivo>0). El mapa emergente + el Hebb espacial cierran el
acople. SI CIERTA: comio_efectivo>0, y en el log se ve que el agente ejecuta 'do' en lugares
donde aprendio que hay comida. SI FALSA: comio_efectivo=0 y el log muestra el lugar con comida
pero el agente no hace 'do' ahi (la integracion sigue sin cerrar el acople fino).

Se guarda un LOG por seed para el analisis de patrones (filtrar/analizar despues del run).
"""
import sys, os, random, json, hashlib
from collections import Counter, defaultdict
sys.path.insert(0, os.path.expanduser("~/vaults/vega-vault/NOUS/DSCN-G/EXPERIMENTS/SGM"))
import importlib, sgm_core; importlib.reload(sgm_core)
from sgm_core import SGMAgent
import crafter
import numpy as np

D = 128; N_NODES = 64
ACC = {0:"noop",1:"mv_l",2:"mv_r",3:"mv_u",4:"mv_d",5:"do",6:"sleep",
       7:"p_stone",8:"p_table",9:"p_furnace",10:"p_plant",11:"mk_w_pick",
       12:"mk_s_pick",13:"mk_i_pick",14:"mk_w_sword",15:"mk_s_sword",
       16:"mk_i_sword"}
MOV = {1,2,3,4}
COMIDA = {14, 18}; ENEMIGO = {15, 16}; DO = 5
MOVE_DIR = {1: (-1, 0), 2: (1, 0), 3: (0, -1), 4: (0, 1)}
UMBRAL_EAT = 2.0


def gradiente(sem, px, py, clases, r=8):
    b, bd = (0, 0), r * r + 1
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            if dx == 0 and dy == 0:
                continue
            x, y = px + dx, py + dy
            if 0 <= x < sem.shape[1] and 0 <= y < sem.shape[0]:
                if sem[y, x] in clases:
                    d = abs(dx) + abs(dy)
                    if d < bd:
                        bd, b = d, (dx, dy)
    return b, bd


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


def obs_clave(pos, enfrente):
    payload = f"{pos}|{enfrente}"
    return hashlib.md5(payload.encode()).hexdigest()[:12]


def correr_vida(seed, max_p=1200):
    """Vida completa (hasta muerte natural o max_p). Devuelve resumen + log detallado."""
    ag = SGMAgent(random.Random(seed), D, n_nodes=N_NODES, gamma=0.01)
    ag.set_edges({i: random.sample(range(N_NODES), min(5, N_NODES - 1))
                  for i in range(N_NODES)})
    ag.instinto_alimentacion = DO   # ADAPTADOR: accion de interactuar de Crafter
    env = crafter.Env(); env.reset()
    obs, r, t, info = env.step(0)
    log = []
    tiles = set(); comio_ef = comio_vac = ataco = mov = 0
    prev_pos = np.array(info["player_pos"], dtype=int)
    facing = (0, 1); prev_hp = 9.0; place_creados = 0
    acc_hist = []
    for step in range(max_p):
        sem = info["semantic"]; inv = info["inventory"]
        px, py = int(info["player_pos"][0]), int(info["player_pos"][1])
        hp = float(inv["health"])
        sf = sem.flatten().tolist()
        sv = [float(v) for v in sf[::64]] + [float(inv["health"])/10.0,
              float(inv["food"])/10.0, float(inv["wood"]), float(inv["stone"]),
              float(inv["iron"])]
        hambre = max(0.0, 1.0 - inv["food"] / 10.0)
        danio = max(0.0, (prev_hp - hp) / 10.0)
        g_ene, d_ene = gradiente(sem, px, py, ENEMIGO)
        amenaza_env = max(0.0, 1.0 - (d_ene - 1) / 3.0) if d_ene < 999 else 0.0
        amenaza = max(danio * 1.5, amenaza_env * 0.8)
        ex, ey = px + facing[0], py + facing[1]
        enfrente = 0
        hay_comida_cerca = False; hay_enemigo_cerca = False
        if 0 <= ex < 64 and 0 <= ey < 64:
            v = sem[ey, ex]
            if v in COMIDA:
                enfrente = 1
            elif v in ENEMIGO:
                enfrente = 2
        # registra place cell
        bucket = (px // 4, py // 4)
        clave = obs_clave(bucket, enfrente)
        n_place_antes = len(ag.place_cells)
        ag._registrar_place_cell(clave)
        if len(ag.place_cells) > n_place_antes:
            place_creados += 1
        ag._hambre_real = min(1.0, hambre)
        ag._amenaza = min(1.0, amenaza)
        ag._algo_enfrente = enfrente
        g_comida, d_comida = gradiente(sem, px, py, COMIDA)
        hay_comida_cerca = g_comida != (0, 0)
        hay_enemigo_cerca = g_ene != (0, 0)
        if amenaza > hambre and g_ene != (0, 0):
            ag._target_dir = g_ene; ag._target_dist = d_ene
        elif hambre > 0.05 and g_comida != (0, 0):
            ag._target_dir = g_comida; ag._target_dist = d_comida
        else:
            ag._target_dir = (0, 0); ag._target_dist = 0
        ag._gradiente_dir = g_ene if amenaza > hambre else g_comida
        ag._gradiente_dist = d_ene if amenaza > hambre else d_comida
        ag._hay_gradiente = hambre > 0.05 or amenaza > 0.05
        ag._inc_dirs = {a: inc_dir(ag.modelo_mundo, a) for a in MOV}
        ag._config_grad = {"activo": True, "fuerza": 0.5}
        ag._config_curio = {"activo": True, "fuerza": 0.3}
        if inv["food"] < ag.umbral_hambre_food:
            conn = ag.conn_type.get((DO, 0))
            st = conn.get("strength", 0) if conn else 0
            if not ((DO, 0) in ag.consolidadas) and st < UMBRAL_EAT:
                care = max(0.0, ag.umbral_hambre_food - inv["food"])
                ag._fuerza_instinto_eat_override = ag.instinto_fuerza_base * (care / ag.umbral_hambre_food)
            else:
                ag._fuerza_instinto_eat_override = 0.0
        else:
            ag._fuerza_instinto_eat_override = 0.0
        a = ag.step(sv, list(range(17)))
        food_antes = float(inv["food"])
        place_act = ag.place_activo
        obs, r, t, info = env.step(a)
        food_despues = float(inv["food"])
        cur_pos = np.array(info["player_pos"], dtype=int)
        if a in MOV:
            delta = tuple((cur_pos - prev_pos).tolist())
            facing = delta if delta != (0, 0) else MOVE_DIR[a]
        prev_pos = cur_pos
        ag.actualizar_homeostasis(inv["food"], inv["health"])
        ag._mutar_omega_lugar(float(inv["food"]) / 10.0)
        if a == DO:
            if food_despues > food_antes:
                comio_ef += 1
            elif enfrente == 2:
                ataco += 1
            else:
                comio_vac += 1
        pain = 0.0
        if r < 0:
            pain = abs(r)
        elif inv["health"] < 5:
            pain = 0.1
        ag.reward(max(0.0, r), pain)
        pos = (px, py)
        if pos not in tiles:
            tiles.add(pos); ag.reward(0.05, 0.0)
        ag.incertidumbre_acum = max(0, ag.incertidumbre_acum - 0.01)
        eq = ag.cuantizar_estado(sv)
        ag.actualizar_modelo_mundo(getattr(ag, 'ultimo_estado_q', eq) or eq, a, eq)
        ag.ultimo_estado_q = eq
        if a in MOV:
            mov += 1
        prev_hp = hp
        acc_hist.append(a)
        # REGISTRO detallado de patrones (que hace, donde, senales, resultado do)
        log.append({
            "step": step, "acc": a, "acc_nombre": ACC.get(a, "?"),
            "food": round(float(inv["food"]), 1), "hp": round(float(inv["health"]), 0),
            "hambre": round(hambre, 2), "amenaza": round(min(1.0, amenaza), 2),
            "enfrente": enfrente, "place_activo": place_act,
            "hay_comida_cerca": hay_comida_cerca, "hay_enemigo_cerca": hay_enemigo_cerca,
            "do_efectivo": bool(a == DO and food_despues > food_antes),
            "reward": round(float(r), 2),
        })
        if t:
            break
    resumen = {
        "seed": seed, "pasos": step + 1, "tiles": len(tiles),
        "comio_efectivo": comio_ef, "comio_vacio": comio_vac,
        "ataco": ataco, "mov": mov, "place_creados": place_creados,
        "n_place_cells": len(ag.place_cells), "consol": len(ag.consolidadas),
        "frec_acciones": dict(Counter(ACC.get(x, "?") for x in acc_hist)),
        "muerte": ("natural" if t else "limite_pasos"),
        "food_final": float(inv["food"]), "hp_final": float(inv["health"]),
    }
    return resumen, log


print("=" * 70)
print(" exp_SGM_0139 — Integracion B2c COMPLETA + vidas completas (patrones detallados)")
print("=" * 70)
SEEDS = [42, 7, 99, 123, 2024]
resumenes = []
todos_logs = {}
for seed in SEEDS:
    res, log = correr_vida(seed, max_p=1200)
    resumenes.append(res)
    todos_logs[str(seed)] = log
    print(f" seed {seed}: {res['pasos']}p {res['tiles']}tiles "
          f"comio_ef={res['comio_efectivo']} comio_vac={res['comio_vacio']} "
          f"ataco={res['ataco']} mov={res['mov']} place={res['place_creados']}({res['n_place_cells']}) "
          f"muerte={res['muerte']} food_fin={res['food_final']} hp_fin={res['hp_final']}")
    print(f"    frec: {list(res['frec_acciones'].items())[:3]}...")

out = os.path.expanduser("~/vaults/vega-vault/NOUS/DSCN-G/EXPERIMENTS/SGM/"
                         "results/results_exp_SGM_0139_integracion_b2c.json")
os.makedirs(os.path.dirname(out), exist_ok=True)
json.dump({
    "experiment_id": "exp_SGM_0139",
    "experiment_name": "integracion_b2c_vidas_completas",
    "phase": "Fase 8 - integracion B2c completa (place cell -> do) + vidas completas",
    "date": "2026-08-11",
    "hypothesis": "B2c (lugar->do aprendido cuando comer funciona) cierra el acople: el agente "
                  "comera efectivo (comio_efectivo>0) en alguna seed. Vidas completas + multiple seeds.",
    "config": {"D": D, "N_NODES": N_NODES, "max_pasos": 1200, "seeds": SEEDS,
               "agnostico": True, "instinto_alimentacion": "adaptador (do=5)"},
    "result": {"resumenes": resumenes,
               "log_detallado": "ver results_exp_SGM_0139... los logs por seed estan en el archivo adjunto si se guarda"},
    "script": "experiments/exp_SGM_0139_integracion_b2c.py",
    "results_file": "results/results_exp_SGM_0139_integracion_b2c.json",
    "variant_of": "exp_SGM_0138",
    "notes": "Integracion completa de B2c: en actualizar_homeostasis, cuando el do es efectivo, "
             "se aprende lugar->do (Hebb espacial). El place cell activo influye en el PPR via la "
             "conexion aprendida. Se corre vida completa (hasta muerte) en 5 seeds y se registra "
             "log de patrones por paso para analisis posterior.",
    "notes_criollo": "Ahora le dimos el mapa que armo y lo conectamos a la mano: si en un lugar "
                     "comer funciono, el bicho aprende que ahi se come. Con eso corre varias vidas "
                     "completas y registramos TODO lo que hace (que accion, donde, que senales) "
                     "para ver los patrones: que hace, que no, como y por que.",
}, open(out, "w"), indent=2)
print(f"\n Guardado en: {out}")