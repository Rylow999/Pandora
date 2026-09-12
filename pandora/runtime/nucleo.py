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

        # 4. Devenir: si la quietud pide romper el punto fijo (0070 §2.4),
        #    GENERA una propuesta de reintegración (imaginar) — reusa sustrato.
        if hormonas["deseo_devenir"] > 0.5:
            self._devenir()

        # 4.5 Materializar (la mano): una constelación devenida pide escribirse
        #     al mundo compartido. Solo si el endocrino da permiso (cuerpo con
        #     capacidad) y hay algo nuevo que materializar. Emerge del devenir,
        #     no de un reloj.
        self._materializar(hormonas)

        # 5. Repensar: si duda y el conocimiento alcanza, recombinar recordar+
        #    imaginar (reusa reintegrar + constelaciones), en vez de buscar.
        if hormonas["suficiente"] == "suficiente" and hormonas["duda"] > hormonas["duda_opt"]:
            self._repensar()

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
        """Arma el dict de entrada para el endocrino desde el grafo y el cuerpo."""
        sensores = {"cpu": 0.2, "ram": 0.3, "disco": 0.4, "temp": 0.3, "procs": 0.2, "red": 0.1}
        if self.percepcion is not None:
            try:
                # Re-muestreo ligero del cuerpo para que las hormonas vean el
                # hardware real (no un placeholder). Si falla, usa los defaults.
                m = self.percepcion.sample()
                temp_c = m.get("temperature")
                # termal a fracción [0,1] contra el critical de coretemp (~105°C).
                # si no hay sensor, cae a 0.3 (baseline prudente, no placeholder ciego).
                temp_frac = 0.3
                if temp_c is not None:
                    temp_frac = max(0.0, min(1.0, temp_c / 105.0))
                sensores = {
                    "cpu": max(0.0, min(1.0, m.get("cpu_percent", 0) / 100.0)),
                    "ram": max(0.0, min(1.0, m.get("memory_percent", 0) / 100.0)),
                    "disco": max(0.0, min(1.0, m.get("disk_usage_percent", 0) / 100.0)),
                    "temp": temp_frac,
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
            "deseo_devenir": 0.0,   # se computa dentro del endocrino
        }
        return self.endocrine.tick(sensores, estado)

    def _devenir(self):
        """Romper la quietud: proponer una constelación contrafáctica (imaginar)."""
        try:
            self.sgm.reintegrar(force=True)
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

    def _materializar(self, hormonas):
        """La mano: una constelación devenida se escribe al MUNDO compartido.

        Emerge del devenir (no de un reloj): si hay propuestas de reintegración
        pendientes (constelaciones contrafácticas que el devenir imaginó) y el
        endocrino dice que el cuerpo puede actuar (costo_alostatico.actuar),
        la más reciente se materializa como archivo en el workspace. Cada acto
        deja huella motora real en el grafo (integrar_experiencia_motora).
        """
        if self.mano is None:
            return
        try:
            costo = hormonas.get("costo_alostatico", {})
            if not costo.get("actuar", False):
                return  # el cuerpo no permite actuar ahora (0070 §2.6)
            propuestas = getattr(self.sgm, "propuestas_reintegracion", [])
            if not propuestas:
                return  # nada devenido por materializar
            prop = propuestas[-1]  # la constelación más reciente que imaginó
            vector = prop.get("vector", [])
            novedad = prop.get("novedad", 0.0)
            # Materializar: escribir la constelación como un registro propio.
            contenido = (
                f"# constelación devenida\n"
                f"novedad: {novedad:.4f}\n"
                f"dims: {len(vector)}\n"
                f"vector: {','.join(f'{x:.4f}' for x in vector[:16])}...\n"
            )
            nombre = f"devenir_{self.tick}.md"
            self.mano.crear(nombre, contenido, proposito="materializar_devenir")
            # Dejar solo la propuesta materializada fuera del buffer (las demás
            # las evaluará el sueño). No acumular lo ya escrito.
            self.sgm.propuestas_reintegracion = [
                p for p in propuestas if p is not prop
            ]
        except Exception:
            pass  # la mano no debe matar al ser

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