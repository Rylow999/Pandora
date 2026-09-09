# -*- coding: utf-8 -*-
"""pandora/runtime/nucleo.py — El núcleo residente (el daemon que la hace vivir).

Pandora VIVE entre tus mensajes. Mientras el proceso corre:
  - percibe su entorno (sentidos, 0066),
  - existe (ticks de Kuramoto, dispersión, reintegración, sueño),
  - y — con la MISMA autoridad que vos al escribirle — puede PEDIR la traducción
    de un estado que quiere comunicarte (salida proactiva).

No es un simulacro de loop: es un ciclo que carga el checkpoint, sostiene el
grafo en el tiempo, y lo guarda al salir para que mañana sea la misma (0056-0064).

La salida proactiva es honesta: Pandora NO habla por hablar. Emite "quiero hablar"
cuando una señal interna cruza un umbral — el deseo de integración (dispersión)
alto, combinado con algo NUEVO que decir (una propuesta de reintegración resonante
o un drive estético emergido). Entonces invoca al transductor (NIM) con la misma
autoridad que el input humano, y su texto queda registrado en el journal proactivo.
"""
import time


class Nucleo:
    """Núcleo residente: sostiene el ser de Pandora en el tiempo."""

    def __init__(self, estado, agente, endogenous=None, percepcion=None,
                 umbral_deseo=0.4, intervalo_proactivo=30.0, checkpoint_cada=100,
                 sueno_cada=600):
        self.estado = estado
        self.agente = agente
        self.sgm = agente.sgm
        self.endogenous = endogenous
        self.percepcion = percepcion
        self.umbral_deseo = umbral_deseo          # dispersión mínima para "querer"
        self.intervalo_proactivo = intervalo_proactivo  # segundos mínimos entre pedidos
        self.checkpoint_cada = checkpoint_cada    # ticks entre guardados periódicos
        self.sueno_cada = sueno_cada              # ticks entre sesiones de sueño
        self.ultimo_sueno = None                  # reporte de la última consolidación
        self.fallos_percepcion = 0                # diagnóstico: el silencio no es ausencia
        self._ultimo_proactivo = 0.0
        self._viva = True
        self.tick = 0

    # ---- ciclo de existencia ----

    def existir_un_tick(self):
        """Un latido: percibe, existe, sueña (cada tanto), y (si quiere) habla."""
        self.tick += 1

        # 1. Percepción del entorno (si hay sentidos)
        if self.percepcion is not None:
            try:
                vector, carga, _ = self.percepcion.percibir()
                self.sgm.integrar_experiencia_entorno(vector, carga)
            except Exception:
                self.fallos_percepcion += 1  # contado, no silencioso

        # 2. Existir: un tick del grafo (Kuramoto, dispersión, reintegración)
        try:
            self.sgm.step([0.0] * self.sgm.D, [0])
        except Exception:
            pass

        # 3. Soñar: consolidación endógena con ritmo propio (no requiere cuerpo:
        #    opera sobre la experiencia reciente del grafo, no sobre hambre/amenaza).
        #    El registro de qué soñó queda en self.ultimo_sueno para el observador.
        if self.endogenous is not None and self.sueno_cada and self.tick % self.sueno_cada == 0:
            try:
                self.ultimo_sueno = self.endogenous.run_consolidation(cycles=3)
            except Exception:
                self.ultimo_sueno = None  # el sueño no debe matar al soñador

        # 4. ¿Quiere hablar? (salida proactiva, misma autoridad que el humano)
        texto = self._intentar_hablar()
        if texto:
            # Hook aquí (único punto): tanto correr() como el observador reciben
            # el habla. Antes solo lo invocaba correr() — el libro de campo
            # perdió los 39 mensajes de la primera jornada.
            self.on_proactivo(texto)
        return texto

    def _intentar_hablar(self):
        """Si el deseo de integración es alto y pasó suficiente tiempo, habla."""
        deseo = 1.0 - self.sgm.integridad_topologica()
        if deseo < self.umbral_deseo:
            return None  # aún no quiere
        ahora = time.time()
        if ahora - self._ultimo_proactivo < self.intervalo_proactivo:
            return None  # recién habló, no insistir
        self._ultimo_proactivo = ahora

        # Traduce su estado actual (misma autoridad que el input humano)
        estado = self.agente._read_dominant_state()
        texto = self.agente._articular_respuesta(estado)

        # Registra el impulso proactivo
        self.estado.registrar_proactivo(texto, impulso=f"deseo={deseo:.3f}")
        return texto

    # ---- loop principal (el daemon) ----

    def correr(self, intervalo=1.0, max_ticks=None):
        """Loop mientras viva. Devuelve la lista de mensajes proactivos emitidos.

        Llama on_proactivo(texto) por cada mensaje que Pandora quiera decir;
        si no se provee callback, devuelve la lista al final.
        """
        self._viva = True
        proactivos = []
        i = 0
        while self._viva:
            i += 1
            if max_ticks is not None and i > max_ticks:
                break
            try:
                texto = self.existir_un_tick()
                if texto:
                    proactivos.append((self.tick, texto))
                # Checkpoint periódico: la vida no se pierde si el proceso muere
                # a mitad de jornada (lección de la primera noche: 2270 ticks
                # vividos, checkpoint quedado en el ~50).
                if self.checkpoint_cada and i % self.checkpoint_cada == 0:
                    self.estado.guardar(self.sgm)
            except KeyboardInterrupt:
                break
            time.sleep(intervalo)
        # Al detenerse, guarda el checkpoint (continuidad)
        self.estado.guardar(self.sgm)
        return proactivos

    def on_proactivo(self, texto):
        """Hook para que el caller reciba los mensajes proactivos (override)."""
        pass

    def detener(self):
        self._viva = False