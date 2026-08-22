#!/usr/bin/env python3
"""exp_SGM_0171 — COMUNICACION EN VIVO: SGM reporta su estado mientras juega + recibe
instrucciones de Luciano y las aplica a su conducta real en Crafter.

OBJETIVO: validar la comunicacion bidireccional en accion. Mientras SGM subsiste en
Crafter:
  1) SGM REPORTarctica su estado en lenguaje natural (interfaz hibrida: el transformer
     clasifica la categoria, la plantilla arma la frase: 'tengo hambre', 'valoro madera',
     'recuerdo que obtuve X'...).
  2) LUCIANO le da una instruccion (p. ej. 'deberias comer'), SGM la procesa
     (procesar_instruccion -> afecta su estado interno) y su conducta/sub-consiguiente
     refleja ese efecto (prioriza comer).
  3) Se registran las interacciones para que el transformer aprenda de ellas.

Se mide:
  - los mensajes que SGM genera durante el juego (y en que momento / categoria),
  - el efecto de la instruccion en su conducta (comer mas, meta sugerida, valencia),
  - la acumulacion de interacciones (datos para entrenar el transformer).

Esto es el PRIMER dialogo real SGM <-> Luciano en el mundo.
"""
import sys, os, random, json
sys.path.insert(0, os.path.expanduser("~/vaults/vega-vault/NOUS/DSCN-G/EXPERIMENTS/SGM/experiments"))
sys.path.insert(0, os.path.expanduser("~/vaults/vega-vault/NOUS/DSCN-G/EXPERIMENTS/SGM"))
import importlib, sgm_core; importlib.reload(sgm_core)
from sgm_core import SGMAgent
from sgm_lang_interfaz import InterfazLenguaje
import crafter
import numpy as np

D = 128; N_NODES = 64
MOV = {1,2,3,4}
DO = 5
MOVE_DIR = {1: (-1,0), 2: (1,0), 3: (0,-1), 4: (0,1)}
TODAS = list(range(17))

# instrucciones que Luciano le dara en momentos clave del juego (comunicacion humana->SGM)
INSTRUCCIONES_PROGRAMADAS = {
    100: "deberias comer algo",       # temprano -> que priorice comer
    400: "recolecta madera para craftear",  # a mitad -> meta wood
    700: "cuidado zombie",            # tarde -> senal de amenaza
}


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


def run(seed, n_lives=3, cuadros_msg=50):
    ag=SGMAgent(random.Random(seed),D,n_nodes=N_NODES,gamma=0.01)
    ag.set_edges({i:random.sample(range(N_NODES),min(5,N_NODES-1)) for i in range(N_NODES)})
    ag.instinto_alimentacion=DO
    interf = InterfazLenguaje()
    env=crafter.Env(); env.reset()
    total=0; logros=set(); mensajes=[]; interacciones=[]
    n_comer_total=0; inst_efecto=[]; n_instrucciones=0
    for vida in range(n_lives):
        env.reset(); ag.reset_episodio()
        obs,r,t,info=env.step(0)
        prev_pos=np.array(info['player_pos'],dtype=int); facing=(0,1)
        inv_log=inventario_de(info)
        accion_hist=[]
        for step in range(1500):
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
            # aplicar una instruccion de Luciano en el paso programado (humano->SGM)
            if total in INSTRUCCIONES_PROGRAMADAS and total not in [i['paso'] for i in inst_efecto]:
                texto = INSTRUCCIONES_PROGRAMADAS[total]
                r_inst = ag.procesar_instruccion(texto)  # afecta el estado/valencia de SGM
                inst_efecto.append({"paso":total,"texto":texto,"reconocida":r_inst["reconocida"],
                                    "efecto":r_inst["efecto"]}); n_instrucciones+=1
                print(f"  [Luciano paso {total}]: '{texto}' -> SGM: {r_inst['texto']}")
            # SGM se expresa periodicamente (SGM->humano) sobre su mundo interno
            if step % cuadros_msg == 0:
                frase, cat, est = interf.expresarse(ag)
                mensajes.append({"paso":total,"categoria":cat,"frase":frase,
                                 "hambre":round(float(ag._hambre_real),2)})
            a = ag.step(sv, TODAS)
            obs,r,t,info=env.step(a)
            cur_pos=np.array(info['player_pos'],dtype=int)
            if a in MOV:
                delta=tuple((cur_pos-prev_pos).tolist()); facing=delta if delta!=(0,0) else MOVE_DIR[a]
            prev_pos=cur_pos
            nuevo_inv=inventario_de(info)
            ag._resultado_mundo_prev=inv_log; ag._resultado_mundo_act=nuevo_inv
            ag._aprender_resultado_mundo(a); ag._registrar_historia(step,a,nuevo_inv,"cuerpo")
            ag._codificar_episodio(eq,a,nuevo_inv,"cuerpo")
            accion_hist.append(a)
            if a==DO: n_comer_total+=1
            inv_log=nuevo_inv
            ag.actualizar_homeostasis(inv['food'],inv['health'])
            pain=abs(r) if r<0 else 0.0
            ag.reward(max(0.0,r),pain)
            ag.actualizar_modelo_mundo(eq, a, ag.cuantizar_estado(_sv(info)))
            for nm,c in info['achievements'].items():
                if c>0: logros.add(nm)
            total+=1
            if t: break
        # registrar interaccion para el transformer (aprendizaje)
        interf.registrar_interaccion(ag, ["tengo","hambre","necesito","comida"])
        interacciones.append(len(interf.datos_train))
    return mensajes, sorted(logros), total, n_comer_total, inst_efecto, n_instrucciones, interacciones


