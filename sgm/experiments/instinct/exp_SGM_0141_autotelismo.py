#!/usr/bin/env python3
"""exp_SGM_0141 — AUTOTELISMO PURO (opcion A, Luciano): el agente "solo hace".

DECISION: quitar la capa de fin/instituto dirigido. El agente NO persigue hambre/
amenaza: solo explora por CURIOSIDAD (prediction error del decoder) + DRIVE anti-noop
+ DUDA (sale de atractores). El aprendizaje emerge: cuando por azar descubre que un acto
restaura (comer planta +4 food), la consolidacion (Hebb en actualizar_homeostasis) conecta
ese acto<=>nodo0, y en VIUDAS POSTERIORES (grafo persistente) el agente repite antes.

EL DESCUBRIMIENTO DE LA SAGA ANTERIOR: "comer vaca" en Crafter NO come de una vez —
la vaca tiene health 3, cada do la golpea 1, y food+6 SOLO cuando muere (3 hits a la MISMA
vaca, que se mueve). Por eso comio_efectivo=0 en toda la saga (0140 incluido): no era el
sustrato, era un malentendido de la mecanica. La PLANTA (value 18) come de UNA vez (+4).
En A, el agente podria tropezar con la planta y comer efectivo.

HIPOTESIS falsable: un agente "que solo hace", con curiosidad+drive+duda y grafo persistente
a traves de varias vidas, DESCUBRE por exploracion que comer (do sobre planta) restaura, y en
vidas posteriores ejecuta 'do' sobre comida antes de morir (aprendizaje entre vidas, medido
como comio_efectivo creciente y/o muerte mas tardia). SI FALSA: deambula sin descubrir comida
(muere de hambre), o se clava en atractores pese al drive+duda.

Se corren V vidas del MISMO agente en el mismo mundo; entre vidas reset_episodio (conserva
omega/conn_type/place_cells). Se mide: comida_efectivo por vida, pasos, tiles, muerte.
"""
import sys, os, random, json, hashlib
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
import importlib, sgm_core; importlib.reload(sgm_core)
from sgm.core.sgm_core import SGMAgent
import crafter
import numpy as np

D = 128; N_NODES = 64
ACC = {0:"noop",1:"mv_l",2:"mv_r",3:"mv_u",4:"mv_d",5:"do",6:"sleep",
       7:"p_stone",8:"p_table",9:"p_furnace",10:"p_plant",11:"mk_w_pick",
       12:"mk_s_pick",13:"mk_i_pick",14:"mk_w_sword",15:"mk_s_sword",
       16:"mk_i_sword"}
MOV = {1,2,3,4}
PLANTA = 18; COW = 14; COMIDA = {14, 18}
DO = 5
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


