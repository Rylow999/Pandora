#!/usr/bin/env python3
"""exp_SGM_0173 — COLECTIVIDAD EN MUNDOS SEPARADOS con PROPAGACION DE CONOCIMIENTO.

MISION (Luciano 2026-08-15): 2 grafos en MUNDOS SEPARADOS (cada uno su continuidad) que
COMPARTEN conocimiento. La lectura del 0165 fue: alternar 2 grafos en el mismo cuerpo
FRAGMENTABA la continuidad y evitaba el logro; sin logro no hay cruce. AQUI cada grafo
vive en su propio mundo -> conserva la continuidad para encadenar el crafteo, y cuando
UNO consolida un HITO (craftear/comer), ese conocimiento se PROPAGA al otro (sin
fragmentar a nadie).

Propagacion: A transiere a B la conexion consolidada (accion->recurso) del hito, y B
incorpora + registra en su modelo del otro (creencia ToM). Emergente, sin hardcode.

HIPOTESIS: con mundos separados + propagacion, cada grafo puede lograr MAS (continuidad
preservada) y el conocimiento se acumula en la colectividad mejor que en el mismo cuerpo.
Se mide: logros de cada mundo, y conciencia de propagacion (B adopta el hito de A).
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
# hitos observables que se propagan: (recurso_objetivo, accion_que_lo_produce)
HITOS = {'wood_pickaxe': 11, 'stone': 7}  # si A logra esto, se propaga a B


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


def correr_un_mundo(ag, seed, n_vidas, otro, propagado={}, romper_coldstart=False):
    """Corre UN graf en SU PROPIO mundo. Al final consolida hitos y propaga al otro.
    romper_coldstart=True: coloca una mesa (2 wood) y un wood extra en el inventario al
    empezar, para darle al grafo la PRIMERA experiencia de composicion (romper el cold-start
    del 0170: colocar mesa no tiene recompensa inmediata, sin primer disparo no arranca).
    Es 'periodo sensible': una condicion inicial senial, NO una regla de decision."""
    env=crafter.Env(); env.reset()
    logros=set(); paso_make=None; paso_eat=None; total=0
    for vida in range(n_vidas):
        env.reset(); ag.reset_episodio()
        obs,r,t,info=env.step(0)
        # romper cold-start: dar mesa inicial + wood (solo al grafo designado)
        if romper_coldstart:
            try:
                pw, ph = env._world.shape
                # colocar una mesa cerca del spawn para que el make sea posible desde el inicio
                dirs = [(0,1),(1,0),(0,-1),(-1,0),(1,1),(-1,1)]
                sx, sy = pix = info['player_pos'][:2]; sx, sy = int(sx), int(sy)
                for dx,dy in dirs:
                    tx,ty = sx+dx, sy+dy
                    if 0<=tx<pw and 0<=ty<ph:
                        env._world.place_table((tx,ty))
                        break
                info['inventory']['wood'] = max(info['inventory'].get('wood',0), 2)
            except Exception:
                pass
        prev_pos=np.array(info['player_pos'],dtype=int); facing=(0,1)
        inv_log=inventario_de(info)
        for step in range(2000):
            sem=info['semantic']; inv=info['inventory']
            px,py=int(info['player_pos'][0]),int(info['player_pos'][1])
            # DETECTOR UNICO DE PROXIMIDAD (0172): verificar_proximidad computa de una vez
            # _algo_enfrente (DO), _cerca_tipo (place/make) y _posicion_actual (re-encare).
            mesa_cerca=0.0; mapa_enfrente=0
            try:
                mat_near,_=env._world.nearby((px,py),1)
                if 'table' in mat_near: mesa_cerca=1.0
                ex,ey=px+1,py  # facing por defecto
                if 0<=ex<sem.shape[0] and 0<=ey<sem.shape[1]:
                    vc=sem[ex,ey]
                    if vc in (5,6): mapa_enfrente=1       # comida
                    elif vc in (3,4,11,12,13,14): mapa_enfrente=2  # enemigo
            except Exception:
                pass
            ag.verificar_proximidad(mapa_enfrente, {"mesa": bool(mesa_cerca)}, (px,py))
            sv=_sv(info); eq=ag.cuantizar_estado(sv)
            hambre=max(0.0,1.0-inv['food']/10.0)
            ag._hambre_real=min(1.0,hambre); ag._amenaza=0.0
            ag._config_grad={"activo":False,"fuerza":0.0}
            ag._config_curio={"activo":True,"fuerza":0.4}
            ag._inc_dirs={a:inc_dir(ag.modelo_mundo,a) for a in MOV}
            ag._hay_gradiente=False
            # mundo interno: gate como en 0159 (la mejor config)
            accion_imag=None
            if hambre>0.4:
                acc_raz,_ = ag.razonar_meta('food')
                if acc_raz is not None:
                    _sig,conf,bonus = ag.predecir_recompensa(acc_raz, eq, metas_priorizadas=['food'])
                    if (conf>0 or bonus>0) and ag.decidir_explotar(eq, acc_raz):
                        accion_imag=acc_raz
            a = ag.step(sv, TODAS) if accion_imag is None else accion_imag
            obs,r,t,info=env.step(a)
            cur_pos=np.array(info['player_pos'],dtype=int)
            if a in MOV:
                delta=tuple((cur_pos-prev_pos).tolist()); facing=delta if delta!=(0,0) else MOVE_DIR[a]
            prev_pos=cur_pos
            nuevo_inv=inventario_de(info)
            ag._resultado_mundo_prev=inv_log; ag._resultado_mundo_act=nuevo_inv
            ag._aprender_resultado_mundo(a)
            ag._registrar_historia(step, a, nuevo_inv, "mundo_propio")
            ag._codificar_episodio(eq, a, nuevo_inv, "mundo_propio")
            inv_log=nuevo_inv
            # consolidar hitos al producirlos (como 0155) y PROPAGAR al otro
            for rec, acc in HITOS.items():
                if rec in nuevo_inv:
                    nodo = ag._hash_recurso_a_nodo(rec)
                    ag.consolidar_hito(acc, nodo)
                    if otro is not None:
                        otro.observar_otro(ag, acc, rec)  # el otro aprende vicario + modelo
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
    return logros, paso_make, paso_eat, total


print("="*70)
print(" exp_SGM_0173 — COLECTIVIDAD: 2 grafos en MUNDOS SEPARADOS con PROPAGACION")
print("="*70)

def _guardar(estado_json):
    out=os.path.expanduser("~/vaults/vega-vault/NOUS/DSCN-G/EXPERIMENTS/SGM/"
                           "results/results_exp_SGM_0173_colectividad_coldstart.json")
    json.dump(estado_json, open(out,"w"), indent=2, default=str)
    return out

# estado parcial: A primero (rompe su cold-start para que pueda craftear y propagar)
agA=SGMAgent(random.Random(42),D,n_nodes=N_NODES,gamma=0.01)
agB=SGMAgent(random.Random(43),D,n_nodes=N_NODES,gamma=0.01)
for a in (agA,agB):
    a.set_edges({i:random.sample(range(N_NODES),min(5,N_NODES-1)) for i in range(N_NODES)})
    a.instinto_alimentacion=DO
# A rompe su cold-start (mesa+wood inicial) -> puede craftear -> propaga a B.
# B NO rompe (aprende vicariamente de A cuando A logre el hito).
lA,pMA,pEA,tA = correr_un_mundo(agA, 42, 12, agB, romper_coldstart=True)
print(f"  proceso A (su mundo, coldstart roto): {tA} pasos, logros={sorted(lA)}, make={pMA}, eat={pEA}")
# guardar parcial INMEDIATO (no perder el trabajo de A ante interrupcion)
out_p = _guardar({
  "experiment_id":"exp_SGM_0173","experiment_name":"colectividad_coldstart_crafteo",
  "phase":"Fase 9 - colectividad emergente: 2 grafos en mundos separados con propagacion",
  "date":"2026-08-15","status":"parcial_mundo_A",
  "mission":"colectividad sin fragmentar continuidad; cada grafo en su mundo, propaga hitos al otro",
  "config":{"D":D,"N_NODES":N_NODES,"n_vidas_cada_uno":12,"seeds_A_B":[42,43]},
  "result":{"A":{"logros":sorted(lA),"paso_make":pMA,"paso_eat":pEA,"pasos":tA},"B":None,
            "conocimiento_propagado_a_B":None},
  "notes":"GUARDADO INCREMENTAL (mundo A) ante riesgo de interrupcion del proceso.",
})
print(f"  [parcial guardado] {out_p}")
# luego B
lB,pMB,pEB,tB = correr_un_mundo(agB, 43, 12, agA)
print(f"  proceso B (su mundo): {tB} pasos, logros={sorted(lB)}, make={pMB}, eat={pEB}")
nmB=len(agB.modelo_del_otro); mb=dict(agB.modelo_del_otro)
print(f"  conocimiento propagado a B: {nmB} recursos -> {mb}")

out=os.path.expanduser("~/vaults/vega-vault/NOUS/DSCN-G/EXPERIMENTS/SGM/"
                       "results/results_exp_SGM_0173_colectividad_coldstart.json")
json.dump({
  "experiment_id":"exp_SGM_0173","experiment_name":"colectividad_coldstart_crafteo",
  "phase":"Fase 9 - colectividad emergente: 2 grafos en mundos separados con propagacion de conocimiento",
  "date":"2026-08-15",
  "mision":"probar la colectividad SIN fragmentar la continuidad: cada grafo en su propio mundo; "
           "cuando UNO consolida un hito, lo PROPAGA al otro. El cruce emerge del conocimiento "
           "compartido, no de alternar un mismo cuerpo (lectura 0165).",
  "hypothesis":"con mundos separados + propagacion, cada grafo conserva la continuidad para lograr "
               "mas, y el conocimiento se acumula en la colectividad (B adopta el hito de A).",
  "config":{"D":D,"N_NODES":N_NODES,"n_vidas_cada_uno":12,"seeds_A_B":[42,43],
            "hitos_propagados": list(HITOS.keys())},
  "result":{"A":{"logros":lA,"paso_make":pMA,"paso_eat":pEA,"pasos":tA},
            "B":{"logros":lB,"paso_make":pMB,"paso_eat":pEB,"pasos":tB},
            "conocimiento_propagado_a_B":{"n_recursos":nmB,"recursos":mb}},
  "script":"experiments/exp_SGM_0173_colectividad_coldstart.py",
  "results_file":"results/results_exp_SGM_0173_colectividad_coldstart.json",
  "variant_of":"exp_SGM_0165",
  "lit_refs":["colectividad por propagacion de conocimiento","aprendizaje vicario Bandura",
              "modelo del otro ToM"],
  "notes":"Mundos separados (continuidad preservada) + propagacion de hitos entre grafos. El cruce "
           "emerge del conocimiento compartido, sin fragmentar la continuidad de ninguno.",
  "notes_criollo":"Dos cerebros, cada uno en su propio mundo, que se pasan lo que van aprendiendo. "
                    "Asi ninguno pierde su hilo, y el conocimiento se junta en el grupo.",
  },open(out,"w"),indent=2, default=str)
print(f"\n Guardado en: {out}")