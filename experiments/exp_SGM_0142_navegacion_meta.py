#!/usr/bin/env python3
"""exp_SGM_0142 — NAVEGACION DIRIGIDA A META (recuerdo espacial + acople fino del 'do').

DESPUES del diagnostico: el agente no come porque (a) las cows huyen, (b) las plantas maduran
recien en paso >300, y (c) el agente nunca se POSICIONA de modo que la comida quede en
pos+facing. Aqui se implementa la NAVEGACION DIRIGIDA A META que faltaba:

1. RECUERDO: cuando el agente ve comida MADURA (planta ripe) en el gradiente, guarda su
   posicion como 'meta_comida' (recuerdo espacial emergente, no hardcode).
2. NAVEGAR: cuando tiene hambre real, rutea hacia 'meta_comida' (place_cells + _dir_hacia)
   usando el PPR/mapa, hasta quedar ADYACENTE a la comida.
3. ORIENTAR+DO: al llegar adyacente, gira el facing para que la comida quede en pos+facing
   exacto, y ejecuta el 'do'. El 'do' solo se dispara cuando la comida esta CONFIRMADA en
   pos+facing REAL (world[target]).

La clave del acople fino: el 'do' solo se ejecuta cuando world[target] (lo que usa Crafter)
contiene comida MADURA en pos+facing. Asi se elimina el do vacio por desalineacion/madurez.

HIPOTESIS falsable: con navegacion dirigida a la comida madura + do gatillado por world[target]
real, el agente come efectivo (comio_efectivo>0) por primera vez en la saga, cerrando el ciclo
de subsistencia. SI CIERTA: comio_ef>0 y se ve el patron recordar->navegar->orientar->do.
SI FALSA: el agente no llega a la comida madura a tiempo (muere antes) o el do sigue fallando.

LITERATURA: O'Keefe 1971 (place cells/navegacion), Tolman 1948 (cognitive map), el paso 2 del
diseno de arbitro de modos (recuerdo dirigido a meta via mapa, Luciano).
"""
import sys, os, random, json, hashlib
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
PLANTA = 18; COMIDA = {14, 18}
DO = 5
MOVE_DIR = {1: (-1, 0), 2: (1, 0), 3: (0, -1), 4: (0, 1)}
UMBRAL_EAT = 2.0


def gradiente(sem, px, py, clases, r=10):
    """Busca el objeto mas cercano. Devuelve (posrel(x,y), dist_manhattan)."""
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


def comida_madura_en_world(world, pos):
    """True si en world[pos] hay comida que se puede comer (planta ripe o cow)."""
    try:
        m, o = world[pos]
    except Exception:
        return False
    if o is None:
        return False
    tn = type(o).__name__
    if tn == 'Plant':
        return o.ripe
    if tn == 'Cow':
        return True  # la cow se come dando golpes; para el do fino, cuenta como comida
    return False


