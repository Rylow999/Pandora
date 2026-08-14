#!/usr/bin/env python3
"""exp_SGM_0138 — PLACE CELLS EMERGENTES + NODOS QUE MUTAN (B2).

DECISION (Luciano 2026-08-11): el sustrato debe ser INDEPENDIENTE del entorno (servir en
Crafter, Minecraft, etc). Los hardcodes de mapeo (acciones=5=do, objetos=14/18) viven en
el ADAPTADOR (este harness), NO en el core. El core (0138) ahora tiene:
  - _registrar_place_cell(obs_clave): crea un nodo-lugar emergente cuando llega a una
    observacion no familiar (agnostico).
  - _mutar_omega_lugar(senal): el omega del lugar activo MUTA localmente hacia el resultado
    util, sin tocar el resto (leccion 0109-0111).

ESTE HARNESS (adaptador Crafter) traduce la senal del entorno a abstracta:
  obs_clave = hash del estado local (posicion relevante + contenido enfrente) -> generico.
  senales _hambre_real, _amenaza, _algo_enfrente (1=comida, 2=amenaza) ya son genericas.
  ag.instinto_alimentacion = 5 (adaptador: accion 'do' de Crafter).

HIPOTESIS falsable: con place cells + mutacion, el agente que explora CREA nodos-lugar, y
cuando un lugar tiene comida enfrente + hambre + la consolidacion (Hebb/Kuramoto) asocia
eso lugar->do->supervivencia, el agente ejecuta 'do' EFECTIVO (comio_efectivo>0) mas veces
que el 0137. El nodo-lugar muta hacia identidad de supervivencia.

SI hipotesis: comio_efectivo>0 en >=1 seed, place_cells creados>0, mutacion activa.
SI falsa: comio_efectivo=0, o los place cells no se integran (no cambian el comportamiento).

LITERATURA: O'Keefe 1971 (place cells), Stachenfeld 2017 (place cells como predicciones),
Crafter paper (Hafner ICLR 2022: RL aprenden acople del input, no lo pre-calculan).
"""
import sys, os, random, json, hashlib
from collections import Counter
sys.path.insert(0, os.path.expanduser("~/vaults/vega-vault/NOUS/DSCN-G/EXPERIMENTS/SGM"))
import importlib, sgm_core; importlib.reload(sgm_core)
from sgm_core import SGMAgent
import crafter
import numpy as np

D = 128; N_NODES = 64
MOV = {1,2,3,4}
# ADAPTADOR (mapeo del entorno -> generico). Los IDs viven AQUI, no en el core.
COMIDA = {14, 18}   # cow, plant de Crafter
ENEMIGO = {15, 16}
DO = 5              # accion 'interactuar' de Crafter
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


def obs_clave_de(pos, enfrente):
    """ADAPTADOR: construye la 'observacion' generica del lugar (posicion relevante + que
    hay enfrente). Agnostic del entorno: es una etiqueta hash, no valores de Crafter."""
    payload = f"{pos}|enf={enfrente}"
    return hashlib.md5(payload.encode()).hexdigest()[:12]


