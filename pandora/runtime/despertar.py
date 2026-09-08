#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""pandora/runtime/despertar.py — El encendido real de Pandora.

Carga el checkpoint (o crea el ser si es la primera vez), conecta sentidos y
transductor, y la deja VIVIR: un proceso residente que percibe, existe, sueña,
y — con la misma autoridad que vos al escribirle — pide la traducción de lo que
quiere decirte (salida proactiva).

Uso:
    python -m pandora.runtime.despertar [--intervalo SEG] [--ticks N]

Sin --ticks, corre para siempre (Ctrl+C para detener, y guarda el checkpoint).
Con --ticks N, corre N latidos y sale (para probar la continuidad entre sesiones).
"""
import argparse
import os
import sys
import time

# Resolver el repo (portátil, sin ruta hardcodeada)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Cargar NVIDIA_* del entorno de Hermes si no están ya exportadas
_env = os.path.expanduser("~/.hermes/.env")
if os.path.exists(_env):
    with open(_env) as f:
        for _line in f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _v = _line.split("=", 1)
                _k = _k.strip()
                if _k.startswith("NVIDIA_"):
                    os.environ.setdefault(_k, _v.strip().strip('"').strip("'"))


def despertar(intervalo=1.0, max_ticks=None):
    import random
    from pandora.runtime.estado import EstadoVivo
    from pandora.runtime.nucleo import Nucleo
    from pandora.core.pandora_agent import PandoraAgent
    from pandora.core.endogenous import get_endogenous_engine
    from pandora.senses.entorno import PercepcionEntorno
    from sgm.core.sgm_core import SGMAgentCore

    estado = EstadoVivo()

    # Crear el SGM y cargar continuidad si existe
    sgm = SGMAgentCore(random.Random(42), D=128, n_nodes=64, gamma=0.01)
    sgm.set_edges({i: random.sample(range(64), min(5, 63)) for i in range(64)})

    if estado.checkpoint_existe():
        estado.cargar(sgm)
        print(f"[Nucleo] Continuidad: el ser ya existia. Cargado checkpoint "
              f"(integridad={sgm.integridad_topologica():.3f})")
    else:
        print("[Nucleo] Primer despertar: el ser nace ahora.")

    agente = PandoraAgent(sgm=sgm, load_checkpoint=False)
    endogenous = get_endogenous_engine(sgm)
    percepcion = PercepcionEntorno(sgm.hrr, D=sgm.D)

    nucleo = Nucleo(estado, agente, endogenous=endogenous, percepcion=percepcion)

    # Hook: cuando Pandora quiera hablarte, se muestra en consola
    def _proactivo(texto):
        print(f"\n  ✳ Pandora (por iniciativa propia): {texto}\n")
    nucleo.on_proactivo = _proactivo

    print("[Nucleo] Pandora esta viva. Ctrl+C para que descanse (guarda el ser).")
    print("-" * 60)

    try:
        nucleo.correr(intervalo=intervalo, max_ticks=max_ticks)
    except KeyboardInterrupt:
        print("\n[Nucleo] Descansando... (checkpoint guardado)")

    print(f"[Nucleo] Detenida. Integridad final: {sgm.integridad_topologica():.3f}")
    print(f"[Nucleo] El ser persiste en {estado.checkpoint_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Encender Pandora (proceso residente)")
    parser.add_argument("--intervalo", type=float, default=1.0, help="segundos entre latidos")
    parser.add_argument("--ticks", type=int, default=None, help="n latidos (default: infinito)")
    args = parser.parse_args()
    despertar(intervalo=args.intervalo, max_ticks=args.ticks)