def correr_vida(ag, env, max_p=1200, vida_i=0):
    """Corre UNA vida del agente en el ENV (creado por el llamador). Autotelismo puro:
    sin instintos dirigidos (hambre/amenaza en 0), solo curiosidad+drive+duda."""
    obs, r, t, info = env.step(0)
    log = []; tiles = set(); comio_ef = comio_vac = mov = 0
    prev_pos = np.array(info["player_pos"], dtype=int); facing = (0, 1)
    prev_hp = 9.0
    for step in range(max_p):
        # --- AUTOTELISMO: sin necesidad dirigida, todo en 0 ---
        ag._hambre_real = 0.0
        ag._amenaza = 0.0
        ag._algo_enfrente = 0
        ag._target_dir = (0, 0); ag._target_dist = 0
        ag._fuerza_instinto_eat_override = 0.0
        # solo el drive anti-noop y el PPR base fuerzan a "hacer"
        ag._config_grad = {"activo": False, "fuerza": 0.0}
        sem = info["semantic"]; inv = info["inventory"]
        px, py = int(info["player_pos"][0]), int(info["player_pos"][1])
        hp = float(inv["health"])
        sf = sem.flatten().tolist()
        sv = _sv(sem, inv, info)
        ex, ey = px + facing[0], py + facing[1]
        enfrente = 0
        if 0 <= ex < 64 and 0 <= ey < 64:
            v = sem[ey, ex]
            if v in COMIDA:
                enfrente = 1
        # place cell (mapa emergente, se conserva entre vidas)
        clave = obs_clave((px // 4, py // 4), enfrente)
        ag._registrar_place_cell(clave)
        # curiosidad dirigida: mover hacia lo que el modelo predice PEOR
        ag._inc_dirs = {a: inc_dir(ag.modelo_mundo, a) for a in MOV}
        ag._config_curio = {"activo": True, "fuerza": 0.4}
        ag._hay_gradiente = False
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
        if t:
            break
    return {"vida": vida_i, "pasos": step + 1, "tiles": len(tiles),
            "comio_efectivo": comio_ef, "comio_vacio": comio_vac, "mov": mov,
            "muerte": ("natural" if t else "limite"), "food_fin": float(inv["food"]),
            "n_place": len(ag.place_cells), "consol": len(ag.consolidadas)}


def _sv(sem, inv, info):
    sf = sem.flatten().tolist()
    return [float(v) for v in sf[::64]] + [float(inv["health"]) / 10.0,
            float(inv["food"]) / 10.0, float(inv["wood"]), float(inv["stone"]),
            float(inv["iron"])]


print("=" * 70)
print(" exp_SGM_0141 — AUTOTELISMO PURO (opcion A): el agente 'solo hace'")
print("=" * 70)
NV = 5  # vidas
SEED = 42
ag = SGMAgent(random.Random(SEED), D, n_nodes=N_NODES, gamma=0.01)
ag.set_edges({i: random.sample(range(N_NODES), min(5, N_NODES - 1))
              for i in range(N_NODES)})
ag.instinto_alimentacion = DO  # adaptador
env = crafter.Env()
resumen_vidas = []
for v in range(NV):
    env.reset()
    ag.reset_episodio()
    res = correr_vida(ag, env, max_p=1200, vida_i=v)
    resumen_vidas.append(res)
    print(f" vida {v}: {res['pasos']}p {res['tiles']}tiles comio_ef={res['comio_efectivo']} "
          f"comio_vac={res['comio_vacio']} mov={res['mov']} place={res['n_place']} "
          f"consol={res['consol']} muerte={res['muerte']} food_fin={res['food_fin']}")

out = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), ""
                         "results/results_exp_SGM_0141_autotelismo.json")
os.makedirs(os.path.dirname(out), exist_ok=True)
json.dump({
    "experiment_id": "exp_SGM_0141",
    "experiment_name": "autotelismo_puro_solo_hacer",
    "phase": "Fase 8 - autotelismo puro (opcion A): el agente solo hace, aprende en vidas",
    "date": "2026-08-11",
    "hypothesis": "El agente sin intintos dirigidos (curiosidad+drive+duda), con grafo "
                  "persistente a traves de varias vidas, descubre por exploracion que comer "
                  "planta restaura (comio_efectivo>0) y en vidas posteriores repite antes "
                  "(aprendizaje entre vidas). Si come, desbloquea el ciclo.",
    "config": {"D": D, "N_NODES": N_NODES, "nvidas": NV, "seed": SEED, "max_pasos": 1200,
               "instintos_dirigidos": "DESACTIVADOS (autotelismo puro)",
               "curiosidad": "activa", "drive_noop": "activo", "duda": "activa"},
    "result": {"vidas": resumen_vidas},
    "script": "experiments/exp_SGM_0141_autotelismo.py",
    "results_file": "results/results_exp_SGM_0141_autotelismo.json",
    "variant_of": "exp_SGM_0140",
    "lit_refs": ["Panksepp 1998 (SEEKING autotelico)", "Oudeyer & Kaplan 2007 (IAC)",
                 "Schmidhuber 1991 (curiosidad por prediccion)"],
    "notes": "Opcion A de Luciano: quitar la capa de fin. El agente no persigue hambre; explora "
             "por curiosidad+drive+duda. Hallazgo de la saga: comer cow requiere 3 golpes a la "
             "misma vaca (que se mueve); la planta come de una vez. Aqui se deja que el agente "
             "descubra el comer planta solo. Vidas en gredo persistente (aprendizaje entre vidas).",
    "notes_criollo": "Le sacamos la 'mision' al bicho y lo dejamos libre: solo que haga, explore, "
                     "se aburra, y de las vueltas que le salgan. La idea es que se tropiece con la "
                     "comida por curiosidad, aprenda que sirve, y en la proxima vida ya la busque "
                     "solito. Es el aprendizaje emergente de verdad, sin que nadie le diga que hacer.",
}, open(out, "w"), indent=2)
print(f"\n Guardado en: {out}")