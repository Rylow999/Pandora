#!/usr/bin/env python3
"""exp_SGM_0165 — MARATON del MUNDO INTERNO integrado (Fase 9 completa) + colectividad 2 grafos.

MISION: correr escala temporal (muchas vidas) con el Mundo Interno COMPLETO y 2 grafos
alternando el mismo cuerpo, para ver QUE EMERGE cuando:
1. Cada grafo tiene su vida interna (memoria episodica, imaginacion/gate, valencia,
   identidad/auto-modelo).
2. Se cruzan via APRENDIZAJE VICARIO + MODELO DEL OTRO (Pieza 5): cuando un grafo logra
   algo, el otro lo OBSERVA y refuerza su red (Bandura) y forma una creencia sobre el otro
   (ToM) - ya no es dictado explicito (0156) sino inferencia por observacion.

HIPOTESIS: con el Mundo Interno completo + la colectividad (aprendizaje vicario entre
grafos), la SUBSISTENCIA COLECTIVA emerge mejor que con un solo agente: si un grafo
aprende a sobrevivir/craftear, el otro lo adopta por observacion sin re-descubrir.

Se mide: logros del conjunto, paso hasta comer/craftear, n observaciones vicarias,
modelo del otro, y narrativa social/identidad de ambos grafos.
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
# acciones que si se ven producir un logro, son observables por el otro
LOGROS_OBSERVABLES = {'wood_pickaxe': 11, 'wood': 3, 'stone': 7, 'food': 5}


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


def run(seed, n_lives=20):
    agA=SGMAgent(random.Random(seed),D,n_nodes=N_NODES,gamma=0.01)
    agB=SGMAgent(random.Random(seed+1),D,n_nodes=N_NODES,gamma=0.01)
    for a in (agA, agB):
        a.set_edges({i:random.sample(range(N_NODES),min(5,N_NODES-1)) for i in range(N_NODES)})
        a.instinto_alimentacion=DO
    env=crafter.Env(); env.reset()
    total=0; logros=set(); n_vicario=0; paso_eat=None; paso_make=None
    resumen=[]
    for vida in range(n_lives):
        env.reset(); agA.reset_episodio(); agB.reset_episodio()
        obs,r,t,info=env.step(0)
        prev_pos=np.array(info['player_pos'],dtype=int); facing=(0,1)
        inv_log=inventario_de(info)
        for step in range(2000):
            sem=info['semantic']; inv=info['inventory']
            px,py=int(info['player_pos'][0]),int(info['player_pos'][1])
            sv=_sv(info)
            eq=agA.cuantizar_estado(sv)
            hambre=max(0.0,1.0-inv['food']/10.0)
            # alternar grafo activo por turno
            ag = agA if step%2==0 else agB
            otro = agB if ag is agA else agA
            ag._hambre_real=min(1.0,hambre); ag._amenaza=0.0
            ag._posicion_actual=(px,py); ag._algo_enfrente=0
            ag._config_grad={"activo":False,"fuerza":0.0}
            ag._config_curio={"activo":True,"fuerza":0.4}
            ag._inc_dirs={a:inc_dir(ag.modelo_mundo,a) for a in MOV}
            ag._hay_gradiente=False
            # MUNDO INTERNO para decidir: usar la meta homeostatica (comer) si hambre,
            # o la preferencia (valencia) si cubierta - con gate de confianza.
            accion_imag=None
            if hambre>0.4:
                meta = ag.elegir_meta(hambre, ['food'], ['food','wood','wood_pickaxe'])
                acc_raz,_ = ag.razonar_meta(meta)
                if acc_raz is not None:
                    _sig,conf,bonus = ag.predecir_recompensa(acc_raz, eq, metas_priorizadas=[meta])
                    if (conf>0 or bonus>0) and ag.decidir_explotar(eq, acc_raz):
                        accion_imag = acc_raz
            a = ag.step(sv, TODAS) if accion_imag is None else accion_imag
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
            # valencia por recursos que subieron
            for rec,cant in nuevo_inv.items():
                if cant > inv_log.get(rec,0):
                    ag.actualizar_valencia(rec, 1.0)
            inv_log=nuevo_inv
            # APRENDIZAJE VICARIO + MODELO DEL OTRO: si el grafo activo obtuvo un recurso
            # observable, el OTRO lo registra (Bandura+ToM) SIN dictado explicito.
            for rec, acc_base in LOGROS_OBSERVABLES.items():
                if rec in nuevo_inv and (rec not in inv_log):
                    otro.observar_otro(ag, acc_base, rec)
                    n_vicario += 1
            # hitos
            if 'wood_pickaxe' in nuevo_inv and paso_make is None: paso_make=total
            if info['achievements'].get('eat_cow',0)>0 and paso_eat is None: paso_eat=total
            ag.actualizar_homeostasis(inv['food'],inv['health'])
            pain=abs(r) if r<0 else 0.0
            ag.reward(max(0.0,r),pain)
            ag.actualizar_modelo_mundo(eq, a, ag.cuantizar_estado(_sv(info)))
            for nm,c in info['achievements'].items():
                if c>0: logros.add(nm)
            total+=1
            if t: break
        resumen.append({"vida":vida,"pasos":step+1,"logros":len(logros),
                        "vicario":n_vicario,"modelo_B":dict(agB.modelo_del_otro)})
        print(f"  vida {vida}: {step+1}p logros={len(logros)} vicario={n_vicario} "
              f"modeloB={sorted(agB.modelo_del_otro)}")
    return resumen, sorted(logros), total, paso_make, paso_eat, n_vicario


print("="*70)
print(" exp_SGM_0165 — MARATON MUNDO INTERNO COMPLETO + colectividad 2 grafos (escala temporal)")
print("="*70)
res, logros, pasos, pm, pe, nv = run(42, n_lives=20)
print(f"\n  seed 42: {pasos} pasos, logros={logros}, paso_make={pm}, paso_eat={pe}, vicario={nv}")

out=os.path.expanduser("~/vaults/vega-vault/NOUS/DSCN-G/EXPERIMENTS/SGM/"
                       "results/results_exp_SGM_0165_maraton_mundo_interno_colectivo.json")
json.dump({
  "experiment_id":"exp_SGM_0165","experiment_name":"maraton_mundo_interno_completo_colectividad",
  "phase":"Fase 9 - Maratun del Mundo Interno completo + 2 grafos con aprendizaje vicario",
  "date":"2026-08-14",
  "mision":"escala temporal + Mundo Interno completo (5 piezas) + colectividad (los 2 grafos se "
           "cruzan por observacion/vicario, no dictado). Ver que emerge la subsistencia colectiva.",
  "hypothesis":"con el mundo interno completo y aprendizaje vicario entre grafos, la subsistencia "
               "colectiva emerge: un grafo que aprende, el otro lo adopta por observacion.",
  "config":{"D":D,"N_NODES":N_NODES,"n_lives":20,"seed":42,"grafos":2,"control":"alternado cuerpo"},
  "result":{"vidas":res,"logros":logros,"pasos":pasos,"paso_make":pm,"paso_eat":pe,
            "observaciones_vicarias":nv},
  "script":"experiments/exp_SGM_0165_maraton_mundo_interno_colectivo.py",
  "results_file":"results/results_exp_SGM_0165_maraton_mundo_interno_colectivo.json",
  "variant_of":"exp_SGM_0159",
  "lit_refs":["Fase 9 5 piezas","aprendizaje vicario Bandura","ToM modelo del otro"],
  "notes":"Maratun: mundo interno completo + 2 grafos en el mismo cuerpo que se cruzan por "
           "observacion (vicario+modelo del otro). Busca que la colectividad supere al individuo.",
  "notes_criollo":"El bicho completo con su mundo interno, y DOS cerebros compartiendo cuerpo que "
                   "se aprenden el uno al otro mirandose. Vemos si la inteligencia colectiva "
                   "subsiste mejor que uno solo, a lo largo de muchas vidas.",
},open(out,"w"),indent=2)
print(f"\n Guardado en: {out}")