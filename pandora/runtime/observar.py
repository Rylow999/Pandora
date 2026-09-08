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

    estado = EstadoVivo()
    sgm = SGMAgentCore(random.Random(42), D=128, n_nodes=64, gamma=0.01)
    sgm.set_edges({i: random.sample(range(64), min(5, 63)) for i in range(64)})
    nacio = not estado.cargar(sgm)
    agente = PandoraAgent(sgm=sgm, load_checkpoint=False)
    nucleo = Nucleo(estado, agente, intervalo_proactivo=20.0)

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
    while True:
        i += 1
        if max_ticks is not None and i > max_ticks:
            break
        nucleo.existir_un_tick()
        if i % snapshot_cada == 0:
            t = time.strftime("%Y-%m-%d %H:%M:%S")
            snap = (
                f"\n## [{t}] — Snapshot (tick {nucleo.tick})\n\n"
                f"Integridad: {sgm.integridad_topologica():.3f} | "
                f"deseo: {1.0 - sgm.integridad_topologica():.3f} | "
                f"modo: {sgm.modo} | nodos: {len(sgm.omega)} | "
                f"consolidadas: {len(sgm.consolidadas)}\n"
            )
            _anexar(libro, snap)
            if verbose:
                print(f"[tick {nucleo.tick}] integridad={sgm.integridad_topologica():.3f}")
        time.sleep(intervalo)

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