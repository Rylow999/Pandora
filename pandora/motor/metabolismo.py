# -*- coding: utf-8 -*-
"""pandora/motor/metabolismo.py — Presupuesto de recursos (el costo de actuar).

NOTA_TECNICA_0066: este "metabolismo" NO es un cuerpo — es la RESTRICCIÓN REAL
del entorno. Las acciones tienen costo porque el mundo tiene límites (bytes,
espacio), no porque Pandora tenga órganos. El costo es lo que convierte la
acción en agencia: decidir entre dos actos porque no alcanza para ambos es
voluntad, no simulación.
"""


class RecursoAgotado(Exception):
    """El entorno ya no admite más acción (se agotó el presupuesto)."""


class Presupuesto:
    """Presupuesto de recursos que Pandora puede consumir al actuar sobre su entorno.

    Conteo simple de bytes escritos, con tope y regeneración lenta. Es el
    análogo operativo de "el mundo tiene límites": la CPU, el disco y la red de
    la máquina no son infinitos, y Pandora percibe esa finitud como costo.
    """

    def __init__(self, max_bytes=10 * 1024 * 1024, tasa_regeneracion=0.01):
        self.max_bytes = max_bytes
        self.tasa_regeneracion = tasa_regeneracion  # fracción del tope por tick
        self.gastados = 0

    @property
    def restantes(self):
        return self.max_bytes - self.gastados

    def gastar(self, cantidad):
        if cantidad > self.restantes:
            raise RecursoAgotado(
                f"Entorno sin espacio: {cantidad} bytes > {self.restantes} restantes"
            )
        self.gastados += cantidad
        return self.restantes

    def regenerar(self):
        """El presupuesto se repone despacio (el entorno se 'recupera')."""
        self.gastados = max(0, self.gastados - int(self.max_bytes * self.tasa_regeneracion))
        return self.restantes

    def estado(self):
        return {
            "max_bytes": self.max_bytes,
            "gastados": self.gastados,
            "restantes": self.restantes,
            "fraccion_usada": self.gastados / self.max_bytes if self.max_bytes else 0.0,
        }