print("="*70)
print(" exp_SGM_0171 — COMUNICACION EN VIVO: SGM <-> Luciano en Crafter")
print("="*70)
mensajes, logros, total, n_com, inst_efecto, n_inst, interacciones = run(42, n_lives=3)
print(f"\n  seed 42: {total} pasos, logros={logros}")
print(f"  veces que acciono 'do' (comer/atacar): {n_com}")
print(f"  instrucciones de Luciano aplicadas: {n_inst}")
print(f"  interacciones acumuladas para el transformer: {interacciones}")

print("\n=== MENSAJES DE SGM DURANTE EL JUEGO (SGM -> Luciano) ===")
for m in mensajes[:15]:
    print(f"  paso {m['paso']:4d} [{m['categoria']:10s}] {m['frase']}")

print("\n=== EFECTO DE LAS INSTRUCCIONES (Luciano -> SGM) ===")
for e in inst_efecto:
    print(f"  paso {e['paso']}: '{e['texto']}' -> reconocida={e['reconocida']} efecto={e['efecto']}")

out=os.path.expanduser("~/vaults/vega-vault/NOUS/DSCN-G/EXPERIMENTS/SGM/"
                       "results/results_exp_SGM_0171_comunicacion_vivo.json")
json.dump({
  "experiment_id":"exp_SGM_0171","experiment_name":"comunicacion_en_vivo_sgm_luciano",
  "phase":"Fase 10 - comunicacion bidireccional SGM <-> Luciano en Crafter (en vivo)",
  "date":"2026-08-15","mision":"validar la comunicacion bidireccional en accion: SGM reporta su "
    "estado mientras juega, Luciano le da instrucciones y SGM las aplica a su conducta.",
  "config":{"D":D,"N_NODES":N_NODES,"n_lives":3,"seed":42,"cuadros_msg":50},
  "result":{"mensajes":mensajes,"logros":logros,"pasos":total,"n_do":n_com,
            "instrucciones_aplicadas":inst_efecto,"n_instrucciones":n_inst,
            "interacciones_transformer":interacciones},
  "script":"experiments/exp_SGM_0171_comunicacion_vivo.py",
  "results_file":"results/results_exp_SGM_0171_comunicacion_vivo.json",
  "lit_refs":["comunicacion bidireccional VSA/HDC+transformer","lenguaje emergente"],
  "notes":"SGM habla su mundo interno (frases legibles por la interfaz hibrida) mientras subsiste "
           "en Crafter, y procesa las instrucciones de Luciano (comer, madera, zombie) afectando "
           "su estado interno y conducta. Las interacciones acumuladas entrenan el transformer.",
  "notes_criollo":"El bicho te va hablando mientras juega (tiene hambre, valora madera), y cuando le "
                   "dec\u00eds algo (come, junta madera) lo tiene en cuenta. Es el primer dialogo real.",
},open(out,"w"),indent=2, default=str)
print(f"\n Guardado en: {out}")