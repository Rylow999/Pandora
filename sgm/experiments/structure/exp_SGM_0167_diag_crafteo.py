#!/usr/bin/env python3
"""exp_SGM_0167 — DIAGNOSTICO del crafteo (un solo grafo, instrumentado).

MISION: entender POR QUE al agente le cuesta tanto craftear (make_wood_pickaxe). Usamos un
solo grafo con la mejor config (0152: libertad + conocimiento + mundo persistente) y
LOGUEAMOS en detalle el estado de la cadena:
  - cuando junta wood (y cuanto), si hay mesa cerca, cuando INTENTA make/place,
    y cuando falla (sin mesa / sin wood / el agente no eligio).

HIPOTESIS a testear por diag nostico (no adivinar):
  a) El agente nunca junta wood >= 2 (no encuentra arboles).
  b) Junta wood pero nunca coloca la mesa (no dispara place_table).
  c) Coloca mesa pero nunca dispara el make (el prefiere_comp no gatilla).
  d) El make se dispara pero falla (mesa no esta cerca / no tiene el wood en ese paso).
  e) El gate del random (0.4) impide que craftee aun con las condiciones.

Se mide la frecuencia de cada condicion para ver el cuello de botella real.
STDOUT legible con contadores de cada etapa de la cadena.
"""
import sys, os, random, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
import importlib, sgm_core; importlib.reload(sgm_core)
from sgm.core.sgm_core import SGMAgent
import crafter
import numpy as np

D = 128; N_NODES = 64
MOV = {1,2,3,4}
DO = 5
MOVE_DIR = {1: (-1,0), 2: (1,0), 3: (0,-1), 4: (0,1)}
TODAS = list(range(17))
COMP_ACCIONES = {11:"make_wood_pickaxe",12:"make_stone_pickaxe",13:"make_iron_pickaxe",
                 14:"make_wood_sword",15:"make_stone_sword",16:"make_iron_sword"}
COMP_RECURSOS = {11:["wood"],12:["wood","stone"],13:["wood","coal","iron"],
                 14:["wood"],15:["wood","stone"],16:["wood","coal","iron"]}


def inventario_de(info):
    inv=info['inventory']
    return {k:int(v) for k,v in inv.items() if v>0}


def inc_dir(m,a):
    if not m: return 1.0
    t,nw=0,0
    for (e,ac),tr in m.items():
        if ac==a:
            t+=sum(tr.values())
            for sq,c in tr.items():
                if c<=1: nw+=1
    return nw/max(1,t)


def _sv(info):
    inv=info['inventory']
    sem=info['semantic']
    return [float(v) for v in sem.flatten().tolist()[::64]]+[inv['health']/10.0,
            inv['food']/10.0,inv['wood'],inv['stone'],inv['iron']]


