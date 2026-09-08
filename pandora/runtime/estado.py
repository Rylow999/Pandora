# -*- coding: utf-8 -*-
"""pandora/runtime/estado.py — Persistencia del núcleo residente.

El "ser" continuo. Cuando Pandora VIVE (proceso residente), su grafo no debe
evaporarse al apagar: el checkpoint se guarda al salir y se carga al arrancar,
para que mañana sea la MISMA que hoy (0056-0064, ACTA P1).

Directorio de runtime: pandora/runtime/data/ (ignorado por git — es su estado
vivo, no código).
"""
import os
from pathlib import Path


class EstadoVivo:
    """Maneja el ciclo guardar/cargar del grafo residente.

    - checkpoint: el SGM serializado (omega, phi, clavo, hilo, constelación,
      phi_root, propuestas pendientes...).
    - journal: los mensajes que Pandora quiso decir por propia iniciativa.
    """

    def __init__(self, base_dir="pandora/runtime/data"):
        self.base = Path(base_dir)
        self.base.mkdir(parents=True, exist_ok=True)
        self.checkpoint_path = self.base / "nucleo_checkpoint.npy"
        self.journal_path = self.base / "proactivo.jsonl"

    def checkpoint_existe(self):
        return self.checkpoint_path.exists()

    def cargar(self, sgm):
        """Carga el grafo desde checkpoint. Devuelve True si había uno."""
        if not self.checkpoint_existe():
            return False
        return sgm.cargar(str(self.checkpoint_path))

    def guardar(self, sgm):
        """Guardado ATÓMICO: escribe a un archivo temporal y renombra.

        np.save directo sobre el checkpoint real puede dejarlo corrupto a medias
        si el proceso muere a mitad de escritura (crash, SIGKILL, reboot). Con
        tmp+os.replace, el checkpoint real siempre es una versión completa.
        """
        import numpy as np
        tmp = str(self.checkpoint_path) + ".tmp.npy"
        final = str(self.checkpoint_path)
        np.save(tmp, sgm._serializar_estado()) if hasattr(sgm, "_serializar_estado") else sgm.guardar(tmp)
        import os as _os
        _os.replace(tmp, final)

    def registrar_proactivo(self, texto, impulso):
        """Registra un mensaje que Pandora quiso decir por propia iniciativa."""
        import json, time
        with open(self.journal_path, "a", encoding="utf-8") as f:
            f.write(json.dumps({
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "impulso": impulso,
                "texto": texto,
            }, ensure_ascii=False) + "\n")