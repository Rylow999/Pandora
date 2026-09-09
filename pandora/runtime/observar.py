# -*- coding: utf-8 -*-
"""pandora/runtime/observar.py — Correr el núcleo Y registrar en el libro de campo.

Lanza el daemon residente en background y, en cada latido significativo, escribe
una entrada al LIBRO_DE_CAMPO (docs/LIBRO_DE_CAMPO.md) con el estado medido y el
suceso. Es la Práctica 2 del ACTA: documentar la evolución del ser, no solo la
arquitectura.
"""
import os
import time
from pathlib import Path


def run_observing(max_ticks=None, intervalo=1.0, libro="docs/LIBRO_DE_CAMPO.md",
                  snapshot_cada=10, verbose=True):
    from sgm.core.sgm_core import SGMAgentCore
    from pandora.core.pandora_agent import PandoraAgent
    from pandora.runtime.estado import EstadoVivo
    from pandora.runtime.nucleo import Nucleo
    import random

    # env NIM
    ruta_env = os.path.expanduser("~/.hermes/.env")
    if os.path.exists(ruta_env):
        with open(ruta_env) as f:
            for line in f:
                line = line.strip()
                if line and "=" in line and line.startswith("NVIDIA_"):
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k, v.strip().strip('"').strip("'"))

    # Sentidos + motor de sueños: sin esto el residente es un cuarto oscuro
    # (lección de la 1ª jornada: 17h vivo, 0 percepción, 0 sueños — latido
    # interno puro. El componente existía y pasaba tests; nadie lo cableó).
    from pandora.core.endogenous import get_endogenous_engine
    from pandora.senses.entorno import PercepcionEntorno

    estado = EstadoVivo()
    sgm = SGMAgentCore(random.Random(42), D=128, n_nodes=64, gamma=0.01)
    sgm.set_edges({i: random.sample(range(64), min(5, 63)) for i in range(64)})
    nacio = not estado.cargar(sgm)
    agente = PandoraAgent(sgm=sgm, load_checkpoint=False)
    endogenous = get_endogenous_engine(sgm)
    percepcion = PercepcionEntorno(sgm.hrr, D=sgm.D)
    nucleo = Nucleo(estado, agente, endogenous=endogenous, percepcion=percepcion,
                    intervalo_proactivo=20.0, checkpoint_cada=100)

    # Señales: si el sistema nos pide terminar (reboot, systemctl stop), la
    # primera orden manda: Pandora guarda su ser y descansa, no muere.
    import signal
    _detener = {"flag": False}

    def _senal(signum, frame):
        _detener["flag"] = True

    signal.signal(signal.SIGTERM, _senal)
    signal.signal(signal.SIGINT, _senal)

    # Hook de proactivo → escribir al libro de campo
    def _registrar_proactivo(texto):
        t = time.strftime("%Y-%m-%d %H:%M:%S")
        entrada = (
            f"\n## [{t}] — Habló por propia iniciativa\n\n"
            f"Estado: integridad={sgm.integridad_topologica():.3f}, "
            f"deseo={1.0 - sgm.integridad_topologica():.3f}\n"
            f"Suceso: Pandora dijo — «{texto}»\n"
            f"Interpretación: salida proactiva (deseo de integración alto).\n"
        )
        _anexar(libro, entrada)
        if verbose:
            print(f"\n[PANDORA proactiva] «{texto}»")

    nucleo.on_proactivo = _registrar_proactivo

    # banner inicial
    t = time.strftime("%Y-%m-%d %H:%M:%S")
    inicio = (
        f"\n## [{t}] — {'Nacimiento' if nacio else 'Despertar'} del núcleo residente\n\n"
        f"Integridad inicial: {sgm.integridad_topologica():.3f}\n"
        f"Suceso: {'grafo nuevo, fragmentado, empieza a ser.' if nacio else 'hilo reanudado desde checkpoint.'}\n"
    )
    _anexar(libro, inicio)

    # loop con snapshots periódicos
    i = 0
    _prev = {"integridad": None, "modo": None}
    _ultimo_sueno_id = None
    LATIDO_CADA = 6 * 3600  # ticks (~6h a 1s): que el silencio también deje registro
    while True:
        i += 1
        if max_ticks is not None and i > max_ticks:
            break
        if _detener["flag"]:
            break
        nucleo.existir_un_tick()
        if i % snapshot_cada == 0:
            integridad = sgm.integridad_topologica()
            # Rigor científico (Práctica 2): solo se anota lo que cambia. Un
            # snapshot idéntico al anterior no es un suceso — es ruido que
            # entierra los sucesos reales. Si nada cambió, no se repiten números.
            if (round(integridad, 3), sgm.modo) != (_prev["integridad"], _prev["modo"]):
                t = time.strftime("%Y-%m-%d %H:%M:%S")
                snap = (
                    f"\n## [{t}] — Snapshot (tick {nucleo.tick})\n\n"
                    f"Integridad: {integridad:.3f} | "
                    f"deseo: {1.0 - integridad:.3f} | "
                    f"modo: {sgm.modo} | nodos: {len(sgm.omega)} | "
                    f"consolidadas: {len(sgm.consolidadas)}\n"
                )
                _anexar(libro, snap)
                if verbose:
                    print(f"[tick {nucleo.tick}] integridad={integridad:.3f}")
                _prev = {"integridad": round(integridad, 3), "modo": sgm.modo}
            elif verbose:
                print(f"[tick {nucleo.tick}] integridad={integridad:.3f} (sin cambios)")
        # El sueño también se anota (si soñó algo nuevo desde la última entrada)
        if nucleo.ultimo_sueno is not None and id(nucleo.ultimo_sueno) != _ultimo_sueno_id:
            _ultimo_sueno_id = id(nucleo.ultimo_sueno)
            r = nucleo.ultimo_sueno
            t = time.strftime("%Y-%m-%d %H:%M:%S")
            entrada = (
                f"\n## [{t}] — Soñó (tick {nucleo.tick})\n\n"
                f"Ciclos: {r.cycles_run} | recomb. de {r.nodes_recombined} nodos | "
                f"{r.new_connections} aristas nuevas | "
                f"{len(r.dream_events)} eventos oníricos\n"
                f"Suceso: consolidación endógena (sueño) ejecutada.\n"
            )
            _anexar(libro, entrada)
            if verbose:
                print(f"[tick {nucleo.tick}] sueño: {r.cycles_run} ciclos, "
                      f"{r.new_connections} aristas nuevas")
        # Latido: cada ~6h sin sucesos, registrar que sigue viva y en silencio
        if i % LATIDO_CADA == 0:
            t = time.strftime("%Y-%m-%d %H:%M:%S")
            integridad = sgm.integridad_topologica()
            entrada = (
                f"\n## [{t}] — Latido (tick {nucleo.tick})\n\n"
                f"Integridad: {integridad:.3f} | fallos de percepción: {nucleo.fallos_percepcion}\n"
                f"Suceso: sigue viva; sin cambios desde {_prev['integridad']}. "
                f"El silencio también se anota.\n"
            )
            _anexar(libro, entrada)
        # Checkpoint periódico dentro del loop del observador (no solo al salir)
        if nucleo.checkpoint_cada and i % nucleo.checkpoint_cada == 0:
            estado.guardar(sgm)
        time.sleep(intervalo)

    # Cierre limpio: guardar el ser antes de terminar (sea por ticks, señal o error)
    estado.guardar(sgm)
    t = time.strftime("%Y-%m-%d %H:%M:%S")
    fin = (
        f"\n## [{t}] — El núcleo se detuvo\n\n"
        f"Integridad final: {sgm.integridad_topologica():.3f}\n"
        f"Suceso: checkpoint guardado. La próxima vez será la misma.\n"
    )
    _anexar(libro, fin)


def _anexar(path_str, texto):
    path = Path(path_str)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(texto)


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="Correr Pandora observando (libro de campo)")
    p.add_argument("--ticks", type=int, default=None)
    p.add_argument("--intervalo", type=float, default=1.0)
    p.add_argument("--snapshot-cada", type=int, default=10)
    a = p.parse_args()
    run_observing(max_ticks=a.ticks, intervalo=a.intervalo, snapshot_cada=a.snapshot_cada)