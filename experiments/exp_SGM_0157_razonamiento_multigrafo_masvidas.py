#!/usr/bin/env python3
"""exp_SGM_0157 — RAZONAMIENTO SOBRE EL GRAFO + VARIOS GRAFOS EN EL MISMO CRAFTER.

MISION (Luciano 2026-08-11): (1) el sistema crea su propia experiencia interna/historia y
razona sobre ella (planificacion simbolica sobre el conocimiento aprendido); (2) varios
grafos en el mismo Crafter que se cruzan: aprenden entre ellos (explicito) y se comunican.

Este experimento tiene 2 GRAFOS (A y B) alternando el control del MISMO cuerpo en el mismo
mundo de Crafter. Cada grafo:
- registra su HISTORIA INTERNA (buffer episodico de lo que hace y que resulta),
- cuando tiene una META (p.ej. sobrevivir/comida), RAZONA sobre su historia
  (razonar_meta) para componer el plan, en vez de solo reaccionar,
- COMPARTE conocimiento con el otro (comunicacion explicita: si A aprende que 'accion X
  produce recurso R', se lo dicta a B, que incorpora la conexion a su grafo).

HIPOTESIS: con razonamiento + comunicacion explicita, el conocimiento FLUYE entre grafos
y el conjunto subsiste mas eficientemente: si un grafo descubre como craftear, el otro lo
adopta (vicario+explicito) sin tener que re-descubrirlo.

Se mide: logros del conjunto, conexiones compartidas, velocidad de subsistencia.
"""
import sys, os, random, json
sys.path.insert(0, os.path.expanduser("~/vaults/vega-vault/NOUS/DSCN-G/EXPERIMENTS/SGM"))
import importlib, sgm_core; importlib.reload(sgm_core)
from sgm_core import SGMAgent
import crafter
import numpy as np

D = 128; N_NODES = 64
MOV = {1,2,3,4}
DO = 5
MOVE_DIR = {1: (-1,0), 2: (1,0), 3: (0,-1), 4: (0,1)}
TODAS = list(range(17))
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


def run(seed, n_lives=8):
    agA = SGMAgent(random.Random(seed),D,n_nodes=N_NODES,gamma=0.01)
    agB = SGMAgent(random.Random(seed+1),D,n_nodes=N_NODES,gamma=0.01)
    for a in (agA, agB):
        a.set_edges({i:random.sample(range(N_NODES),min(5,N_NODES-1)) for i in range(N_NODES)})
        a.instinto_alimentacion = DO
    env=crafter.Env(); env.reset()
    total_pasos=0; logros_totales=set(); compartidas=0
    resumen=[]
    for vida in range(n_lives):
        env.reset(); agA.reset_episodio(); agB.reset_episodio()
        obs,r,t,info=env.step(0)
        prev_pos=np.array(info['player_pos'],dtype=int); facing=(0,1)
        inv_log=inventario_de(info)
        # alternar que grafo controla cada paso (se cruzan en el mismo cuerpo)
        agente_activo = agA
        pasos_control = {0:0, 1:0}
        for step in range(2000):
            sem=info['semantic']; inv=info['inventory']
            px,py=int(info['player_pos'][0]),int(info['player_pos'][1])
            sv=[float(v) for v in sem.flatten().tolist()[::64]]+[inv['health']/10.0,
                inv['food']/10.0,inv['wood'],inv['stone'],inv['iron']]
            hambre=max(0.0,1.0-inv['food']/10.0)
            # configurar el grafo activo
            ag = agA if step%2==0 else agB
            ag._hambre_real=min(1.0,hambre); ag._amenaza=0.0
            ag._posicion_actual=(px,py); ag._algo_enfrente=0
            ag._config_grad={"activo":False,"fuerza":0.0}
            ag._config_curio={"activo":True,"fuerza":0.4}
            ag._inc_dirs={a:inc_dir(ag.modelo_mundo,a) for a in MOV}
            ag._hay_gradiente=False
            # RAZONAMIENTO: si el grafo activo tiene hambre y ESTA COMIDA en su historia,
            # razonar la meta 'comida' y ejecutar la accion recomendada (no solo reaccion)
            accion_razonada = None
            if hambre > 0.4:
                acc_raz, plan = ag.razonar_meta('food')
                if acc_raz is not None:
                    accion_razonada = acc_raz
            a = ag.step(sv, TODAS) if accion_razonada is None else accion_razonada
            obs,r,t,info=env.step(a)
            cur_pos=np.array(info['player_pos'],dtype=int)
            if a in MOV:
                delta=tuple((cur_pos-prev_pos).tolist()); facing=delta if delta!=(0,0) else MOVE_DIR[a]
            prev_pos=cur_pos
            nuevo_inv=inventario_de(info)
            ag._resultado_mundo_prev=inv_log; ag._resultado_mundo_act=nuevo_inv
            ag._aprender_resultado_mundo(a)
            # registrar HISTORIA INTERNA del grafo activo (experiencia subjetiva)
            ag._registrar_historia(step, a, nuevo_inv, "cuerpo_compartido")
            inv_log=nuevo_inv
            # COMUNICACION EXPLICITA: si el grafo activo aprendio wood_pickaxe, compartirlo
            # (el conocimiento fluye de un grafo al otro; se cuenta la transferencia)
            if 'wood_pickaxe' in nuevo_inv:
                otro = agB if ag is agA else agA
                if ag.compartir_conocimiento(otro, 'wood_pickaxe'):
                    compartidas += 1
            ag.actualizar_homeostasis(inv['food'],inv['health'])
            pain=abs(r) if r<0 else 0.0
            ag.reward(max(0.0,r),pain)
            for nm,c in info['achievements'].items():
                if c>0: logros_totales.add(nm)
            total_pasos+=1
            pasos_control[0 if ag is agA else 1]+=1
            if t: break
        resumen.append({"vida":vida,"pasos":step+1,"logros":len(logros_totales),
                        "conn_A":len(agA.conn_type),"conn_B":len(agB.conn_type),
                        "historia_A":len(agA.historia),"historia_B":len(agB.historia)})
        print(f"  vida {vida}: {step+1}p logros={len(logros_totales)} connA={len(agA.conn_type)} "
              f"connB={len(agB.conn_type)} histA={len(agA.historia)} histB={len(agB.historia)}")
    # conteo real de compartidas (las conexiones que B obtuvo por sharing):
    conn_share = sum(1 for (i,j) in agA.consolidadas if (i,j) in agB.conn_type)
    return resumen, sorted(logros_totales), total_pasos, conn_share


