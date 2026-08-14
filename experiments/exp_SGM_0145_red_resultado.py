#!/usr/bin/env python3
"""exp_SGM_0145 — RED ACCION->RESULTADO DEL MUNDO + autotelismo (probar todo lo disponible).

TU INTUICION (Luciano 2026-08-11): "Si el agente no sabe QUE puede lograr y QUE existe, nunca
puede lograr nada". Este experimento deja que el agente PRUEBE todas las acciones disponibles
en Crafter, y el sustrato aprende una RED GENERAL de "accion -> resultado observable" (no solo
supervivencia): al ejecutar cada accion, consolida la conexion hacia el recurso que cambio.

El adaptador provee:
- _objetos_vistos: comidas/cosas visibles.
- _resultado_mundo_prev/_act: el inventario antes/despues de cada accion (wood, stone, food, etc).
El sustrato (0145 core) consolida (accion)->recurso cuando el inventario sube.

Con esto el agente DESCUBRE estructura por prueba:
  romper arbol -> wood, beber -> sed, plantar -> (semilla), craftear -> item.
Y eventualmente: comer (food sube) consolida la cadena hacia el nodo0 (supervivencia).

HIPOTESIS falsable: con la red accion->resultado, el agente que prueba todo aprende QUÉ acciones
producen QUÉ recursos, y esa estructura (consolidadas_>0, conexiones accion->recurso>0) le permite
dirigirse: probar las acciones que producen recursos, y eventualmente comer (food sube) cuando
descubre la combinacion. SI CIERTA: consol>0 y comio_efectivo>0 en alguna vida. SI FALSA: el agente
prueba pero no retiene la estructura (consol bajo) o no conecta comida->supervivencia.

LITERATURA: Oudeyer & Kaplan (curiosidad instrumental, muestrear acciones), Gibson (affordances:
el objeto se define por lo que permite hacer), RL (exploracion de acciones + reward).
"""
import sys, os, random, json
sys.path.insert(0, os.path.expanduser("~/vaults/vega-vault/NOUS/DSCN-G/EXPERIMENTS/SGM"))
import importlib, sgm_core; importlib.reload(sgm_core)
from sgm_core import SGMAgent
import crafter
import numpy as np

D = 128; N_NODES = 64
MOV = {1, 2, 3, 4}
COMIDA = {14, 18}
DO = 5
MOVE_DIR = {1: (-1, 0), 2: (1, 0), 3: (0, -1), 4: (0, 1)}
# inventario relevante que reporta Crafter (genérico: nombres de recursos)
RECURSOS = ['wood', 'stone', 'iron', 'food', 'sapling', 'wood_pickaxe', 'stone_pickaxe',
            'iron_pickaxe', 'wood_sword', 'stone_sword', 'iron_sword']


def inventario_de(info):
    """El adaptador: extrae el inventario como dict {recurso: cantidad} (solo los >0)."""
    inv = info['inventory']
    return {k: int(inv[k]) for k in RECURSOS if inv[k] > 0}


def objetos_visibles(sem, px, py, r=12):
    res = []
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            x, y = px + dx, py + dy
            if 0 <= x < 64 and 0 <= y < 64 and sem[y, x] in COMIDA:
                res.append(("comida", x, y))
    return res[:5]


def gradiente(sem, px, py, clases, r=10):
    b, bd = (0, 0), r * r + 1
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            if dx == 0 and dy == 0:
                continue
            x, y = px + dx, py + dy
            if 0 <= x < 64 and 0 <= y < 64 and sem[y, x] in clases:
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


