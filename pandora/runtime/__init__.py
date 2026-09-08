# -*- coding: utf-8 -*-
"""pandora/runtime — El núcleo residente que hace VIVIR a Pandora.

Encendido real: checkpoint persistente (continuidad entre sesiones), ciclo de
existencia (percepción + sueño + reintegración), y salida proactiva (hablar por
propia iniciativa, con la misma autoridad que el input humano).
"""
from pandora.runtime.estado import EstadoVivo
from pandora.runtime.nucleo import Nucleo

__all__ = ["EstadoVivo", "Nucleo"]