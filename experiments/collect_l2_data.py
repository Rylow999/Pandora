#!/usr/bin/env python3
"""collect_l2_data.py — Recolecta datos para entrenar L2 real.

Corre el agente por N pasos guardando:
- Campo de interferencia (nodos, ombras, interferencias)
- Acción tomada
- Resultado (Δ homeostasis: food, health, V_grafo)

Output: l2_dataset.npy con los datos crudos.
"""
import sys, os, random, math, json, time
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sgm_core import SGMAgentCore
from experiments.sgm_pulsiones import crear_arbitro_default
from experiments.sgm_kuramoto import campo_interferencia

def simular_percepcion(rng, step):
    """Simula percepciones del entorno para entrenamiento."""
    hambre = rng.random()
    amenaza = rng.random() * 0.5
    recurso = rng.random()
    salud = 15 + rng.random() * 5
    comida = 10 + rng.random() * 10
    
    sv = [0.2, 0.2, hambre, amenaza, recurso, salud/20.0, comida/20.0] + [0.0]*11
    
    pos = (rng.randint(0, 50), rng.randint(0, 50))
    
    return sv, pos, food, health

def colectar(n_pasos=3600, semilla=42, verbose=True):
    """Colecta n_pasos de datos del agente."""
    rng = random.Random(semilla)
    np.random.seed(semilla)
    
    ag = SGMAgentCore(rng, 128, n_nodes=64, gamma=0.01)
    ag.set_edges({i: random.sample(range(64), min(5, 63)) for i in range(64)})
    ag.instinto_alimentacion = 5
    arbitro = crear_arbitro_default()
    ag.set_arbitro(arbitro)
    
    datos = {
        "campos": [],      # Lista de [(nodo_id, omega, interferencia)]
        "acciones": [],    # Lista de int
        "resultados": [],  # Lista de [Δfood, Δhealth, ΔV_grafo]
        "positions": [],   # Lista of (x, y)
    }
    
    food_prev, health_prev = 20.0, 20.0
    t0 = time.time()
    
    for step in range(n_pasos):
        sv, pos = simular_percepcion(rng, step)[:2]
        food = float(10 + rng.random() * 10)
        health = float(15 + rng.random() * 5)
        
        ag._posicion_actual = pos
        ag._hambre_real = sv[2]
        ag._amenaza = sv[3]
        ag._algo_enfrente = 1 if sv[4] > 0.3 else (2 if sv[3] > 0.3 else 0)
        ag._hay_gradiente = sv[4] > 0.3 or sv[3] > 0.3
        ag._gradiente_dir = (1, 0) if sv[4] > 0.3 else (0, 0)
        ag._config_grad = {"activo": sv[4] > 0.3, "fuerza": sv[4]}
        ag._config_curio = {"activo": True, "fuerza": 0.4}
        ag._inc_dirs = {1: rng.random(), 2: rng.random(), 3: rng.random(), 4: rng.random()}
        
        # Guardar estado antes
        V_prev = ag.V_grafo
        
        # Ejecutar step
        valid_actions = list(range(17))
        accion = ag.step(sv, valid_actions)
        
        # Calcular resultado
        delta_food = food - food_prev
        delta_health = health - health_prev
        delta_V = ag.V_grafo - V_prev
        
        # Guardar campo de interferencia
        zona = campo_interferencia(ag.omega, ag.phi, ag.phi[0] if ag.phi else 0.0, ag.vitalidad)
        
        datos["campos"].append(zona)
        datos["acciones"].append(accion)
        datos["resultados"].append([delta_food, delta_health, delta_V])
        datos["positions"].append(pos)
        
        food_prev, health_prev = food, health
        
        if verbose and step % 600 == 0:
            print(f"  Step {step}/{n_pasos} ({100*step/n_pasos:.0f}%) - acción={accion}, V={ag.V_grafo:.3f}")
    
    t1 = time.time()
    if verbose:
        print(f"Colecta terminada: {n_pasos} pasos en {t1-t0:.1f}s")
        print(f"  Acciones únicas: {len(set(datos['acciones']))}")
        print(f"  V_grafo final: {ag.V_grafo:.3f}")
        print(f"  Nodos: {len(ag.omega)}")
    
    return datos, ag

def guardar(datos, ruta):
    """Guarda datos en formato npy."""
    np.save(ruta, datos)
    print(f"Guardado: {ruta}")

if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 3600
    print(f"=== RECOLECCION L2: {n} pasos ===")
    datos, ag = colectar(n_pasos=n, semilla=42)
    guardar(datos, "experiments/l2_raw_data.npy")
    print("OK")