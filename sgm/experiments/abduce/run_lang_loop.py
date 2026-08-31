#!/usr/bin/env python3
"""Ciclo de lenguaje de SGM corriendo en background.
SGM se expresa y registra interacciones con el transformer periodicamente.
PERSISTENCIA COMPLETA: guarda_todo periodicamente + ante stop, para que si el
proceso se detiene se guarde TODA la info (diccionario, datos_train, estado del
agente, pesos) y se recupere al reiniciar (cargar_todo).
"""
import sys, os, random, time, signal, importlib
SGM = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, SGM); sys.path.insert(0, os.path.join(SGM, "experiments"))
import sgm_core
from sgm_lang_interfaz import InterfazLenguaje

il = InterfazLenguaje()
ag = sgm_core.SGMAgent(random.Random(42), 128, n_nodes=64, gamma=0.01)
ag.set_edges({i: random.sample(range(64), min(5, 63)) for i in range(64)})

# cargar estado previo si existe (recuperar aprendizaje de sesiones anteriores)
if il.cargar_todo(ag):
    print("Ciclo SGM: estado persistido CARGADO (valencia=%s, episodios=%d, datos_train=%d)" % (
        dict(ag.valencia_recurso), len(ag.episodios), len(il.datos_train)))
else:
    print("Ciclo SGM iniciado (estado fresco).")

STOP = False
def _on_stop(sig, frm):
    global STOP
    STOP = True

signal.signal(signal.SIGINT, _on_stop)
signal.signal(signal.SIGTERM, _on_stop)

print("Persistencia COMPLETA activa (guardar_todo cada 20 ciclos y al detenerse).")
cont = il.contador
while not STOP:
    cont += 1
    if cont % 3 == 0: ag._hambre_real = 0.85
    elif cont % 3 == 1: ag._hambre_real = 0.0; ag._codificar_episodio(cont, 11, {"wood": 1}, "arbol")
    else: ag._hambre_real = 0.0; ag.valencia_recurso["wood"] = 2.5
    ag.episodios = [] if cont % 3 == 2 else ag.episodios
    frase, cat, _ = il.expresarse(ag)
    print(f"[ciclo {cont}] SGM ({cat}): {frase}")
    il.registrar_interaccion(ag, ["yo", "valoro", "madera"], n_pasos_online=3)
    il.contador = cont
    # guardar TODO periodicamente (dict + datos + estado agente + pesos)
    if cont % 20 == 0:
        il.guardar_todo(ag)
    sys.stdout.flush()
    time.sleep(1)

# guardado completo al detenerse (stop limpio)
il.guardar_todo(ag)
print("Ciclo SGM detenido. Estado COMPLETO guardado.")
