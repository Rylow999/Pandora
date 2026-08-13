#!/usr/bin/env python3
"""exp_SGM_0137 — ACOPLE FINO CORRECTO: facing REAL derivado del engine.

FIX CLINICO (verificado): los errores de 0120-0136 vinieron de PRE-DIGESTAR el estado
del entorno a mano (mapeo de acciones, mapeo de objetos 13/17 vs 14/18, facing asumido).
La leccion de la literatura RL (Crafter paper, Hafner ICLR 2022): los baselines reciben
la imagen cruda y aprenden el acople percepcion-accion, no lo pre-calculan.

AQUI: el facing se deriva del MOVIMIENTO REAL del player (diferencia de player_pos entre
pasos), que verifique que coincide con player.facing 4/4. Nada de asumir facing manual.
Ademas, 'do' solo se empuja cuando hay un objetivo CONFIRMADO en pos+facing real (la
celda exacta que usara el engine). Esto elimina los 'do' vacios (93x en 0136).

HIPOTESIS: con el facing real + 'do' solo ante objetivo confirmado enfrente, el agente
por fin come efectivo (comio_efectivo>0) al tocar una cow/plant real. Cierra el acople
cuerpo-mundo fino que faltaba.

LITERATURA: Crafter paper (Hafner ICLR 2022) - los RL aprenden acople percepcion-accion,
no lo hardcodean. Leccion: derivar del engine, no asumir.
"""
import sys, os, random, json
from collections import Counter
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
COMIDA = {14, 18}   # cow, plant (mapao CORRECTO)
ENEMIGO = {15, 16}  # zombie, skeleton
COMER = 5           # 'do'
UMBRAL_EAT = 2.0
MOVE_DIR = {1: (-1, 0), 2: (1, 0), 3: (0, -1), 4: (0, 1)}


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


def correr(seed, max_p=600):
    ag = SGMAgent(random.Random(seed), D, n_nodes=N_NODES, gamma=0.01)
    ag.set_edges({i: random.sample(range(N_NODES), min(5, N_NODES - 1))
                  for i in range(N_NODES)})
    env = crafter.Env(); env.reset()
    obs, r, t, info = env.step(0)
    tiles = set(); comio_ef = comio_vac = ataco = mov = ciclos = 0
    food_bajo = False
    prev_pos = np.array(info["player_pos"], dtype=int)
    facing = (0, 1)  # inicial de Crafter
    prev_hp = 9.0
    for step in range(max_p):
        sem = info["semantic"]; inv = info["inventory"]
        px, py = int(info["player_pos"][0]), int(info["player_pos"][1])
        hp = float(inv["health"])
        sf = sem.flatten().tolist()
        sv = [float(v) for v in sf[::64]] + [float(inv["health"])/10.0,
              float(inv["food"])/10.0, float(inv["wood"]), float(inv["stone"]),
              float(inv["iron"])]
        # hambre/amenaza
        hambre = max(0.0, 1.0 - inv["food"] / 10.0)
        danio = max(0.0, (prev_hp - hp) / 10.0)
        g_enemigo, dist_enemigo = gradiente(sem, px, py, ENEMIGO)
        amenaza_env = max(0.0, 1.0 - (dist_enemigo - 1) / 3.0) if dist_enemigo < 999 else 0.0
        amenaza = max(danio * 1.5, amenaza_env * 0.8)
        # celda REAL enfrente (pos + facing derivado)
        ex, ey = px + facing[0], py + facing[1]
        algo_enfrente = 0
        if 0 <= ex < 64 and 0 <= ey < 64:
            v = sem[ey, ex]
            if v in COMIDA:
                algo_enfrente = 1
            elif v in ENEMIGO:
                algo_enfrente = 2
        # senales
        ag._hambre_real = min(1.0, hambre)
        ag._amenaza = min(1.0, amenaza)
        ag._algo_enfrente = algo_enfrente
        ag._gradiente_dir = g_enemigo; ag._gradiente_dist = dist_enemigo
        ag._hay_gradiente = g_enemigo != (0, 0)
        ag._inc_dirs = {a: inc_dir(ag.modelo_mundo, a) for a in MOV}
        ag._config_grad = {"activo": True, "fuerza": 0.5}
        ag._config_curio = {"activo": True, "fuerza": 0.3}
        g_comida, d_comida = gradiente(sem, px, py, COMIDA)
        if amenaza > hambre and g_enemigo != (0, 0):
            ag._target_dir = g_enemigo; ag._target_dist = max(abs(g_enemigo[0]), abs(g_enemigo[1]))
        elif hambre > 0.05 and g_comida != (0, 0):
            ag._target_dir = g_comida; ag._target_dist = d_comida
        else:
            ag._target_dir = (0, 0); ag._target_dist = 0
        # instinto comer override
        if inv["food"] < ag.umbral_hambre_food:
            conn = ag.conn_type.get((COMER, 0))
            st = conn.get("strength", 0) if conn else 0
            if not ((COMER, 0) in ag.consolidadas) and st < UMBRAL_EAT:
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
        # derivar facing REAL del engine: delta de posiciones al moverse
        cur_pos = np.array(info["player_pos"], dtype=int)
        if a in MOV:
            delta = tuple((cur_pos - prev_pos).tolist())
            # si el move fue bloqueado (pared), el facing igual cambio; usar MOVE_DIR[a]
            facing = delta if delta != (0, 0) else MOVE_DIR[a]
        prev_pos = cur_pos
        ag.actualizar_homeostasis(inv["food"], inv["health"])
        # contabilizar do (usando facing que YA se actualizo para el proximo paso)
        # NOTA: el 'do' del paso actual actuo sobre el facing anterior; contar contra algo_enfrente del inicio
        if a == COMER:
            if food_despues > food_antes:
                comio_ef += 1
            elif algo_enfrente == 2:
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
            "consol": len(ag.consolidadas)}