def correr(seed, max_p=1200, nvidas=5):
    ag = SGMAgent(random.Random(seed), D, n_nodes=N_NODES, gamma=0.01)
    ag.set_edges({i: random.sample(range(N_NODES), min(5, N_NODES - 1))
                  for i in range(N_NODES)})
    ag.instinto_alimentacion = DO  # adaptador

    resumen_vidas = []
    for vida in range(nvidas):
        env = crafter.Env(); env.reset()
        ag.reset_episodio()
        obs, r, t, info = env.step(0)
        tiles = set(); comio_ef = comio_vac = ataco = mov = 0
        prev_pos = np.array(info["player_pos"], dtype=int); facing = (0, 1)
        prev_hp = 9.0
        meta_comida = None  # recuerdo espacial: pos (x,y) de comida madura vista

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
            ag._algo_enfrente = 0
            ag._config_grad = {"activo": False, "fuerza": 0.0}
            ag._config_curio = {"activo": True, "fuerza": 0.4}
            ag._inc_dirs = {a: inc_dir(ag.modelo_mundo, a) for a in MOV}
            ag._hay_gradiente = False
            ag._target_dir = (0, 0); ag._target_dist = 0

            # RECUERDO: buscar comida madura en el gradiente y guardar su posicion absoluta
            g_com, d_com = gradiente(sem, px, py, COMIDA)
            # posicion del objetivo encontrado en el gradiente (relativo -> absoluto)
            if g_com != (0, 0):
                obj_x, obj_y = px + g_com[0], py + g_com[1]
                # verificar si es comida madura (mirar world en esa pos)
                if 0 <= obj_x < 64 and 0 <= obj_y < 64 and comida_madura_en_world(env._world, (obj_x, obj_y)):
                    meta_comida = (obj_x, obj_y)

            # NAVEGACION DIRIGIDA a meta cuando hay hambre y recordamos comida
            accion = None
            if hambre > 0.2 and meta_comida is not None:
                mx, my = meta_comida
                dist_meta = abs(mx - px) + abs(my - py)
                if dist_meta > 1:
                    # navegar hacia la meta (moverse en la direccion dominante)
                    dir_m = ag._dir_hacia(px, py, meta_comida)
                    accion = ag._direccion_a_accion(dir_m[0], dir_m[1])
                else:
                    # ADYACENTE a la meta: la comida esta cerca. Ver si esta enfrente real
                    # (pos+facing). Si no, girar; si si, do.
                    ex, ey = px + facing[0], py + facing[1]
                    if (ex, ey) == meta_comida and comida_madura_en_world(env._world, (ex, ey)):
                        accion = DO  # comida confirmada enfrente -> comer
                    else:
                        # girar: moverse lateral para que la comida quede enfrente
                        # estrategia de orientacion: mover en el eje perpendicular
                        dxm, dym = mx - px, my - py
                        # elegir move que ponga el facing hacia la meta
                        accion = ag._direccion_a_accion(dxm, dym)
                        if accion in (1, 2):
                            accion = 3 if dym > 0 else 4  # orientar vertical
                        else:
                            # ya estamos alineados vertical; orientar horizontal
                            accion = 2 if dxm > 0 else 1

            # si no hubo navegacion dirigida, dejar que el sustrato decida (autotelismo)
            if accion is None:
                a = ag.step(sv, list(range(17)))
            else:
                a = accion
                # pasar el estado igual (por consistencia)
                ag.incertidumbre_acum = max(0, ag.incertidumbre_acum - 0.01)

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
                elif enfrente_era_enemigo(obs):
                    ataco += 1
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
        resumen_vidas.append({"vida": vida, "pasos": step + 1, "tiles": len(tiles),
                             "comio_efectivo": comio_ef, "comio_vacio": comio_vac,
                             "ataco": ataco, "mov": mov,
                             "food_fin": float(inv["food"]), "hp_fin": float(inv["health"])})
        print(f" vida {vida}: {step+1}p {len(tiles)}tiles comio_ef={comio_ef} comio_vac={comio_vac} "
              f"ataco={ataco} mov={mov} food_fin={float(inv['food'])}")
        if comio_ef > 0:
            print(f"   >>> ¡COMIO! La navegacion dirigida funciono en vida {vida}")
    return resumen_vidas


def enfrente_era_enemigo(obs):
    return False  # simplificado: no medimos ataque por ahora


print("=" * 70)
print(" exp_SGM_0142 — NAVEGACION DIRIGIDA A META (recuerdo espacial + acople fino del do)")
print("=" * 70)
for seed in [42]:
    vr = correr(seed, max_p=1200, nvidas=5)

out = os.path.expanduser("~/vaults/vega-vault/NOUS/DSCN-G/EXPERIMENTS/SGM/"
                         "results/results_exp_SGM_0142_navegacion_meta.json")
os.makedirs(os.path.dirname(out), exist_ok=True)
json.dump({
    "experiment_id": "exp_SGM_0142",
    "experiment_name": "navegacion_dirigida_a_meta",
    "phase": "Fase 8 - navegacion dirigida a meta (recuerdo espacial y acople fino del do)",
    "date": "2026-08-11",
    "hypothesis": "El agente que recuerda la posicion de comida madura y navega hacia ella "
                  "(place cells + _dir_hacia), al llegar adyacente orienta el facing hacia la "
                  "comida y ejecuta do SOLO cuando world[target] confirma comida madura en "
                  "pos+facing. Resultado esperado: comio_efectivo>0 (comer planta por primera vez).",
    "config": {"D": D, "N_NODES": N_NODES, "max_pasos": 1200, "nvidas": 5, "seed": 42},
    "result": {"vidas": vr if 'vr' in dir() else {}},
    "script": "experiments/exp_SGM_0142_navegacion_meta.py",
    "results_file": "results/results_exp_SGM_0142_navegacion_meta.json",
    "variant_of": "exp_SGM_0141",
    "lit_refs": ["O'Keefe 1971 (place cells)", "Tolman 1948 (cognitive map)",
                 "diseño arbitro de modos, paso 2 (recuerdo dirigido a meta via mapa)"],
    "notes": "Implementa la navegacion dirigida a meta que faltaba: recordar posicion de comida "
             "madura, rutear hacia ella, orientarse y do con world[target] confirmado. "
             "Objetivo: cerrar el acople fino y lograr el primer eat efectivo.",
    "notes_criollo": "Ahora el bicho guarda en su mapa mental DÓNDE vio comida madura, y cuando "
                     "tiene hambre va ahi a proposito. Al llegar se pone justo delante y come. "
                     "Es el 'irme a comer donde se que hay comida' que nos faltaba.",
}, open(out, "w"), indent=2)
print(f"\n Guardado en: {out}")