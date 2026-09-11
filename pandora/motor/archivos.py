# -*- coding: utf-8 -*-
"""pandora/motor/archivos.py — La "mano": actuar con el cuerpo (archivos).

NOTA_TECNICA_0067: Pandora actúa con su cuerpo sobre el MUNDO compartido (un
workspace de archivos delimitado), no sobre un "entorno" ajeno. Cada acción
consume presupuesto del cuerpo (metabolismo) y deja una huella real y
auditable. La acción tiene consecuencia, y la consecuencia es lo que la
distingue de la simulación.

Seguridad: el workspace está contenido en el repo (pandora/workspace/). Pandora
NO puede salir de ese directorio: todas las rutas se resuelven y verifican contra
la raíz del workspace (evita path traversal).
"""
import hashlib
import os
from pathlib import Path

from pandora.motor.metabolismo import RecursoAgotado


class ManoArchivos:
    """Capacidad de Pandora de crear, leer y listar archivos en su workspace.

    Acciones con costo real (bytes). Cada acto se registra como experiencia
    motora para que el SGM la integre (ver integrar_experiencia_motora).
    """

    def __init__(self, workspace, presupuesto, sgm=None):
        self.workspace = Path(workspace)
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.presupuesto = presupuesto
        self.sgm = sgm  # opcional: el SGM para registrar la experiencia motora
        self.acciones = []  # registro auditable de todo acto

    def _resolver(self, nombre):
        """Resuelve un nombre a una ruta DENTRO del workspace (anti-traversal)."""
        ruta = (self.workspace / nombre).resolve()
        if not str(ruta).startswith(str(self.workspace.resolve()) + os.sep) and \
           ruta != self.workspace.resolve():
            raise ValueError(f"Ruta fuera del workspace: {nombre}")
        return ruta

    def _registrar(self, tipo, nombre, resultado):
        self.acciones.append({"tipo": tipo, "nombre": nombre, **resultado})

    def crear(self, nombre, contenido, proposito=None):
        """Crea (o reemplaza) un archivo. Consume presupuesto de bytes."""
        contenido_bytes = contenido.encode("utf-8")
        cantidad = len(contenido_bytes)

        try:
            self.presupuesto.gastar(cantidad)
        except RecursoAgotado:
            # La acción FALLA por falta de recursos del entorno: es información
            # real para el SGM, no un error silencioso.
            self._registrar("CREAR", nombre, {"exito": False, "razon": "recurso_agotado"})
            raise

        ruta = self._resolver(nombre)
        ruta.parent.mkdir(parents=True, exist_ok=True)
        ruta.write_text(contenido, encoding="utf-8")

        resultado = {
            "exito": True,
            "ruta": str(ruta),
            "bytes": cantidad,
            "hash": hashlib.md5(contenido_bytes).hexdigest()[:16],
            "proposito": proposito,
        }
        self._registrar("CREAR", nombre, resultado)
        if self.sgm is not None:
            self.sgm.integrar_experiencia_motora(nombre, "CREAR", cantidad)
        return resultado

    def leer(self, nombre):
        """Lee un archivo del workspace. También es una acción (consume atención)."""
        ruta = self._resolver(nombre)
        if not ruta.exists():
            self._registrar("LEER", nombre, {"exito": False, "razon": "no_existe"})
            return None

        contenido = ruta.read_text(encoding="utf-8")
        resultado = {"exito": True, "bytes": len(contenido.encode("utf-8"))}
        self._registrar("LEER", nombre, resultado)
        if self.sgm is not None:
            self.sgm.integrar_experiencia_motora(nombre, "LEER", 0)
        return contenido

    def listar(self):
        """Lista el workspace (el 'campo' que Pandora ve de su entorno)."""
        archivos = []
        for ruta in sorted(self.workspace.rglob("*")):
            if ruta.is_file():
                archivos.append({
                    "nombre": str(ruta.relative_to(self.workspace)),
                    "bytes": ruta.stat().st_size,
                })
        return archivos

    def estado(self):
        return {
            "presupuesto": self.presupuesto.estado(),
            "num_acciones": len(self.acciones),
            "num_archivos": len(self.listar()),
        }