print("=" * 70)
print(" exp_SGM_0137 — ACOPLE FINO REAL: facing derivado del engine, do con objetivo enfrente")
print("=" * 70)
for seed in [42, 7, 99]:
    res = correr(seed, max_p=600)
    print(f" seed {seed}: {res['pasos']}p {res['tiles']}tiles "
          f"comio_efectivo={res['comio_efectivo']} comio_vacio={res['comio_vacio']} "
          f"ataco={res['ataco']} mov={res['mov']} ciclos={res['ciclos']} "
          f"consol={res['consol']} muerte={res['muerte']}")

out = os.path.expanduser("~/vaults/vega-vault/NOUS/DSCN-G/EXPERIMENTS/SGM/"
                         "results/results_exp_SGM_0137_acople_fino_real.json")
os.makedirs(os.path.dirname(out), exist_ok=True)
json.dump({
    "experiment_id": "exp_SGM_0137",
    "experiment_name": "acople_fino_facing_real",
    "phase": "Fase 8 - acople fino: facing derivado del engine (no asumido)",
    "date": "2026-08-11",
    "hypothesis": "Con el facing derivado de la diferencia real de player_pos entre pasos "
                  "(verificado coincide 4/4 con player.facing), y 'do' empujado solo cuando "
                  "hay objetivo CONFIRMADO en pos+facing, el agente por fin come efectivo "
                  "(comio_efectivo>0). Elimina los 'do' vacios por facing incorrecto (93x en 0136).",
    "config": {"D": D, "N_NODES": N_NODES, "max_pasos": 600, "seeds": [42, 7, 99],
               "FOOD": [14, 18], "ENEMIGO": [15, 16], "facing": "derivado del engine (movimiento real)"},
    "result": "ver stdout",
    "script": "experiments/exp_SGM_0137_acople_fino_real.py",
    "results_file": "results/results_exp_SGM_0137_acople_fino_real.json",
    "variant_of": "exp_SGM_0136",
    "lit_refs": ["Crafter paper (Hafner ICLR 2022): RL aprenden acople percepcion-accion, no lo pre-calculan; eat_cow es un achievement dificil"],
    "notes": "Leccion de los errores 0120-0136: pre-digestar el estado a mano (facing asumido) "
             "crea puntos de falla. Aqui el facing se deriva del engine (delta de player_pos), "
             "eliminando la variable manual erronea. 'do' solo se dispara con objetivo "
             "confirmado en pos+facing real.",
    "notes_criollo": "Aprendi la leccion: cada vez que le 'adivinaba' al bicho el estado del "
                     "mundo (mapeo de objetos, facing), metia la pata. Ahora el facing lo saco "
                     "directo del juego (mirando como se movio de verdad el player entre pasos), "
                     "y el 'do' solo se lanza cuando la comida esta confirmada al frente. "
                     "Asi el bicho deberia por fin comer de verdad.",
}, open(out, "w"), indent=2)
print(f"\n Guardado en: {out}")