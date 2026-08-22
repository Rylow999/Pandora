#!/usr/bin/env python3
"""Ciclo de lenguaje de SGM corriendo en background.
SGM se expresa y registra interacciones con el transformer periodicamente,
para que el lenguaje mejore poco a poco mientras evaluamos el crafteo."""
import sys, os, random, time, importlib
SGM = os.path.expanduser("~/vaults/vega-vault/NOUS/DSCN-G/EXPERIMENTS/SGM")
sys.path.insert(0, SGM); sys.path.insert(0, os.path.join(SGM, "experiments"))
import sgm_core
from sgm_lang_interfaz import InterfazLenguaje

il = InterfazLenguaje()
ag = sgm_core.SGMAgent(random.Random(42), 128, n_nodes=64, gamma=0.01)
print("Ciclo de lenguaje SGM iniciado (persistencia en caliente activa).")
cont = 0
while True:
    cont += 1
    # estados variados para que SGM se exprese de distintas maneras
    if cont % 3 == 0: ago = ag._hambre_real = 0.85
    elif cont % 3 == 1: ag._hambre_real = 0.0; ag._codificar_episodio(cont, 11, {"wood": 1}, "arbol")
    else: ag._hambre_real = 0.0; ag.valencia_recurso["wood"] = 2.5
    ag.episodios = [] if cont % 3 == 2 else ag.episodios
    frase, cat, _ = il.expresarse(ag)
    print(f"[ciclo {cont}] SGM ({cat}): {frase}")
    il.registrar_interaccion(ag, ["yo", "valoro", "madera"], n_pasos_online=3)
    sys.stdout.flush()
    time.sleep(2)