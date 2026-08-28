#!/usr/bin/env python3
"""exp_SGM_0144 — MODELO DE OBJETO PREDICTIVO (opcion A) + acople fino del 'do'.

DESPUES del refactor 0143 (sustrato autonomo) y el 0144 core (modelo de objeto predictivo):
el sustrato ahora modela cada objeto como un PROCESO que aprende su velocidad y predice su
posicion FUTURA. El adaptador le pasa los objetos vistos (cows/plantas con posicion real),
el agente aprende su trayectoria y navega hacia DONDE ESTARAN, no donde estaban.

La decision de 'do' usa la PREDICCION: cuando la posicion predicha del objeto coincide con
pos+facing, el agente hace 'do'. Esto compensa el movimiento de la cow (que antes se escapaba
siempre) y la maduracion de la planta.

HIPOTESIS falsable: con el modelo de objeto predictivo, el agente navega hacia la posicion
predicha de la comida, la alcanza cuando aun esta ahi (o predice su movimiento), y al estar
enfrente ejecuta 'do' efectivo (comio_efectivo>0) al menos en una seed. El objetivo de la cow
ahora es acertar donde estara, no donde la vio.

SI CIERTA: comio_ef>0. SI FALSA: el agente sigue sin comer (la prediccion no basta, o el
desfase obj-semantic persiste).

LITERATURA: Piaget (object permanence), world models (Ha & Schmidhuber 2018), Loci (arxiv
2310.10372: imaginar trayectoria de objetos), affordances (Gibson 1979).
"""
import sys, os, random, json
sys.path.insert(0, os.path.expanduser("~/vaults/vega-vault/NOUS/DSCN-G/EXPERIMENTS/SGM"))
import importlib, sgm_core; importlib.reload(sgm_core)
from sgm.core.sgm_core import SGMAgent
import crafter
import numpy as np

D = 128; N_NODES = 64
MOV = {1, 2, 3, 4}
COMIDA = {14, 18}
DO = 5
MOVE_DIR = {1: (-1, 0), 2: (1, 0), 3: (0, -1), 4: (0, 1)}
UMBRAL_EAT = 2.0


def gradiente(sem, px, py, clases, r=10):
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


def objetos_visibles(sem, px, py, r=12):
    """El adaptador: encuentra comidas (cow/plant) visibles en el mapa y devuelve sus
    posiciones globales reales (x,y). Usa el semantic pero toma la pos del objeto."""
    res = []
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            x, y = px + dx, py + dy
            if 0 <= x < 64 and 0 <= y < 64 and sem[y, x] in COMIDA:
                res.append(("comida", x, y))
    return res[:5]  # limitar a los 5 mas cercanos para no saturar