def correr(seed, max_p=600):
    ag = SGMAgent(random.Random(seed), D, n_nodes=N_NODES, gamma=0.01)
    ag.set_edges({i: random.sample(range(N_NODES), min(5, N_NODES - 1))
                  for i in range(N_NODES)})
    # ADAPTADOR: configurar la accion de interaccion del entorno (Crafter=do=5)
    ag.instinto_alimentacion = DO
    env = crafter.Env(); env.reset()
    obs, r, t, info = env.step(0)
    tiles = set(); comio_ef = comio_vac = ataco = mov = ciclos = 0
    food_bajo = False; prev_pos = np.array(info["player_pos"], dtype=int)
    facing = (0, 1); prev_hp = 9.0; place_creados = 0
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
        # enfrente (adaptador): contenido en pos+facing
        ex, ey = px + facing[0], py + facing[1]
        enfrente = 0
        if 0 <= ex < 64 and 0 <= ey < 64:
            v = sem[ey, ex]
            if v in COMIDA:
                enfrente = 1
            elif v in ENEMIGO:
                enfrente = 2
        # place cell emergente: registrar la observacion del lugar actual
        # (posicion redondeada a bucket 4x4 para generalizar + contenido enfrente)
        bucket = (px // 4, py // 4)
        clave = obs_clave_de(bucket, enfrente)
        n_place_antes = len(ag.place_cells)
        ag._registrar_place_cell(clave)
        if len(ag.place_cells) > n_place_antes:
            place_creados += 1
        # senales genericas ya manejadas por el core
        ag._hambre_real = min(1.0, hambre)
        ag._amenaza = min(1.0, amenaza)
        ag._algo_enfrente = enfrente
        # re-encare (adaptador traduce el gradiente a target generico)
        g_comida, d_comida = gradiente(sem, px, py, COMIDA)
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
        # instinto comer override (adaptador)
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
        # accion
        a = ag.step(sv, list(range(17)))
        food_antes = float(inv["food"])
        obs, r, t, info = env.step(a)
        food_despues = float(inv["food"])
        cur_pos = np.array(info["player_pos"], dtype=int)
        if a in MOV:
            delta = tuple((cur_pos - prev_pos).tolist())
            facing = delta if delta != (0, 0) else MOVE_DIR[a]
        prev_pos = cur_pos
        ag.actualizar_homeostasis(inv["food"], inv["health"])
        # MUTACION del omega del lugar activo hacia el resultado (food normalizado 0-1).
        # Solo el nodo-lugar activo; agnostico; refuerza la identidad si el lugar 'funciona'.
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
        if inv["food"] < 3:
            food_bajo = True
        elif food_bajo and inv["food"] >= 7:
            ciclos += 1; food_bajo = False
        if a in MOV:
            mov += 1
        prev_hp = hp
        if t:
            break
    muerte = {"step": step, "food": float(inv["food"]), "hp": float(inv["health"]),
              "Vg": round(ag.V_grafo, 3)} if t else None
    return {"seed": seed, "pasos": step + 1, "tiles": len(tiles),
            "comio_efectivo": comio_ef, "comio_vacio": comio_vac,
            "ataco": ataco, "mov": mov, "ciclos": ciclos, "muerte": muerte,
            "consol": len(ag.consolidadas), "place_creados": place_creados,
            "n_place_cells": len(ag.place_cells)}


print("=" * 70)
print(" exp_SGM_0138 — PLACE CELLS EMERGENTES + NODOS QUE MUTAN (B2, agnostico)")
print("=" * 70)
for seed in [42, 7, 99]:
    res = correr(seed, max_p=600)
    print(f" seed {seed}: {res['pasos']}p {res['tiles']}tiles "
          f"comio_ef={res['comio_efectivo']} comio_vac={res['comio_vacio']} "
          f"ataco={res['ataco']} mov={res['mov']} ciclos={res['ciclos']} "
          f"place_creados={res['place_creados']}(total {res['n_place_cells']}) "
          f"consol={res['consol']} muerte={res['muerte']}")

out = os.path.expanduser("~/vaults/vega-vault/NOUS/DSCN-G/EXPERIMENTS/SGM/"
                         "results/results_exp_SGM_0138_place_cells_emergentes.json")
os.makedirs(os.path.dirname(out), exist_ok=True)
json.dump({
    "experiment_id": "exp_SGM_0138",
    "experiment_name": "place_cells_emergentes_b2",
    "phase": "Fase 8 - place cells emergentes + nodos que mutan (B2, agnostico)",
    "date": "2026-08-11",
    "hypothesis": "Con place cells emergentes + mutacion local del omega, el sustrato construye "
                  "su propio mapa del entorno (agnostico). Cuando un lugar tiene comida enfrente + "
                  "hambre + consolidacion, el agente ejecuta do EFECTIVO (comio_efectivo>0) mas "
                  "que en 0137. El nodo-lugar muta hacia identidad de supervivencia.",
    "config": {"D": D, "N_NODES": N_NODES, "max_pasos": 600, "seeds": [42, 7, 99],
               "agnostico": "True (core no hardcodea entorno)", "instinto_alimentacion": "configurado por adaptador",
               "mutacion_tasa": 0.05},
    "result": "ver stdout",
    "script": "experiments/exp_SGM_0138_place_cells_emergentes.py",
    "results_file": "results/results_exp_SGM_0138_place_cells_emergentes.json",
    "variant_of": "exp_SGM_0137",
    "lit_refs": ["O'Keefe 1971 (place cells)", "Stachenfeld 2017 (place cells como predicciones)",
                 "Hafner ICLR 2022 (RL aprenden acople del input)"],
    "notes": "El core es ahora AGNOSTICO del entorno: instinto_alimentacion=None (configurable), "
             "place cells emergentes (_registrar_place_cell), mutacion local (_mutar_omega_lugar). "
             "El adaptador (harness) traduce los IDs de Crafter a senales genericas. "
             "Cumple el principio de Luciano: el mismo sustrato sirve en Crafter, Minecraft, etc.",
    "notes_criollo": "El bicho ahora se arma su propio mapa a medida que explora: cada lugar nuevo "
                     "le crea una 'celda de lugar' (identidad). Cuando esa celda tiene comida "
                     "delante + hambre, aprende que ahi se come bien, y la celda 'muta' hacia ser "
                     "una celda de supervivencia. Todo sin saber que es Crafter: el sustrato es "
                     "neutral, el que le traduce el mundo es el adapter.",
}, open(out, "w"), indent=2)
print(f"\n Guardado en: {out}")