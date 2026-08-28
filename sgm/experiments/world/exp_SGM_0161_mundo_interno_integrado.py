#!/usr/bin/env python3
"""exp_SGM_0161 — Integra las 3 piezas del Mundo Interno en subsistencia de Crafter.
MEMORIA EPSODICA (1) + IMAGINACION/gate (2) + VALOR HEDONICO POR OBJETO (3).

El agente, al decidir con hambre, coordina TODO su mundo interno:
1. RECUERDA episodios salientes (que acciones le dieron resultados).
2. VALORA los recursos por su valencia individual (recurso_mas_valorado/meta preferida).
3. IMAGINA consecuencias con gate de confianza (imaginar -> decidir_explotar).

HIPOTESIS falsable: el agente con las 3 piezas integradas sobrevive MEJOR (comer mas,
craftear, mas logros) que sin ellas. mide paso_comienza comiendo (eat_cow si aparece),
logros acumulados, y cuanto influyo la valencia/imaginacion.

LITERATURA: mundo interno (Fase 9): memoria episodica (1), proyeccion Ha&Schmidhuber (2),
valencia individualizada Damasio (3). El agente completo con mundo interno deberia
subsistir mejor que el reactivo.
"""
import sys, os, random, json
sys.path.insert(0, os.path.expanduser("~/vaults/vega-vault/NOUS/DSCN-G/EXPERIMENTS/SGM"))
import importlib, sgm_core; importlib.reload(sgm_core)
from sgm.core.sgm_core import SGMAgent
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
    ag=SGMAgent(random.Random(seed),D,n_nodes=N_NODES,gamma=0.01)
    ag.set_edges({i:random.sample(range(N_NODES),min(5,N_NODES-1)) for i in range(N_NODES)})
    ag.instinto_alimentacion=DO
    env=crafter.Env(); env.reset()
    total_pasos=0; logros_totales=set()
    paso_eat=None; paso_make=None; n_imagino=0; n_valoro=0
    resumen=[]
    for vida in range(n_lives):
        env.reset(); ag.reset_episodio()
        obs,r,t,info=env.step(0)
        prev_pos=np.array(info['player_pos'],dtype=int); facing=(0,1)
        inv_log=inventario_de(info)
        for step in range(2000):
            sem=info['semantic']; inv=info['inventory']
            px,py=int(info['player_pos'][0]),int(info['player_pos'][1])
            sv=[float(v) for v in sem.flatten().tolist()[::64]]+[inv['health']/10.0,
                inv['food']/10.0,inv['wood'],inv['stone'],inv['iron']]
            hambre=max(0.0,1.0-inv['food']/10.0)
            ag._hambre_real=min(1.0,hambre); ag._amenaza=0.0
            ag._posicion_actual=(px,py); ag._algo_enfrente=0
            ag._config_grad={"activo":False,"fuerza":0.0}
            ag._config_curio={"activo":True,"fuerza":0.4}
            ag._inc_dirs={a:inc_dir(ag.modelo_mundo,a) for a in MOV}
            ag._hay_gradiente=False
            eq=ag.cuantizar_estado(sv)
            accion_imag=None
            if hambre>0.4:
                # 3 VPIECAS DEL MUNDO INTERNO COORDINADAS:
                # (a) VALOR HEDONICO: la meta es el recurso que MAS valora (o food si nada)
                meta_preferida = ag.recurso_mas_valorado(['food','wood','wood_pickaxe'])
                if meta_preferida is None:
                    meta_preferida = 'food'
                n_valoro += 1
                # (b) RAZONAMIENTO sobre la meta preferida (desde memoria episodica)
                acc_raz, _plan = ag.razonar_meta(meta_preferida)
                if acc_raz is not None:
                    # (c) IMAGINACION con gate de confianza
                    _sig, conf, bonus = ag.predecir_recompensa(acc_raz, eq, metas_priorizadas=[meta_preferida])
                    if (conf>0 or bonus>0) and ag.decidir_explotar(eq, acc_raz):
                        accion_imag = acc_raz
                        n_imagino += 1
            a = ag.step(sv, TODAS) if accion_imag is None else accion_imag
            obs,r,t,info=env.step(a)
            cur_pos=np.array(info['player_pos'],dtype=int)
            if a in MOV:
                delta=tuple((cur_pos-prev_pos).tolist()); facing=delta if delta!=(0,0) else MOVE_DIR[a]
            prev_pos=cur_pos
            nuevo_inv=inventario_de(info)
            ag._resultado_mundo_prev=inv_log; ag._resultado_mundo_act=nuevo_inv
            ag._aprender_resultado_mundo(a)
            # registro: historia + memoria episodica + VALENCIA por cada recurso que cambio
            ag._registrar_historia(step, a, nuevo_inv, "cuerpo")
            ag._codificar_episodio(eq, a, nuevo_inv, "cuerpo")
            # al final del paso, valorar los recursos que subieron (valencia hedónica)
            for rec, cant in nuevo_inv.items():
                if cant > inv_log.get(rec, 0):
                    ag.actualizar_valencia(rec, 1.0, dolor=abs(r) if r<0 else 0.0)
            inv_log=nuevo_inv
            # registrar hitos
            if 'wood_pickaxe' in nuevo_inv and paso_make is None:
                paso_make = total_pasos
            if info['achievements'].get('eat_cow',0)>0 and paso_eat is None:
                paso_eat = total_pasos
            ag.actualizar_homeostasis(inv['food'],inv['health'])
            pain=abs(r) if r<0 else 0.0
            ag.reward(max(0.0,r),pain)
            ag.actualizar_modelo_mundo(eq, a, ag.cuantizar_estado(_sv(info)))
            for nm,c in info['achievements'].items():
                if c>0: logros_totales.add(nm)
            total_pasos+=1
            if t: break
        resumen.append({"vida":vida,"pasos":step+1,"logros":len(logros_totales),
                        "episodios":len(ag.episodios),"valencias":dict(ag.valencia_recurso),
                        "n_imagino":n_imagino})
        print(f"  vida {vida}: {step+1}p logros={len(logros_totales)} epi={len(ag.episodios)} "
              f"val={len(ag.valencia_recurso)} imagino={n_imagino}")
    return resumen, sorted(logros_totales), total_pasos, paso_make, paso_eat, n_imagino


