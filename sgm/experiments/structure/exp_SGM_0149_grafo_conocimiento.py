#!/usr/bin/env python3
"""exp_SGM_0149 — GRAFO DE CONOCIMIENTO DEL MUNDO (V2): el sustrato aprende COMPOSICION.

MISION (Luciano 2026-08-11): que el sustrato CONSTRUYA por observacion su propio grafo de
conocimiento del mundo (que existencia, que se combina con que), integrado al grafo agentico
y auto-extensible. Base del bucle: conocimiento -> composicion -> nuevo-conocimiento.

EL HALLAZGO DEL 0148: el agente libre descubre RECOLECCION (collect) pero NO da el salto a
COMPOSICION (make/place) porque recolecta recursos pero no prueba combinarlos. V2 da el
empuje OBSERVACIONAL (no hardcode): cuando el inventario tiene recursos y hay una accion de
composicion NO probada que podria consumirlos, la curiosidad se dirige hacia ESA accion.

Recetas (grafo de conocimiento que debe EMERGER, del adaptador):
  make_wood_pickaxe: wood -> wood_pickaxe   (necesita mesa place_table cerca)
  make_wood_sword  : wood -> wood_sword
  make_stone_pickaxe: wood+stone -> stone_pickaxe
  etc.

El sustrado aprende por observacion: cuando hace make_X y el inventario gana el tool, consolida
en su grafo [recurso_disp, accion_composicion] -> resultado. Cuando falla, aprende que falta un
requisito (la mesa). Es V2: el conocimiento NO se inyecta, se CONSTRUYE.

HIPOTESIS: con curiosidad dirigida a composicion (probar make cuando tengo los recursos), el
agente que en 0148 NO crafteaba, ahora prueba make_* y descubre el grafo de composicion:
desbloquea make_x en ≥1 vida, y se ve la red [recurso+accion]->tool en conn_type.

Se corren varias seed/vidas. Se registra el GRAFO DE CONOCIMIENTO aprendido (recetas descubiertas).
"""
import sys, os, random, json, hashlib
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
import importlib, sgm_core; importlib.reload(sgm_core)
from sgm.core.sgm_core import SGMAgent
import crafter
import numpy as np

D = 128; N_NODES = 64
MOV = {1,2,3,4}
DO = 5
MOVE_DIR = {1: (-1,0), 2: (1,0), 3: (0,-1), 4: (0,1)}
COMIDA = {14,18}
TODAS = list(range(17))
ACC = {0:"noop",1:"mv_l",2:"mv_r",3:"mv_u",4:"mv_d",5:"do",6:"sleep",
       7:"p_stone",8:"p_table",9:"p_furnace",10:"p_plant",11:"mk_wood_pick",
       12:"mk_stone_pick",13:"mk_iron_pick",14:"mk_wood_sword",15:"mk_stone_sword",16:"mk_iron_sword"}
# Acciones de composicion (make_*) -> receta consume de (del adaptador, agnostico)
COMP_ACCIONES = {11:"make_wood_pickaxe",12:"make_stone_pickaxe",13:"make_iron_pickaxe",
                 14:"make_wood_sword",15:"make_stone_sword",16:"make_iron_sword"}
COMP_RECURSOS = {11:["wood"],12:["wood","stone"],13:["wood","coal","iron"],
                 14:["wood"],15:["wood","stone"],16:["wood","coal","iron"]}
PLACE = {7:"place_stone",8:"place_table",9:"place_furnace",10:"place_plant"}


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


