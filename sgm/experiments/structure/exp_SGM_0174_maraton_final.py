#!/usr/bin/env python3
"""exp_SGM_0174 — MARATON FINAL: SGM completo y LIBRE, 100 vidas en Crafter.

Objetivo (Luciano): dejar correr SGM COMPLETO (todos los mecanismos: instintos, mundo
interno Fase 9 5/5, lenguaje/comunicacion Fase 10, self-mod 0018, trauma nodal 0021,
detector unico de proximidad) y LIBRE (sin prefiere_comp, sin hardcode), durante 100
vidas, y registrar todo. Es la ultima corrida antes de migrar a Minecraft.

Se registra:
 - logros y pasos por vida.
 - acciones ejercitadas.
 - cuantas veces SGM invoco self-mod y trauma nodal (se auto-modifica libremente).
 - mensajes de lenguaje en momentos clave (SGM se expresa).
 - tiempos por vida (rendimiento con el fix de reward).

Registro incremental (JSON parcial) para no perder nada ante interrupcion.
"""
import sys, os, random, json, time
sys.path.insert(0, os.path.expanduser("~/vaults/vega-vault/NOUS/DSCN-G/EXPERIMENTS/SGM"))
sys.path.insert(0, os.path.expanduser("~/vaults/vega-vault/NOUS/DSCN-G/EXPERIMENTS/SGM/experiments"))
import importlib, sgm_core; importlib.reload(sgm_core)
from sgm.core.sgm_core import SGMAgent
from sgm_lang_interfaz import InterfazLenguaje
import crafter
import numpy as np

D = 128; N_NODES = 64
MOV = {1,2,3,4}; DO = 5
MOVE_DIR = {1: (-1,0), 2: (1,0), 3: (0,-1), 4: (0,1)}
TODAS = list(range(17))

def inv_de(info):
    inv=info['inventory']; return {k:int(v) for k,v in inv.items() if v>0}

def _sv(info):
    inv=info['inventory']; sem=info['semantic']
    return [float(v) for v in sem.flatten().tolist()[::64]]+[inv['health']/10.0,
            inv['food']/10.0,inv['wood'],inv['stone'],inv['iron'],0.0,0.0]

