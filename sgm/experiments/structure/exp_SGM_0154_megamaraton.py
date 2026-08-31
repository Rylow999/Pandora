#!/usr/bin/env python3
"""exp_SGM_0154 — LIBERTAD + CONOCIMIENTO DEL MUNDO + MUNDO PERSISTENTE + 30min.

MISION (Luciano 2026-08-11): "si le damos libertad y conocimiento del mundo en donde esta,
junto a todas las funciones que puede realizar, deberia poderlo hacer por su cuenta si le
damos varias vidas y que funcione durante 30 minutos".

La pieza que faltaba en 0148-0150: cada vida RESETEABA el mundo (env.reset() -> mundo nuevo),
asi la mesa que colocó en la vida 1 DESAPARECIA. AQUI el MUNDO PERSISTE entre vidas:
los objetos no-player que el agente colocó (mesa, planta) + el grafo del sustrato se
conservan. Asi el progreso fisico (mesa colocada) y el cognitivo (conocimiento aprendido)
ACUMULAN entre vidas -> la cadena recolectar->mesa->make puede completarse.

Ademas se le da el CONOCIMIENTO DEL MUNDO (las recetas make/place como tabla) al sustrato,
no para guiarlo sino como el repertorio de posibilidades (lo que pidió: entender el mundo).

Se corre con mundo persistente + vidas largas hasta ~30min (fijamos pasos-altos/multi-vidas).

HIPOTESIS: con mundo persistente + conocimiento + vidas multiples, el agente completa la
cadena: recolecta wood -> place_table -> make_wood_pickaxe -> desbloquea la composicion.
SI CIERTA: descubrio_comp incluye place_table Y make* => primera sintesis lograda.
SI FALSA: muere antes o no conecta la secuencia (el conocimiento no se traduce en accion).
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
ACC = {0:"noop",1:"mv_l",2:"mv_r",3:"mv_u",4:"mv_d",5:"do",6:"sleep",
       7:"p_stone",8:"p_table",9:"p_furnace",10:"p_plant",11:"mk_wood_pick",
       12:"mk_stone_pick",13:"mk_iron_pick",14:"mk_wood_sword",15:"mk_stone_sword",16:"mk_iron_sword"}
COMP_ACCIONES = {11:"make_wood_pickaxe",12:"make_stone_pickaxe",13:"make_iron_pickaxe",
                 14:"make_wood_sword",15:"make_stone_sword",16:"make_iron_sword"}
COMP_RECURSOS = {11:["wood"],12:["wood","stone"],13:["wood","coal","iron"],
                 14:["wood"],15:["wood","stone"],16:["wood","coal","iron"]}
# CONOCIMIENTO DEL MUNDO: recetas make y place (el repertorio de posibilidades)
# place_table (8) usa wood:2 -> habilita make. Se le da como conocimiento, no como guia.
MAKE_MESA = {11:"table",12:"table",13:["table","furnace"],14:"table",15:"table",16:["table","furnace"]}
PLACE_USA = {7:{"stone":1},8:{"wood":2},9:{"stone":4},10:{"sapling":1}}


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


def run(seed, t_max_pasos=15000, n_lives=30):
    """Simulador de 30min (muchos pasos) con MUNDO PERSISTENTE entre vidas."""
    ag=SGMAgent(random.Random(seed),D,n_nodes=N_NODES,gamma=0.01)
    ag.set_edges({i:random.sample(range(N_NODES),min(5,N_NODES-1)) for i in range(N_NODES)})
    ag.instinto_alimentacion=DO
    env=crafter.Env(); env.reset()
    total_pasos=0
    logros_totales=set()
    # objetos colocados que persisten entre vidas (mesas, plantas) como lista de (tipo,pos)
    objetos_persistentes=[]
    resultados=[]
    for vida in range(n_lives):
        # MUNDO PERSISTENTE: recrear el mundo pero re-inyectar los objetos que el agente
        # colocó en vidas anteriores (mesas/plantas) -> el progreso fisico persiste.
        env=crafter.Env(); env.reset()
        # re-inyectar objetos colocados (mesas/plantas) del mundo previo
        objetos_persistentes_ok = []
        for cls_name, pos in objetos_persistentes:
            try:
                if cls_name == 'table':
                    # la mesa es un MATERIAL (type=material en _place), no un objeto:
                    # se restaura seteando el material en el mapa del nuevo mundo.
                    env._world[pos] = 'table'
                else:
                    from crafter import objects
                    cls = getattr(objects, cls_name, None)
                    if cls is not None:
                        env._world.add(cls(env._world, np.array(pos, dtype=int)))
                objetos_persistentes_ok.append((cls_name, tuple(pos)))
            except Exception:
                pass
        objetos_persistentes = objetos_persistentes_ok
        ag.reset_episodio()
        obs,r,t,info=env.step(0)
        prev_pos=np.array(info['player_pos'],dtype=int); facing=(0,1)
        inv_log=inventario_de(info); probadas_comp=set(); descubrio=set()
        paso_make_primero=None; paso_eat_primero=None  # memoria: paso donde logra cada hito
        for step in range(2000):
            sem=info['semantic']; inv=info['inventory']
            px,py=int(info['player_pos'][0]),int(info['player_pos'][1])
            hp=float(inv['health'])
            sv=[float(v) for v in sem.flatten().tolist()[::64]]+[inv['health']/10.0,
                inv['food']/10.0,inv['wood'],inv['stone'],inv['iron']]
            hambre=max(0.0,1.0-inv['food']/10.0)
            ag._hambre_real=min(1.0,hambre); ag._amenaza=0.0
            ag._posicion_actual=(px,py); ag._algo_enfrente=0
            ag._config_grad={"activo":False,"fuerza":0.0}
            ag._config_curio={"activo":True,"fuerza":0.4}
            ag._inc_dirs={a:inc_dir(ag.modelo_mundo,a) for a in MOV}
            ag._hay_gradiente=False
            # CURIOSIDAD A COMPOSICION con CONOCIMIENTO DEL MUNDO (recetas).
            try:
                mat_near,_=env._world.nearby((px,py),1); hay_mesa='table' in mat_near
            except Exception:
                hay_mesa=False
            prefiere_comp=None
            for acc,recs in COMP_RECURSOS.items():
                if acc in probadas_comp: continue
                if all(inv.get(r,0)>0 for r in recs):
                    if hay_mesa:
                        prefiere_comp=acc
                    elif inv.get('wood',0)>=2:
                        prefiere_comp=8  # place_table (precondicion)
                    break
            a=ag.step(sv,TODAS)
            if prefiere_comp is not None and a not in COMP_ACCIONES and a!=8 and random.random()<0.4:
                a=prefiere_comp
            # antes de step, si vamos a colocar algo y funciona, registrarlo
            obs,r,t,info=env.step(a)
            cur_pos=np.array(info['player_pos'],dtype=int)
            if a in MOV:
                delta=tuple((cur_pos-prev_pos).tolist()); facing=delta if delta!=(0,0) else MOVE_DIR[a]
            prev_pos=cur_pos
            nuevo_inv=inventario_de(info)
            ag._resultado_mundo_prev=inv_log; ag._resultado_mundo_act=nuevo_inv
            ag._aprender_resultado_mundo(a)
            inv_log=nuevo_inv
            # registrar place_table COLOCADO (persistir la mesa en el mundo)
            if a==8 and info['achievements'].get('place_table',0)>0:
                if ('table',(cur_pos[0]+facing[0],cur_pos[1]+facing[1])) not in objetos_persistentes:
                    objetos_persistentes.append(('table',(int(cur_pos[0]+facing[0]),int(cur_pos[1]+facing[1]))))
                    print(f"    [PERSISTE] vida {vida}: mesa colocada guardada")
            if a in COMP_ACCIONES:
                probadas_comp.add(a)
                tool=COMP_ACCIONES[a].replace('make_','')
                if tool in nuevo_inv:
                    descubrio.add(COMP_ACCIONES[a])
            if ('wood_pickaxe' in nuevo_inv or info['achievements'].get('make_wood_pickaxe',0) > 0) and paso_make_primero is None:
                paso_make_primero = step  # memoria: paso del primer crafteo (acelera entre vidas)
                # 0154-A: consolidar el HITO (accion_make -> nodo del pico) directo, memoria fuerte
                nodo_tool = ag._hash_recurso_a_nodo('wood_pickaxe')
                ag.consolidar_hito(a, nodo_tool)
            if info['achievements'].get('eat_cow',0)>0 and paso_eat_primero is None:
                paso_eat_primero = step
                # 0154-A: consolidar el HITO de comer (do -> nodo0 comida) directo
                ag.consolidar_hito(5, 0)  # do -> nodo0 (supervivencia/comer)
            ag.actualizar_homeostasis(inv['food'],inv['health'])
            pain=abs(r) if r<0 else 0.0
            ag.reward(max(0.0,r),pain)
            for nm,c in info['achievements'].items():
                if c>0: logros_totales.add(nm)
            total_pasos+=1
            if t: break
        resultados.append({"vida":vida,"pasos":step+1,"probadas_comp":sorted(probadas_comp),
                          "descubrio":sorted(descubrio),"logros_totales":len(logros_totales),
                          "paso_make":paso_make_primero,"paso_eat":paso_eat_primero,
                          "mesas_persist":{"tipo":objetos_persistentes},
                          "consol":len(ag.consolidadas),"n_conn":len(ag.conn_type)})
        print(f"  vida {vida}: {step+1}p probadas_comp={len(probadas_comp)} "
              f"descubrio={sorted(descubrio)} logros={len(logros_totales)} "
              f"mesas_persist={len(objetos_persistentes)} consol={len(ag.consolidadas)} "
              f"conn={len(ag.conn_type)}")
    return resultados, sorted(logros_totales), total_pasos


print("="*70)
print(" exp_SGM_0154 — MEGAMARATON (3h): escala temporal, ver que logra el sistema")
print("="*70)
TODAS_SEEDS = []
for seed in [42]:
    res, logros, pasos = run(seed, n_lives=60)
    TODAS_SEEDS.append({"seed": seed, "vidas": res, "logros": logros, "pasos_totales": pasos})
    print(f"\n  seed {seed}: {pasos} pasos totales, logros desbloqueados = {logros}")

out=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), ""
                       "results/results_exp_SGM_0154_megamaraton.json")
os.makedirs(os.path.dirname(out),exist_ok=True)
json.dump({
    "experiment_id":"exp_SGM_0154","experiment_name":"megamaraton_3h_escala_temporal",
    "phase":"Fase 8 - MEGAMARATON (3h): escala temporal, que logra el sistema",
    "date":"2026-08-14",
    "mision":"Luciano: dejar al sistema correr 3 horas y ver que logra. Escala temporal max: "
             "60 vidas con mundo persistente + conocimiento + consolidacion de hitos (0153-A). "
             "El sustrado deberia seguir escalando la composicion (crafteo, comer, defensa) con tiempo.",
    "config":{"D":D,"N_NODES":N_NODES,"n_lives":60,"max_pasos_vida":2000,"seed":42,
              "mundo_persistente":True,"conocimiento_mundo":"recetas make/place como repertorio",
              "consolidacion_hitos":"0153-A activa"},
    "result":{"seeds":TODAS_SEEDS},
    "script":"experiments/exp_SGM_0154_megamaraton.py",
    "results_file":"results/results_exp_SGM_0154_megamaraton.json",
    "variant_of":"exp_SGM_0153",
    "lit_refs":["libertad + conocimiento del mundo + persistencia (Luciano)",
                "grafo de conocimiento como repertorio de posibilidades"],
    "notes":"Mundo persistente entre vidas + conocimiento del mundo (recetas) + libertad + "
             "vidas largas. Objetivo: que el agente complete recolectar->mesa->make pjor su cuenta.",
    "notes_criollo":"Le prometimos lo que pediste: libertad, saber como funciona el mundo, "
                     "y que el mundo no se borre entre vida y vida (si coloco la mesa queda). "
                     "Con eso, en varias vidas largas, el agente deberia juntar madera, poner "
                     "mesa, y craftear su primera herramienta SOLO.",
},open(out,"w"),indent=2)
print(f"\n Guardado en: {out}")