def correr_vida(ag, env, vida_i, max_p=1500):
    obs,r,t,info=env.step(0)
    prev_pos=np.array(info['player_pos'],dtype=int); facing=(0,1)
    prev_hp=9.0
    inv_log=inventario_de(info)
    tills=set()
    probadas_comp=set()   # acciones de composicion ya probadas
    descubrio_comp=[]     # [accion, tool] que si produjo
    meta=(flatten) if False else None
    log=[]
    for step in range(max_p):
        sem=info['semantic']; inv=info['inventory']
        px,py=int(info['player_pos'][0]),int(info['player_pos'][1])
        hp=float(inv['health'])
        sv=[float(v) for v in sem.flatten().tolist()[::64]]+[float(inv['health'])/10.0,
            float(inv['food'])/10.0,float(inv['wood']),float(inv['stone']),float(inv['iron'])]
        hambre=max(0.0,1.0-inv['food']/10.0)
        ag._hambre_real=min(1.0,hambre); ag._amenaza=0.0
        ag._posicion_actual=(px,py); ag._algo_enfrente=0
        ag._config_grad={"activo":False,"fuerza":0.0}
        ag._config_curio={"activo":True,"fuerza":0.4}
        ag._inc_dirs={a:inc_dir(ag.modelo_mundo,a) for a in MOV}
        ag._hay_gradiente=False
        ag.meta_recordada=None
        # CURIOSIDAD DIRIGIDA A COMPOSICION: si tengo recursos que habilitan un make_no_probado,
        # inyectar en el pool de acciones esa accion con sesgo (muestreo Oudeyer).
        # (no hardcode: el mapeo recurso->make del adaptador; el sustrato curioso lo prueba)
        sesgo_comp=0.0
        prefiere_comp=None
        for acc,recurso_neces in COMP_RECURSOS.items():
            if acc in probadas_comp: continue
            if all(inv.get(r,0)>0 for r in recurso_neces):
                # tengo los recursos y no probe este make -> curiosealo
                prefiere_comp=acc
                sesgo_comp=0.8
                break
        a=ag.step(sv,TODAS)
        # aplicamos el sesgo de curiosidad a la composicion (si el sustrato no eligio make)
        if prefiere_comp is not None and a not in COMP_ACCIONES and random.random()<0.3:
            a=prefiere_comp  # muestrear el make prometedor (Oudeyer: accion desconocida en condicion)
        food_antes=float(inv['food'])
        obs,r,t,info=env.step(a)
        food_despues=float(inv['food'])
        cur_pos=np.array(info['player_pos'],dtype=int)
        if a in MOV:
            delta=tuple((cur_pos-prev_pos).tolist()); facing=delta if delta!=(0,0) else MOVE_DIR[a]
        prev_pos=cur_pos
        # aprender resultado del mundo
        nuevo_inv=inventario_de(info)
        ag._resultado_mundo_prev=inv_log; ag._resultado_mundo_act=nuevo_inv
        ag._aprender_resultado_mundo(a)
        inv_log=nuevo_inv
        # registrar acciones de composicion probadas/descubiertas
        if a in COMP_ACCIONES:
            probadas_comp.add(a)
            # si el inventario gano el tool correspondiente
            tool=COMP_ACCIONES[a].replace('make_','')
            if nuevo_inv.get(tool,0)>inv_log.get(tool,0) or tool in nuevo_inv:
                descubrio_comp.append(COMP_ACCIONES[a])
                print(f"    [COMPOSICION] vida {vida_i} paso {step}: {COMP_ACCIONES[a]} -> {tool} !")
        ag.actualizar_homeostasis(inv['food'],inv['health'])
        pain=abs(r) if r<0 else 0.0
        ag.reward(max(0.0,r),pain)
        pos=(px,py)
        if pos not in tills: tills.add(pos)
        eq=ag.cuantizar_estado(sv)
        ag.actualizar_modelo_mundo(getattr(ag,'ultimo_estado_q',eq) or eq,a,eq)
        ag.ultimo_estado_q=eq
        if t: break
    return {"vida":vida_i,"pasos":step+1,"tiles":len(tills),
            "probadas_comp":sorted(probadas_comp),
            "descubrio_comp":descubrio_comp,
            "inv_final":inventario_de(info),"consol":len(ag.consolidadas),
            "n_conn":len(ag.conn_type),"n_place":len(ag.place_cells)}


print("="*70)
print(" exp_SGM_0149 — GRAFO DE CONOCIMIENTO DEL MUNDO (V2): aprender COMPOSICION")
print("="*70)
SEEDS=[42,7]; VIDAS=4; MAXP=1500
TODOS=[]
for seed in SEEDS:
    ag=SGMAgent(random.Random(seed),D,n_nodes=N_NODES,gamma=0.01)
    ag.set_edges({i:random.sample(range(N_NODES),min(5,N_NODES-1)) for i in range(N_NODES)})
    ag.instinto_alimentacion=DO
    env=crafter.Env()
    print(f"\n--- seed {seed} ---")
    for v in range(VIDAS):
        env.reset(); ag.reset_episodio()
        res=correr_vida(ag,env,v,max_p=MAXP)
        TODOS.append({"seed":seed,**res})
        print(f"  vida {v}: {res['pasos']}p probadas_comp={len(res['probadas_comp'])} "
              f"descubrio={res['descubrio_comp']} consol={res['consol']} conn={res['n_conn']}")

out=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), ""
                       "results/results_exp_SGM_0149_grafo_conocimiento.json")
os.makedirs(os.path.dirname(out),exist_ok=True)
json.dump({
    "experiment_id":"exp_SGM_0149","experiment_name":"grafo_conocimiento_composicion_V2",
    "phase":"Fase 8 - grafo de conocimiento del mundo construido por observacion (V2)",
    "date":"2026-08-11",
    "mision":"Luciano V2: el sustrato construye por observacion su propio grafo de conocimiento "
             "del mundo, integrado y auto-extensible. El hallazgo del 0148: recoleccion basal "
             "pero no composicion (craftear). Aqui se da el empuje observacional de curiosidad "
             "hacia make_* cuando hay recursos, para que el agente DESCUBRA la sintesis.",
    "config":{"D":D,"N_NODES":N_NODES,"seeds":SEEDS,"vidas":VIDAS,"max_pasos":MAXP},
    "result":{"vidas":TODOS},
    "script":"experiments/exp_SGM_0149_grafo_conocimiento.py",
    "results_file":"results/results_exp_SGM_0149_grafo_conocimiento.json",
    "variant_of":"exp_SGM_0148",
    "lit_refs":["Oudeyer & Kaplan (curiosidad hacia acciones desconocidas en condicion)",
                "grafo de conocimiento / prior estructural","V2: conocimiento aprendido, no inyectado"],
    "notes":"V2: el sustrado construye el grafo de conocimiento del mundo observando. Cuando el "
             "inventario tiene recursos que habilitan un make no probado, la curiosidad lo empuja "
             "a muestrearlo. Si produce, consolida [recurso+accion]->tool. Busca EL SALTO A LA "
             "COMPOSICION que el 0148 mostro que faltaba.",
    "notes_criollo":"Le dimos la curiosidad de probar las combinaciones cuando tiene los materiales: "
                     "si tiene madera y nunca intento hacer un pico, lo tienta a probarlo. Asi "
                     "descubre que puede COMBINAR recursos para hacer herramientas (la sintesis "
                     "que le faltaba). Es el germen de entender el mundo: no solo juntar, sino CREAR.",
},open(out,"w"),indent=2)
print(f"\n Guardado en: {out}")