def _sv(info):
    inv=info['inventory']
    sem=info['semantic']
    return [float(v) for v in sem.flatten().tolist()[::64]]+[inv['health']/10.0,
            inv['food']/10.0,inv['wood'],inv['stone'],inv['iron']]


print("="*70)
print(" exp_SGM_0161 — MUNDO INTERNO INTEGRADO (memoria+imaginacion+valencia) en subsistencia")
print("="*70)
res, logros, pasos, paso_make, paso_eat, n_imagino = run(42, n_lives=8)
print(f"\n  seed 42: {pasos} pasos, logros={logros}, paso_make={paso_make}, paso_eat={paso_eat}, "
      f"n_imaginaciones={n_imagino}")

out=os.path.expanduser("~/vaults/vega-vault/NOUS/DSCN-G/EXPERIMENTS/SGM/"
                       "results/results_exp_SGM_0161_mundo_interno_integrado.json")
json.dump({
  "experiment_id":"exp_SGM_0161","experiment_name":"mundo_interno_integrado_subsistencia",
  "phase":"Fase 9 - Mundo Interno integrado (3 piezas) en subsistencia de Crafter",
  "date":"2026-08-14",
  "mision":"integrar memoria episodica + imaginacion/gate + valor hedonico, medir impacto combinado",
  "hypothesis":"el agente con las 3 piezas del mundo interno sobrevive MEJOR (come, craftea, mas logros)",
  "config":{"D":D,"N_NODES":N_NODES,"n_lives":8,"seed":42},
  "result":{"vidas":res,"logros":logros,"pasos":pasos,"paso_make":paso_make,
            "paso_eat":paso_eat,"n_imaginaciones":n_imagino},
  "script":"experiments/exp_SGM_0161_mundo_interno_integrado.py",
  "results_file":"results/results_exp_SGM_0161_mundo_interno_integrado.json",
  "variant_of":"exp_SGM_0159",
  "lit_refs":["memoria episodica","imaginacion Ha&Schmidhuber","valencia Damasio"],
  "notes":"Las 3 piezas del Mundo Interno coordinadas: valor hedonico elige la meta, razonamiento "
           "la produce desde memoria episodica, imaginacion con gate decide explotar. Ver impacto "
           "combinado en la subsistencia emergente.",
  "notes_criollo":"El bicho con TODO su mundo interno: valora que le importa (preferencia), recuerda "
                   "como lograrlo (memoria), y se anima a probar solo cuando confia (imaginacion con "
                   "gate). Vemos si asi sobrevive y come mejor que sin mundo interno.",
},open(out,"w"),indent=2)
print(f"\n Guardado en: {out}")