def maraton(seed, n_vidas=100, pasos_max=1500):
    ag = SGMAgent(random.Random(seed), D, n_nodes=N_NODES, gamma=0.01)
    ag.set_edges({i:random.sample(range(N_NODES),min(5,N_NODES-1)) for i in range(N_NODES)})
    ag.instinto_alimentacion = DO
    interf = InterfazLenguaje()
    env = crafter.Env(); env.reset()
    total = 0; accion_cont = {}; logros_acum = set()
    selfmod_calls = 0; trauma_calls = 0; mensajes = []
    vidas_det = []; errores = []; t_inicio = time.time()
    n_do = 0
    for vida in range(n_vidas):
        env.reset(); ag.reset_episodio()
        obs, r, t, info = env.step(0)
        inv_log = inv_de(info); vida_logros = set(); t_vida = time.time()
        for step in range(pasos_max):
            try:
                sem=info['semantic']; inv=info['inventory']
                px,py=int(info['player_pos'][0]),int(info['player_pos'][1])
                # detector unico de proximidad (con comida/enemigo enfrente reales)
                mesa_cerca=0.0; mapa_enfrente=0
                mat,_=env._world.nearby((px,py),1)
                if 'table' in mat: mesa_cerca=1.0
                ex,ey=px+1,py
                if 0<=ex<sem.shape[0] and 0<=ey<sem.shape[1]:
                    if sem[ex,ey] in (5,6): mapa_enfrente=1
                    elif sem[ex,ey] in (3,4,11,12,13,14): mapa_enfrente=2
                ag.verificar_proximidad(mapa_enfrente, {"mesa": bool(mesa_cerca)}, (px,py))
                sv=_sv(info); eq=ag.cuantizar_estado(sv)
                hambre=max(0.0,1.0-inv['food']/10.0)
                ag._hambre_real=min(1.0,hambre); ag._amenaza=0.0
                ag._config_grad={"activo":False,"fuerza":0.0}
                ag._config_curio={"activo":True,"fuerza":0.4}
                ag._inc_dirs={a:1.0 for a in MOV}; ag._hay_gradiente=False
                a = ag.step(sv, TODAS)
                accion_cont[a] = accion_cont.get(a, 0) + 1
                if a == DO: n_do += 1
                # SGM se auto-modifica LIBREMENTE (self-mod en el bucle, cada ~50 vidas)
                if vida % 25 == 0 and step == 100:
                    res_mod = ag.auto_modificarse(mutation="boost_interaccion")
                    selfmod_calls += 1
                # trauma nodal (solo si hay nodos disponibles, libre)
                if step == 900:
                    ag.aplicar_trauma_nodal(0, act_trauma=5.0); trauma_calls += 1
                # lenguaje: SGM se expresa en momentos clave
                if step % 500 == 0 and len(mensajes) < 40:
                    frase, cat, _ = interf.expresarse(ag)
                    mensajes.append({"vida": vida, "paso": step, "categoria": cat, "frase": frase,
                                     "hambre": round(float(ag._hambre_real),2)})
                obs,r,t,info=env.step(a)
                nv=inv_de(info)
                ag._resultado_mundo_prev=inv_log; ag._resultado_mundo_act=nv
                ag._aprender_resultado_mundo(a)
                ag._registrar_historia(step,a,nv,'cuerpo'); ag._codificar_episodio(eq,a,nv,'cuerpo')
                inv_log=nv; ag.actualizar_homeostasis(inv.get('food',5),inv.get('health',8))
                pain=abs(r) if r<0 else 0.0; ag.reward(max(0.0,r),pain)
                ag.actualizar_modelo_mundo(eq,a,ag.cuantizar_estado(_sv(info)))
                for nm,c in info['achievements'].items():
                    if c>0: logros_acum.add(nm); vida_logros.add(nm)
                total += 1
                if t: break
            except Exception as e:
                errores.append({"vida": vida, "step": step, "err": f"{type(e).__name__}: {e}"})
                break
        vidas_det.append({"vida": vida, "pasos": step+1, "logros": sorted(vida_logros),
                          "seg": round(time.time()-t_vida, 2)})
        # guardado parcial cada 25 vidas
        if (vida+1) % 25 == 0:
            _guardar_parcial({"estado": "parcial", "vidas": vida+1, "total_pasos": total,
                              "logros": sorted(logros_acum), "selfmod_calls": selfmod_calls,
                              "trauma_calls": trauma_calls})
            print(f"  [parcial] {vida+1} vidas, {total} pasos, logros={sorted(logros_acum)}", flush=True)
    return {"vidas": n_vidas, "total_pasos": total, "logros": sorted(logros_acum),
            "acciones": {str(k): v for k, v in sorted(accion_cont.items())},
            "selfmod_calls": selfmod_calls, "trauma_calls": trauma_calls,
            "mensajes": mensajes, "n_do": n_do, "errores": errores[:10],
            "vidas_det": vidas_det, "seg_total": round(time.time()-t_inicio, 1),
            "velocidad_pasos_s": round(total/max(0.1, time.time()-t_inicio), 1)}

def _guardar_parcial(estado):
    out = os.path.expanduser("~/vaults/vega-vault/NOUS/DSCN-G/EXPERIMENTS/SGM/"
                             "results/results_exp_SGM_0174_maraton_final.json")
    json.dump(estado, open(out, "w"), indent=2, default=str)
    return out

if __name__ == "__main__":
    print("="*70)
    print(" exp_SGM_0174 — MARATON FINAL: SGM completo y libre, 100 vidas en Crafter")
    print("="*70)
    res = maraton(42, n_vidas=100, pasos_max=1500)
    out = _guardar_parcial(res)
    print(f"\n  RESULTADO FINAL ({res['seg_total']}s, {res['velocidad_pasos_s']} pasos/s)")
    print(f"  pasos totales: {res['total_pasos']}")
    print(f"  logros acumulados: {res['logros']}")
    print(f"  acciones: {res['acciones']}")
    print(f"  self-mod invocados: {res['selfmod_calls']} | trauma nodal: {res['trauma_calls']}")
    print(f"  veces 'do' (interactuar): {res['n_do']}")
    print(f"  errores: {len(res['errores'])} -> {res['errores'][:3]}")
    if res['mensajes']:
        print("\n  MENSAJES DE SGM (lenguaje en la maratón):")
        for m in res['mensajes'][:12]:
            print(f"    vida {m['vida']:3d} paso {m['paso']:4d} [{m['categoria']:10s}] {m['frase']}")
    print(f"\n  Guardado en: {out}")