def run(seed, n_lives=8):
    ag=SGMAgent(random.Random(seed),D,n_nodes=N_NODES,gamma=0.01)
    ag.set_edges({i:random.sample(range(N_NODES),min(5,N_NODES-1)) for i in range(N_NODES)})
    ag.instinto_alimentacion=DO
    env=crafter.Env(); env.reset()
    total=0; logros=set()
    # contadores del diagnóstico de la cadena de crafteo
    diag = {"steps_con_wood_ge1":0, "steps_con_wood_ge2":0, "steps_mesa_cerca":0,
            "intentos_place_table":0, "intentos_make":0,
            "make_cond_w_fail_mesa":0, "make_cond_w_fail_wood":0, "make_cond_ok":0,
            "make_ejecutado":0, "make_logrado":0, "place_ejecutado":0, "place_logrado":0,
            "gate_bloqueo_make":0, "gate_bloqueo_place":0}
    for vida in range(n_lives):
        env.reset(); ag.reset_episodio()
        obs,r,t,info=env.step(0)
        prev_pos=np.array(info['player_pos'],dtype=int); facing=(0,1)
        inv_log=inventario_de(info)
        for step in range(2000):
            sem=info['semantic']; inv=info['inventory']
            px,py=int(info['player_pos'][0]),int(info['player_pos'][1])
            sv=_sv(info); eq=ag.cuantizar_estado(sv)
            hambre=max(0.0,1.0-inv['food']/10.0)
            ag._hambre_real=min(1.0,hambre); ag._amenaza=0.0
            ag._posicion_actual=(px,py); ag._algo_enfrente=0
            ag._config_grad={"activo":False,"fuerza":0.0}
            ag._config_curio={"activo":True,"fuerza":0.4}
            ag._inc_dirs={a:inc_dir(ag.modelo_mundo,a) for a in MOV}
            ag._hay_gradiente=False
            # ---- DIAGNOSTICO de la cadena ----
            wood = inv.get('wood',0)
            if wood>=1: diag["steps_con_wood_ge1"]+=1
            if wood>=2: diag["steps_con_wood_ge2"]+=1
            try:
                mat_near,_=env._world.nearby((px,py),1); hay_mesa='table' in mat_near
            except Exception:
                hay_mesa=False
            if hay_mesa: diag["steps_mesa_cerca"]+=1
            # prefiere_comp (la logica del 0152, la que decide craftear)
            prefiere_comp=None; razon_comp=None
            for acc,recs in COMP_RECURSOS.items():
                if all(inv.get(r,0)>0 for r in recs):
                    if hay_mesa:
                        prefiere_comp=acc; razon_comp="make_posible"   # condicion completa
                        diag["make_cond_ok"]+=1
                    elif wood>=2:
                        prefiere_comp=8; razon_comp="place_para_despues_make"  # precond mesa
                    break
            if wood>=1 and not hay_mesa and prefiere_comp is None and all(inv.get(r,0)>0 for r in COMP_RECURSOS[11]):
                diag["make_cond_w_fail_mesa"]+=1  # tiene wood, podria make, pero SIN mesa
            if prefiere_comp is None and wood<2 and (any(inv.get(r,0)>0 for r in ["wood","stone"])==False):
                pass
            # decidir accion: el agente elige, y el prefiere_comp interfiere a veces (logica 0152)
            a = ag.step(sv, TODAS)
            if prefiere_comp is not None and a not in COMP_ACCIONES and a!=8:
                if random.random()<0.4:
                    a=prefiere_comp  # el gate del 0152
                else:
                    # el gate BLOQUEO el crafteo
                    if prefiere_comp==8: diag["gate_bloqueo_place"]+=1
                    else: diag["gate_bloqueo_make"]+=1
            obs,r,t,info=env.step(a)
            cur_pos=np.array(info['player_pos'],dtype=int)
            if a in MOV:
                delta=tuple((cur_pos-prev_pos).tolist()); facing=delta if delta!=(0,0) else MOVE_DIR[a]
            prev_pos=cur_pos
            nuevo_inv=inventario_de(info)
            ag._resultado_mundo_prev=inv_log; ag._resultado_mundo_act=nuevo_inv
            ag._aprender_resultado_mundo(a)
            ag._registrar_historia(step, a, nuevo_inv, "cuerpo")
            ag._codificar_episodio(eq, a, nuevo_inv, "cuerpo")
            inv_log=nuevo_inv
            # registrar intentos/ejecuciones
            if a in COMP_ACCIONES:
                diag["intentos_make"]+=1
                tool=COMP_ACCIONES[a].replace('make_','')
                if tool in nuevo_inv:
                    diag["make_logrado"]+=1; logros.add(COMP_ACCIONES[a])
                else:
                    diag["make_ejecutado"]+=1
            if a==8:
                diag["intentos_place_table"]+=1
                if info['achievements'].get('place_table',0)>0:
                    diag["place_logrado"]+=1
                else:
                    diag["place_ejecutado"]+=1
            ag.actualizar_homeostasis(inv['food'],inv['health'])
            pain=abs(r) if r<0 else 0.0
            ag.reward(max(0.0,r),pain)
            ag.actualizar_modelo_mundo(eq, a, ag.cuantizar_estado(_sv(info)))
            for nm,c in info['achievements'].items():
                if c>0: logros.add(nm)
            total+=1
            if t: break
    return diag, sorted(logros), total


print("="*70)
print(" exp_SGM_0167 — DIAGNOSTICO del crafteo (un solo grafo, instrumentado)")
print("="*70)
diag, logros, total = run(42, n_lives=8)
print(f"\n  seed 42: {total} pasos, logros={logros}")
print("\n=== DIAGNOSTICO de la cadena de crafteo (contadores) ===")
for k,v in diag.items():
    print(f"  {k}: {v}")
print(f"\n  total pasos: {total}")
print("\n  CUADRO: con wood>=2 tuvo cond para comp; con mesa+wood >=2 tenia make_cond_ok;")

out=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), ""
                       "results/results_exp_SGM_0167_diag_crafteo.json")
json.dump({
  "experiment_id":"exp_SGM_0167","experiment_name":"diagnostico_crafteo_un_grafo",
  "phase":"Diagnostico - por que le cuesta craftear (cadena instrumentada)",
  "date":"2026-08-15","mision":"diagnosticar el cuello de botella real del crafteo con datos",
  "config":{"D":D,"N_NODES":N_NODES,"n_lives":8,"seed":42},
  "result":{"diag":diag,"logros":logros,"pasos":total,
            "prediagnostico":"ver contadores para ubicar el eslabon roto de la cadena"},
  "script":"experiments/exp_SGM_0167_diag_crafteo.py",
  "results_file":"results/results_exp_SGM_0167_diag_crafteo.json",
  "variant_of":"exp_SGM_0152",
  "lit_refs":["diagnostico empirico del crafteo"],
  "notes":"Instrumenta cada etapa de la cadena de crafteo (juntar wood, mesa cerca, intentar "
           "make/place, gate). El objetivo es ubicar ERROR del eslabon que impide la composicion.",
  "notes_criollo":"Le ponemos contadores en cada paso del crafteo para ver donde se corta la cadena: "
                   "si no junta madera, si no pone la mesa, si no gatilla el make, o si el make falla.",
},open(out,"w"),indent=2, default=str)
print(f"\n Guardado en: {out}")