print("="*70)
print(" exp_SGM_0157 — RAZONAMIENTO + 2 GRAFOS EN MISMO CRAFTER, MAS VIDAS Y SEEDS (cruce real)")
print("="*70)
SEEDS = [42, 7, 2024]
TODAS_SEEDS = []
for seed in SEEDS:
    res, logros, pasos, share = run(seed, n_lives=12)
    TODAS_SEEDS.append({"seed": seed, "vidas": res, "logros": logros,
                        "pasos": pasos, "conexiones_compartidas": share})
    print(f"\n  seed {seed}: {pasos} pasos, logros={logros}, conexiones compartidas={share}")

out=os.path.expanduser("~/vaults/vega-vault/NOUS/DSCN-G/EXPERIMENTS/SGM/"
                       "results/results_exp_SGM_0157_razonamiento_multigrafo.json")
json.dump({
  "experiment_id":"exp_SGM_0157","experiment_name":"razonamiento_grafo_multigrafo_cruce_3seeds",
  "phase":"Fase 8 - razonamiento sobre el grafo + 2 grafos en el mismo Crafter (3 seeds, 12 vidas)",
  "date":"2026-08-14",
  "mision":"Capturar el CRUCE REAL entre grafos: con mas vidas y seeds, que algun grafo logre craftear "
           "y la comunicacion explicita transfiera ese conocimiento al otro (conexiones_compartidas>0).",
  "config":{"D":D,"N_NODES":N_NODES,"n_lives":12,"seeds":SEEDS,"grafos":2,"control":\
           "alternado (A par, B impar) sobre el mismo cuerpo/mundo"},
  "result":{"seeds":TODAS_SEEDS},
  "script":"experiments/exp_SGM_0157_razonamiento_multigrafo.py",
  "results_file":"results/results_exp_SGM_0157_razonamiento_multigrafo.json",
  "variant_of":"exp_SGM_0155",
  "lit_refs":["experiencia interna/historia (Luciano)", "planificacion simbolica",
              "comunicacion explicita entre agentes (multiagente)"],
  "notes":"Razonamiento sobre el grafo (historia interna -> plan) + 2 grafos que alternan el mismo "
           "cuerpo en Crafter y se comunican conocimiento explicitamente. Busca que el conocimiento "
           "fluya entre grafos y la subsistencia colectiva sea mas eficiente.",
  "notes_criollo":"Dos cerebros (A y B) compartiendo el mismo cuerpo por turnos en el mismo mundo, "
                   "cada uno con su historia interna. Cuando uno aprende algo (hacer un pico) se lo "
                   "cuenta al otro. Asi el conocimiento fluye entre ellos y no tienen que re-descubrir "
                   "todo cada uno. Es el germen de la emergencia colectiva.",
},open(out,"w"),indent=2)
print(f"\n Guardado en: {out}")