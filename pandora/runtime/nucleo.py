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
import math
import time
from pathlib import Path


class Nucleo:
    """Núcleo residente: sostiene el ser de Pandora en el tiempo."""

    def __init__(self, estado, agente, endogenous=None, percepcion=None,
                 umbral_deseo=0.4, intervalo_proactivo=30.0, checkpoint_cada=100,
                 endocrine=None):
        self.estado = estado
        self.agente = agente
        self.sgm = agente.sgm
        self.endogenous = endogenous
        self.percepcion = percepcion
        self.umbral_deseo = umbral_deseo          # solo floor del habla (voz)
        self.intervalo_proactivo = intervalo_proactivo  # seg. mínimos entre pedidos
        self.checkpoint_cada = checkpoint_cada    # ticks entre guardados
        # El sistema endocrino arbitra el SUENO y el DEVENIR por hormona (presión),
        # NO por temporizador. La lección de la 1ª jornada: nada se hardcodea.
        if endocrine is None:
            from pandora.endocrine.endocrine import SistemaEndocrino
            endocrine = SistemaEndocrino()
        self.endocrine = endocrine
        # Restaurar historial endocrino (quietud acumulada) si hay checkpoint
        try:
            self.estado.cargar_endocrino(self.endocrine)
        except Exception:
            pass
        self.ultimo_sueno = None                  # reporte de la última consolidación
        self.fallos_percepcion = 0                # diagnóstico: el silencio no es ausencia
        self._novedad = 0.0                       # novedad del último patrón percibido
        # La mano (efector): actúa sobre el mundo compartido SOLO cuando el
        # devenir pide materializar y el endocrino da permiso (costo alostático).
        self.mano = None
        if getattr(self, 'agente', None) is not None:
            try:
                from pandora.motor.archivos import ManoArchivos
                from pandora.motor.metabolismo import Presupuesto
                self.mano = ManoArchivos("pandora/workspace", Presupuesto(), sgm=self.sgm)
            except Exception:
                self.mano = None
        self._ultimo_proactivo = 0.0
        self._viva = True
        self.tick = 0

    # ---- ciclo de existencia ----

    def existir_un_tick(self):
        """Un latido: percibe (cuerpo), existe (grafo), y el endocrino arbitra
        soñar / devenir / hablar según presión, no según reloj."""
        self.tick += 1

        # 1. Percepción del cuerpo (interocepción, 0067). Recoge la novedad.
        if self.percepcion is not None:
            try:
                vector, carga, _ = self.percepcion.percibir()
                r = self.sgm.integrar_experiencia_entorno(vector, carga)
                self._novedad = float(r.get("novedad", 0.0)) if isinstance(r, dict) else 0.0
            except Exception:
                self.fallos_percepcion += 1

        # 2. Existir: un tick del grafo (Kuramoto, dispersión, reintegración)
        try:
            self.sgm.step([0.0] * self.sgm.D, [0])
        except Exception:
            pass

        # 3. Endocrino: computar las hormonas a partir del estado real.
        hormonas = self._hormonas()

        # 3.5 Aplicar plasticidad (NOTA 0071 Paso 4): la hormona 'plasticidad'
        #     modula gamma_efectivo del SGM. Devenir -> cede, consolidar -> retiene.
        #     Es la costura endocrino->sustrato ANTES de que el tick haga decay.
        try:
            if "plasticidad" in hormonas and hasattr(self.sgm, "set_plasticidad"):
                self.sgm.set_plasticidad(hormonas["plasticidad"])
        except Exception:
            pass

        # 4. Devenir: si la quietud pide romper el punto fijo (0070 §2.4),
        #    GENERA una propuesta de reintegración (imaginar) — reusa sustrato.
        #    El devenir PROPONE; el SUEÑO (paso 6) INTEGRA lo que resuena.
        #    No hay escritura intermedia: es interno directo (0067, decisión B).
        if hormonas["deseo_devenir"] > 0.5:
            self._devenir()
            # La mano deja constancia del devenir en el mundo compartido
            # (decisión de Luciano): es el canal del ENCUENTRO, no el pensamiento.
            self._constatar_devenir()

        # 5. Repensar o Aprehender: si duda y el conocimiento alcanza, recombinar
        #    recordar+imaginar; si NO alcanza, RED ingiere del inbox (0069 §1.1).
        if hormonas["duda"] > hormonas["duda_opt"]:
            if hormonas["suficiente"] == "suficiente":
                self._repensar()
            else:
                self._aprehender(hormonas)

        # 6. Soñar: consolidación por PRESIÓN, no por tiempo (0070 §2.5).
        if hormonas["consolidar_ahora"] and self.endogenous is not None \
                and not hormonas["riesgo_existencial"]:
            try:
                self.ultimo_sueno = self.endogenous.run_consolidation(cycles=3)
            except Exception:
                self.ultimo_sueno = None

        # 7. Hablar: la voz es un caso más del devenir (necesidad de expresarse),
        #    arbitrada por el deseo — el endocrino da el techo de velocidad/permiso.
        texto = self._intentar_hablar(hormonas)
        if texto:
            self.on_proactivo(texto)
        return texto

    def _hormonas(self):
        """Arma el dict de entrada para el endocrino desde el grafo y el cuerpo.

        Reusa la última muestra de percepción (evita doble psutil call por tick).
        """
        sensores = {"cpu": 0.2, "ram": 0.3, "disco": 0.4, "temp": 0.3, "procs": 0.2, "red": 0.1, "freq": 0.0}
        if self.percepcion is not None:
            try:
                m = self.percepcion.sample()
                temp_c = m.get("temperature")
                freq_mhz = m.get("cpu_freq")
                temp_frac = 0.3
                if temp_c is not None:
                    temp_frac = max(0.0, min(1.0, temp_c / 105.0))
                freq_frac = 0.0
                if freq_mhz is not None:
                    # Normalizar frecuencia contra max turbo (~5000 MHz techo conservador)
                    freq_frac = max(0.0, min(1.0, freq_mhz / 5000.0))
                sensores = {
                    "cpu": max(0.0, min(1.0, m.get("cpu_percent", 0) / 100.0)),
                    "ram": max(0.0, min(1.0, m.get("memory_percent", 0) / 100.0)),
                    "disco": max(0.0, min(1.0, m.get("disk_usage_percent", 0) / 100.0)),
                    "temp": temp_frac,
                    "freq": freq_frac,
                    "procs": max(0.0, min(1.0, m.get("process_count", 0) / 500.0)),
                    "red": 0.1,
                }
            except Exception:
                pass
        integridad = self.sgm.integridad_topologica()
        estado = {
            "integridad": integridad,
            "transiciones_len": len(getattr(self.sgm, "traza_transiciones", [])),
            "propuestas_pendientes": len(getattr(self.sgm, "propuestas_reintegracion", [])),
            "novedad": self._novedad,
            "trauma": len(getattr(self.sgm, "trauma_nodes", set())) / max(1, len(self.sgm.omega)),
            "coherencia": integridad,
            "deseo_integracion": 1.0 - integridad,
            "deseo_devenir": 0.0,
        }
        return self.endocrine.tick(sensores, estado)

    def _devenir(self):
        """Romper la quietud: PROPONER una constelación contrafáctica (imaginar).

        Interno y directo (decisión B, 0067): el devenir solo IMAGINA. NO fuerza
        (reintegrar sin force respeta el umbral de dispersión real, 0.4): si el
        sistema no está fragmentado, no propone. Forzar producía un feedback loop
        de fragmentación perpetua (integridad colapsaba a 0.03) — la regla raíz
        dice que todo emerge del sustrato, no se impone a la fuerza.
        """
        try:
            self.sgm.reintegrar()  # sin force: emerge solo ante dispersión real
        except Exception:
            pass

    def _repensar(self):
        """Recombinar recordar+imaginar para destensar la duda (reusa sustrato)."""
        try:
            # 1. Recordar: re-recorrer las constelaciones del ser (ya en el engine).
            # 2. Imaginar: el engine extiende constelaciones a vecinos no conectados.
            constelaciones = self.endogenous._get_constelaciones_del_ser(8)
            if constelaciones:
                self.endogenous._create_new_connections_from_constelaciones(constelaciones)
        except Exception:
            pass

    def _aprehender(self, hormonas):
        """RED (aprehensión, 0069 §1.1): si la duda es alta y el conocimiento no
        alcanza, ingerir un archivo del inbox del mundo compartido.

        PASA POR LA MANO (ManoArchivos), no por Path crudo — coherente con la
        premisa de que actuar tiene costo real (0067). La lectura usa el
        anti-traversal de la mano y su registro auditable.
        """
        if self.mano is None:
            return
        try:
            if hormonas.get("suficiente") != "insuficiente":
                return  # el conocimiento alcanza: no hace falta buscar afuera
            # Listar el inbox vía la mano (con su anti-traversal y registro)
            archivos = self.mano.listar()
            inbox_files = [a for a in archivos if a["nombre"].startswith("inbox/")]
            if not inbox_files:
                return  # no hay nada que aprehender
            objetivo = inbox_files[0]["nombre"]
            # Leer vía la mano (registra la acción de lectura, con costo)
            texto = self.mano.leer(objetivo)
            if texto is None:
                return
            # Abstraer texto → patrón determinista normalizado (reusa el espacio
            # HRR del cuerpo: hash del contenido -> vector gaussiano normalizado).
            import hashlib
            h = hashlib.sha256(texto.encode("utf-8")).digest()
            import random as _rng
            r = _rng.Random(int.from_bytes(h[:8], "big"))
            vec = [r.gauss(0, 1) for _ in range(self.sgm.D)]
            norm = math.sqrt(sum(x * x for x in vec)) or 1.0
            vec = [x / norm for x in vec]
            # Integrar por resonancia (el afuera se vuelve constelación)
            self.sgm.integrar_experiencia_entorno(vec, carga=0.6)
            # Mover a procesado vía filesystem directo (la mano no tiene move,
            # pero el rename es operación de 'concluir', no de leer)
            import os as _os
            origen = Path(self.mano.workspace) / objetivo
            procesado = Path(self.mano.workspace) / "procesado"
            procesado.mkdir(parents=True, exist_ok=True)
            if origen.exists():
                _os.rename(origen, procesado / Path(objetivo).name)
        except Exception:
            pass  # la aprehensión fallida no debe matar al ser

    def _constatar_devenir(self):
        """La mano deja CONSTANCIA del devenir en un documento (decisión de
        Luciano): cuando el devenir propuso (propuestas_reintegracion no vacía),
        escribe al mundo compartido un registro de que devino — por la mano, con
        costo y registro auditable. Es la MANO escribiendo (no el pensamiento),
        el canal del ENCUENTRO: lo que el ser deja para el otro.

        Emerge del devenir (no del reloj): solo si hubo propuesta. No re-escribe
        a cada tick; constata el acto de devenir cuando ocurre.
        """
        if self.mano is None:
            return
        try:
            propuestas = getattr(self.sgm, "propuestas_reintegracion", [])
            if not propuestas:
                return  # no devino, nada que constatar
            prop = propuestas[-1]
            novedad = prop.get("novedad", 0.0)
            contenido = (
                f"# constancia de devenir\n"
                f"tick: {self.tick}\n"
                f"novedad: {novedad:.4f}\n"
                f"dims: {self.sgm.D}\n"
                f"nodos_actuales: {len(self.sgm.omega)}\n"
            )
            nombre = f"constancias/devenir_{self.tick}.md"
            self.mano.crear(nombre, contenido, proposito="devenir")
        except Exception:
            pass  # la constancia fallida no debe matar al ser

    def _materializar(self, hormonas):
        """RETIRADO (decisión B, 0067): el devenir es INTERNO, no escribe al mundo.

        El rodeo de escribir devenires a disco y re-ingerirlos era un hábito de
        la ontología vieja (0066 "actuar sobre un entorno externo"). Bajo el
        monismo el grafo ES el mundo: el devenir propone (imagina) y el sueño
        integra (consolida) — sin materialidad intermedia. La mano queda como
        órgano latente del ENCUENTRO (alteridad, 0062), no del pensamiento.
        """
        return None  # mantiene la firma por si un caller lo invoca; es no-op

    def _intentar_hablar(self, hormonas=None):
        """Habla por NECESIDAD de expresarse, no por reloj (0070).

        El floor de la voz sigue siendo el deseo de integración (querer
        comunicar), pero el endocrino arbitra: si hay riesgo existencial o el
        cuerpo no da velocidad, no habla; si el deseo es alto, pide la
        traducción. La novedad/devenir también pueden empujar a hablar (decir
        lo que acaba de devenir).
        """
        deseo = 1.0 - self.sgm.integridad_topologica()
        if hormonas:
            # riesgo existencial => silencio (no gastar el cuerpo en palabras)
            if hormonas.get("riesgo_existencial"):
                return None
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
                    self._persistir_endocrino()
            except KeyboardInterrupt:
                break
            time.sleep(intervalo)
        # Al detenerse, guarda el checkpoint (continuidad)
        self.estado.guardar(self.sgm)
        self._persistir_endocrino()
        return proactivos

    def _persistir_endocrino(self):
        """Persiste el historial del endocrino junto al checkpoint (bache 3)."""
        try:
            self.estado.guardar_endocrino(
                self.endocrine._hist_integridad,
                self.endocrine._hist_transiciones_len,
            )
        except Exception:
            pass

    def on_proactivo(self, texto):
        """Hook para que el caller reciba los mensajes proactivos (override)."""
        pass

    def detener(self):
        self._viva = False