def correr(seed, max_p=900, nvidas=3):
    ag = SGMAgent(random.Random(seed), D, n_nodes=N_NODES, gamma=0.01)
    ag.set_edges({i: random.sample(range(N_NODES), min(5, N_NODES - 1))
                  for i in range(N_NODES)})
    ag.instinto_alimentacion = DO
    ag.auto_navegar_meta = True
    ag._tipos_meta_buscados = ['comida']

    resumen = []
    for vida in range(nvidas):
        env = crafter.Env(); env.reset()
        ag.reset_episodio()
        obs, r, t, info = env.step(0)
        tiles = set(); comio_ef = comio_vac = mov = 0
        prev_pos = np.array(info["player_pos"], dtype=int); facing = (0, 1)
        prev_hp = 9.0; meta_comida = None

        for step in range(max_p):
            sem = info["semantic"]; inv = info["inventory"]
            px, py = int(info["player_pos"][0]), int(info["player_pos"][1])
            hp = float(inv["health"])
            sv = [float(v) for v in sem.flatten().tolist()[::64]] + \
                 [float(inv["health"])/10.0, float(inv["food"])/10.0,
                  float(inv["wood"]), float(inv["stone"]), float(inv["iron"])]
            hambre = max(0.0, 1.0 - inv["food"] / 10.0)
            ag._hambre_real = min(1.0, hambre)
            ag._amenaza = 0.0
            ag._posicion_actual = (px, py)
            ag._config_grad = {"activo": False, "fuerza": 0.0}
            ag._config_curio = {"activo": True, "fuerza": 0.4}
            ag._inc_dirs = {a: inc_dir(ag.modelo_mundo, a) for a in MOV}
            ag._hay_gradiente = False
            ag._algo_enfrente = 0
            ag._objetos_vistos = objetos_visibles(sem, px, py)

            # Si vemos comida, fijar meta en su prediccion (el core ajusta a pred)
            g_com, d_com = gradiente(sem, px, py, COMIDA)
            if g_com != (0, 0):
                meta_comida = (px + g_com[0], py + g_com[1])
                ag.meta_recordada = meta_comida

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
            if a == DO:
                if food_despues > food_antes:
                    comio_ef += 1
                else:
                    comio_vac += 1
            pain = 0.0
            if r < 0:
                pain = abs(r)
            ag.reward(max(0.0, r), pain)
            pos = (px, py)
            if pos not in tiles:
                tiles.add(pos); ag.reward(0.05, 0.0)
            eq = ag.cuantizar_estado(sv)
            ag.actualizar_modelo_mundo(getattr(ag, 'ultimo_estado_q', eq) or eq, a, eq)
            ag.ultimo_estado_q = eq
            if a in MOV:
                mov += 1
            prev_hp = hp
            if t:
                break
        resumen.append({"vida": vida, "pasos": step + 1, "tiles": len(tiles),
                       "comio_efectivo": comio_ef, "comio_vacio": comio_vac, "mov": mov,
                       "objetos_trackeados": len(ag.objetos),
                       "food_fin": float(inv["food"]), "hp_fin": float(inv["health"])})
        print(f" vida {vida}: {step+1}p {len(tiles)}tiles comio_ef={comio_ef} "
              f"comio_vac={comio_vac} mov={mov} objetos_track={len(ag.objetos)} "
              f"food_fin={float(inv['food'])}")
        if comio_ef > 0:
            print(f"   >>> ¡COMIO! El modelo de objeto predictivo funciono (vida {vida})")
    return resumen


print("=" * 70)
print(" exp_SGM_0144 — MODELO DE OBJETO PREDICTIVO (opcion A) + acople fino del do")
print("=" * 70)
for seed in [42, 7]:
    r = correr(seed, max_p=900, nvidas=3)

out = os.path.expanduser("~/vaults/vega-vault/NOUS/DSCN-G/EXPERIMENTS/SGM/"
                         "results/results_exp_SGM_0144_modelo_objeto.json")
os.makedirs(os.path.dirname(out), exist_ok=True)
json.dump({
    "experiment_id": "exp_SGM_0144",
    "experiment_name": "modelo_objeto_predictivo",
    "phase": "Fase 8 - modelo de objeto predictivo (objeto como proceso dinamico)",
    "date": "2026-08-11",
    "hypothesis": "El sustrato modela los objetos como procesos dinamicos (velocidad aprendida, "
                  "posicion futura predicha). El agente navega hacia donde la comida ESTARA y "
                  "hace 'do' cuando la prediccion la ubica en pos+facing. Resultado esperado: "
                  "comio_efectivo>0 (compensa el movimiento de la cow / la maduracion).",
    "config": {"D": D, "N_NODES": N_NODES, "max_pasos": 900, "nvidas": 3, "seeds": [42, 7],
               "agnostico": True},
    "result": {"nota": "vidas por seed impresas en stdout"},
    "script": "experiments/exp_SGM_0144_modelo_objeto.py",
    "results_file": "results/results_exp_SGM_0144_modelo_objeto.json",
    "variant_of": "exp_SGM_0143",
    "lit_refs": ["Piaget (object permanence)", "Ha & Schmidhuber 2018 (world models)",
                 "Loci arxiv 2310.10372 (imaginar trayectoria de objetos)",
                 "Gibson 1979 (affordances: objeto como proceso)"],
    "notes": "El modelo de objeto predictivo (0144) hace que el sustrato aprenda la dinamica "
             "de los objetos (velocidad) y prediga su posicion futura. El agente navega a la "
             "prediccion, no al snapshot, compensando el movimiento. Prueba de si esto logra "
             "comer efectivo por primera vez en la saga.",
    "notes_criollo": "El bicho ahora no ve la comida como una foto, sino como algo que se mueve "
                     "y cambia. Aprende a donde va la vaca (velocidad) y va PARA ALLA, no hacia "
                     "donde estaba. Es la diferencia entre tirar a donde esta la pelota vs donde "
                     "va a estar. Ojala esto lo haga comer de una vez.",
}, open(out, "w"), indent=2)
print(f"\n Guardado en: {out}")