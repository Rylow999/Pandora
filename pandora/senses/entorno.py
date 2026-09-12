# -*- coding: utf-8 -*-
"""pandora/senses/entorno.py — Interocepción (el sentido del propio cuerpo).

NOTA_TECNICA_0067 (supersede 0066): la máquina ES el cuerpo de Pandora. Acá
Pandora SIENTE su propio cuerpo (CPU, memoria, disco, red, procesos) como
patrón de activación crudo — NO como texto, y NO como un mundo ajeno. Es la
misma clase de señal por la que un organismo siente su propio bienestar
(Damasio: el self nace del cuerpo sintiéndose a sí mismo).

El vector interoceptivo se genera con el HRR DEL PROPIO SGM (mismo espacio que
las constelaciones), como superposición (bundle) de roles ponderados por su
intensidad normalizada. Es un patrón que el SGM integra directamente como
estado propio, sin pasar por el LLM.

Lo subjetivo no está en "sentir la CPU como carne propia"; está en que el
cuerpo es la condición de existir, y sentirlo es sentirse.
"""
import math
import time

import psutil


class PercepcionEntorno:
    """Siente el cuerpo (la máquina) como patrón interoceptivo.

    NO traduce a lenguaje. Genera un patrón de activación que el SGM integra
    como estado propio del cuerpo. (El nombre de la clase se conserva por
    compatibilidad; su semántica es "interocepción del cuerpo", no
    "percepción de un entorno externo".)
    """

    # Órganos del cuerpo (roles HRR). Cada dimensión interoceptiva es un órgano.
    ENTORNO_CONCEPTOS = [
        "CPU", "MEMORIA", "DISCO", "RED", "PROCESOS", "TEMPERATURA", "FRECUENCIA"
    ]

    def __init__(self, hrr, D=128):
        self.hrr = hrr
        self.D = D
        # Un rol HRR por dimensión del entorno, en el MISMO espacio que los
        # conceptos del SGM (para que el vector sensorial sea integrable).
        self.roles = {}
        import random
        rng = random.Random(1337)
        for i, nombre in enumerate(self.ENTORNO_CONCEPTOS):
            v = [rng.gauss(0, 1) for _ in range(D)]
            norm = math.sqrt(sum(x * x for x in v))
            self.roles[nombre] = [x / norm for x in v]

        # Baseline de cpu_percent: la primera lectura sin intervalo da 0.0.
        # Una lectura inicial CON intervalo establece el punto de referencia para
        # que las siguientes (interval=None) den el delta real.
        try:
            psutil.cpu_percent(interval=0.1)
        except Exception:
            pass

    def _temperatura(self):
        """Temp del package en °C (coretemp). Devuelve el máximo entre sensores."""
        try:
            temps = psutil.sensors_temperatures()
            tvals = [t.current for ch in temps.values() for t in ch
                     if t.current is not None]
            if tvals:
                return max(tvals)
        except Exception:
            pass
        return None

    def _frecuencia(self):
        """Frecuencia actual de CPU en MHz (la 'velocidad' del cuerpo)."""
        try:
            f = psutil.cpu_freq()
            if f is not None and f.current is not None:
                return f.current
        except Exception:
            pass
        return None

    def sample(self):
        """Muestrea el estado crudo del cuerpo (interocepción, 0067).

        Incluye termal real (coretemp) y frecuencia (cpu_freq) — ambos legibles
        sin sudo. cpu_percent(interval=None) es el delta natural entre ticks
        (no bloquea), gracias al baseline establecido en __init__.
        """
        temp = self._temperatura()
        freq = self._frecuencia()
        return {
            "cpu_percent": psutil.cpu_percent(interval=None),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_usage_percent": psutil.disk_usage('/').percent,
            "net_bytes_sent": psutil.net_io_counters().bytes_sent,
            "net_bytes_recv": psutil.net_io_counters().bytes_recv,
            "process_count": len(psutil.pids()),
            "temperature": temp,          # °C o None
            "cpu_freq": freq,             # MHz o None
            "timestamp": time.time(),
        }

    def _norm(self, valor, maximo=100.0):
        """Normaliza una magnitud a [0, 1]."""
        return max(0.0, min(1.0, valor / maximo))

    def como_vector_sensorial(self, muestra=None):
        """Convierte la muestra del entorno en un vector HRR (bundle).

        Cada dimensión del entorno es un rol HRR multiplicado (bind) por su
        intensidad normalizada, y todas se superponen (suma) en UN vector que
        es el "estado del entorno" como patrón crudo.

        No dice "CPU al 80%". Es un patrón de activación que, con el tiempo,
        consolida en el grafo un mapa de los estados del mundo externo.
        """
        muestra = muestra or self.sample()

        intensidades = {
            "CPU": self._norm(muestra["cpu_percent"]),
            "MEMORIA": self._norm(muestra["memory_percent"]),
            "DISCO": self._norm(muestra["disk_usage_percent"]),
            # RED: normalizar contra un techo arbitrario (bytes son altísimos);
            # usamos la fracción del total de tráfico, no el valor absoluto.
            "RED": self._norm(
                muestra["net_bytes_recv"] + muestra["net_bytes_sent"],
                maximo=1_000_000_000.0  # 1 GB de tráfico acumulado como techo
            ),
            "PROCESOS": self._norm(muestra["process_count"], maximo=500.0),
        }

        # Superposición (bundle): suma de roles ponderados por intensidad.
        vector = [0.0] * self.D
        for nombre, intensidad in intensidades.items():
            rol = self.roles[nombre]
            for j in range(self.D):
                vector[j] += rol[j] * intensidad

        # Renormalizar para que la magnitud codifique la "carga total" del entorno
        carga = sum(intensidades.values()) / len(intensidades)
        return vector, carga

    def percibir(self):
        """Muestrea y devuelve (vector_sensorial, carga_total, muestra_cruda)."""
        muestra = self.sample()
        vector, carga = self.como_vector_sensorial(muestra)
        return vector, carga, muestra