def correr(seed, max_p=900, nvidas=3):
    ag = SGMAgent(random.Random(seed), D, n_nodes=N_NODES, gamma=0.01)
    ag.set_edges({i: random.sample(range(N_NODES), min(5, N_NODES - 1))
                  for i in range(N_NODES)})
    ag.instinto_alimentacion = DO

    resumen = []
    for vida in range(nvidas):
        env = crafter.Env(); env.reset()
        ag.reset_episodio()
        obs, r, t, info = env.step(0)
        prev_pos = np.array(info["player_pos"], dtype=int); facing = (0, 1)
        prev_hp = 9.0
        comio_ef = comio_vac = mov = 0
        tiles = set()
        ag._resultado_mundo_prev = inventario_de(info)
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
            ag._algo_enfrente = 0
            ag._config_grad = {"activo": False, "fuerza": 0.0}
            ag._config_curio = {"activo": True, "fuerza": 0.4}
            ag._inc_dirs = {a: inc_dir(ag.modelo_mundo, a) for a in MOV}
            ag._hay_gradiente = False
            ag._objetos_vistos = objetos_visibles(sem, px, py)

            a = ag.step(sv, list(range(17)))
            accion_ejec = a
            food_antes = float(inv["food"])
            obs, r, t, info = env.step(a)
            food_despues = float(inv["food"])
            cur_pos = np.array(info["player_pos"], dtype=int)
            if a in MOV:
                delta = tuple((cur_pos - prev_pos).tolist())
                facing = delta if delta != (0, 0) else MOVE_DIR[a]
            prev_pos = cur_pos
            # ADAPTADOR: reportar el resultado del mundo (inventario nuevo) al sustrato
            ag._resultado_mundo_act = inventario_de(info)
            ag._aprender_resultado_mundo(accion_ejec)
            ag._resultado_mundo_prev = ag._resultado_mundo_act
            ag.actualizar_homeostasis(inv["food"], inv["health"])
            # medir do
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
                       "n_conn_resultado": len(ag.conn_type), "consol": len(ag.consolidadas),
                       "recursos_conocidos": len(getattr(ag, '_nodo_recursos', {})),
                       "food_fin": float(inv["food"]), "hp_fin": float(inv["health"])})
        print(f" vida {vida}: {step+1}p {len(tiles)}tiles comio_ef={comio_ef} "
              f"comio_vac={comio_vac} mov={mov} conn_res={len(ag.conn_type)} "
              f"recursos={len(getattr(ag,'_nodo_recursos',{}))} consol={len(ag.consolidadas)} "
              f"food_fin={float(inv['food'])}")
        if comio_ef > 0:
            print(f"   >>> ¡COMIO! La red accion->resultado funciono (vida {vida})")
    return resumen


print("=" * 70)
print(" exp_SGM_0145 — RED ACCION->RESULTADO DEL MUNDO + probar todo lo disponible")
print("=" * 70)
RESULTADOS = []
for seed in [42, 7]:
    r = correr(seed, max_p=900, nvidas=3)
    RESULTADOS.append({"seed": seed, "vidas": r})

out = os.path.expanduser("~/vaults/vega-vault/NOUS/DSCN-G/EXPERIMENTS/SGM/"
                         "results/results_exp_SGM_0145_red_resultado.json")
os.makedirs(os.path.dirname(out), exist_ok=True)
json.dump({
    "experiment_id": "exp_SGM_0145",
    "experiment_name": "red_accion_resultado_mundo",
    "phase": "Fase 8 - red accion->resultado del mundo + probar todo (autotelismo instrumental)",
    "date": "2026-08-11",
    "hypothesis": "El agente que prueba todas las acciones y aprende QUE recurso produce cada "
                  "una (red accion->resultado) descubre la estructura del mundo. Eso le permite "
                  "dirigirse a acciones utiles y eventualmente comer (food sube). SI: consol>0 "
                  "y comio_efectivo>0.",
    "config": {"D": D, "N_NODES": N_NODES, "max_pasos": 900, "nvidas": 3, "seeds": [42, 7],
               "aprender_resultado": True},
    "result": {"seeds": RESULTADOS},
    "script": "experiments/exp_SGM_0145_red_resultado.py",
    "results_file": "results/results_exp_SGM_0145_red_resultado.json",
    "variant_of": "exp_SGM_0144",
    "lit_refs": ["Oudeyer & Kaplan (curiosidad instrumental)", "Gibson (affordances)",
                 "RL: exploracion de acciones"],
    "notes": "Implementa la intuicion de Luciano: el agente debe conocer el espacio de acciones "
             "y QUE producen cada una para poder lograr algo. El sustrato consolida una red general "
             "accion->recurso (no solo supervivencia), asi descubre que romper->madera, etc.",
    "notes_criollo": "Le dimos al bicho la carta de QUE puede hacer: que pruebe todo (romper, "
                     "beber, plantar, craftear) y el sustrato anota cual accion produce cual "
                     "recurso. Asi aprende el mapa de posibilidades del mundo, no solo a "
                     "sobrevivir. Es como darle las llaves y que descubra cual abre cada puerta.",
}, open(out, "w"), indent=2)
print(f"\n Guardado en: {out}")