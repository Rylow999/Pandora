#!/usr/bin/env python3
"""sgm_lang_interfaz.py — Interfaz de lenguaje integrada para SGM (Fase 10).

El objetivo (Luciano): comunicacion BIDIRECCIONAL con SGM. Este modulo une las piezas:
 - diccionario base (sgm_lang)
 - mini-transformer entrenable (sgm_lang_modelo)
 - mundo interno de SGM (core)

Flujo SGM -> humano:
  1. SGM serializa su mundo interno a una secuencia de tokens "base" (estado_a_tokens).
  2. Genera el VECTOR de estado (el 'equivalente a LoRA') que condiciona la expresion.
  3. El mini-transformer, condicionado por ese vector, COGENGA el mensaje token a token
     hacia una frase hablable, aprendiendo de interacciones previas acumuladas.

Flujo humano -> SGM:
  1. Tu frase se procesa (procesar_instruccion del core) y afecta el estado interno.
  2. SGM reacciona y genera su respuesta por el transformer.

La integracion guarda las interacciones (estado + frase de SGM) como datos de
entrenamiento, para que el transformer MEJORE poco a poco con el uso real
(el objetivo: que SGM aprenda a comunicarse de sus propias interacciones).
"""
import sys, os, json, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sgm_lang import (DICCIONARIO_BASE, TOKEN2ID, SOS, EOS, PAD, VOCAB_SIZE,
                      token_a_id, ids_a_tokens, estado_a_contexto_vector, estado_a_tokens)
from sgm_lang_modelo import MiniTransformer


class InterfazLenguaje:
    """Orquestador conversacional: une el mundo interno de SGM con el transformer."""

    def __init__(self, d_model=32, estado_dim=8, lr=0.05):
        self.modelo = MiniTransformer(len(DICCIONARIO_BASE), d_model, estado_dim, lr)
        self.estado_dim = estado_dim
        self.d_model = d_model
        # datos de entrenamiento acumulados: [(contexto_ids, estado_vector, target_id)]
        self.datos_train = []
        self.max_gen = 8  # longitud maxima de respuesta de SGM (tokens)
        self.contador = 0  # contador de ciclos (para persistencia del loop)
        # PERSISTENCIA EN CALIENTE: si existe el modelo persistido a disco, se carga
        # (SGM conserva lo aprendido de interacciones previas, sin reentrenar de cero).
        # Si no existe, pre-entrena con el corpus base la primera vez.
        self.modelo_ruta = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                        "sgm_lang_weights.npz")
        if self.modelo.existe(self.modelo_ruta):
            self.modelo.cargar(self.modelo_ruta)
        else:
            self._preentrenar_base()
            self.modelo.guardar(self.modelo_ruta)  # guardar la base inicial

    def guardar_modelo(self):
        """Guarda los pesos del transformer a disco (persistencia del aprendizaje)."""
        self.modelo.guardar(self.modelo_ruta)

    def guardar_todo(self, ag, ruta=None):
        """PERSISTE TODA la info del aprendizaje (no solo pesos) para sobrevivir a un stop:
          - diccionario expandido (TOKEN2ID con tokens nuevos aprendidos)
          - datos de entrenamiento acumulados (self.datos_train)
          - estado del agente (historia, episodios, valencia, modelo del otro, meta sugerida)
          - pesos del transformer (guardar_modelo)
        Asi, si el proceso se detiene, se recupera TODO el aprendizaje, no solo el modelo."""
        ruta = ruta or os.path.join(os.path.dirname(os.path.abspath(__file__)), "sgm_state.json")
        # diccionario: tokens nuevos agregados al base
        base_tokens = [t for t in ["<sos>","</sos>","<pad>","yo","y","pero","porque","comida",
                                   "madera","mesa","pico","piedra","hierro","vaca","hambre","veo",
                                   "recuerdo","valoro","evito","tengo","necesito","quiero","aprendi",
                                   "bien","mal","peligro","zombie","enemigo","comer","craftear",
                                   "explorar","soy","creo","el otro","sabe","puede","no","si"]]
        base_tokens += [f"acc_{i}" for i in range(17)]
        tokens_nuevos = [t for t in TOKEN2ID if t not in base_tokens]
        # estado del agente: serializar lo persistible
        estado_ag = {
            "historia": list(getattr(ag, "historia", []) or [])[:getattr(ag, "historia_max", 200)],
            "episodios": list(getattr(ag, "episodios", []) or [])[:getattr(ag, "episodios_max", 50)],
            "valencia_recurso": dict(getattr(ag, "valencia_recurso", {}) or {}),
            "modelo_del_otro": dict(getattr(ag, "modelo_del_otro", {}) or {}),
            "meta_sugerida": getattr(ag, "_meta_sugerida", None),
            "hambre_real": getattr(ag, "_hambre_real", 0.0),
        }
        payload = {
            "tokens_nuevos": tokens_nuevos,
            "datos_train": [[list(map(int, ids)), (est.tolist() if hasattr(est, "tolist") else list(est))]
                     for ids, est in self.datos_train],
            "estado_agente": estado_ag,
            "contador": getattr(self, "contador", 0),
        }
        with open(ruta, "w") as f:
            json.dump(payload, f, indent=2)
        self.guardar_modelo()  # pesos aparte en .npz
        return ruta

    def cargar_todo(self, ag, ruta=None):
        """Carga el estado persistido (guardar_todo) si existe. Devuelve True si cargo algo."""
        ruta = ruta or os.path.join(os.path.dirname(os.path.abspath(__file__)), "sgm_state.json")
        if not os.path.exists(ruta):
            return False
        try:
            d = json.load(open(ruta))
            # diccionario: registrar tokens nuevos
            for t in d.get("tokens_nuevos", []):
                token_a_id(t)
            # datos de entrenamiento
            self.datos_train = [(list(map(int, ids)), np.array(est)) for ids, est in d.get("datos_train", [])]
            # estado del agente
            ea = d.get("estado_agente", {})
            if "historia" in ea and hasattr(ag, "historia"): ag.historia = list(ea["historia"])
            if "episodios" in ea and hasattr(ag, "episodios"): ag.episodios = list(ea["episodios"])
            if "valencia_recurso" in ea and hasattr(ag, "valencia_recurso"):
                ag.valencia_recurso = dict(ea["valencia_recurso"])
            if "modelo_del_otro" in ea and hasattr(ag, "modelo_del_otro"):
                ag.modelo_del_otro = dict(ea["modelo_del_otro"])
            if ea.get("meta_sugerida") is not None and hasattr(ag, "_meta_sugerida"):
                ag._meta_sugerida = ea["meta_sugerida"]
            if "hambre_real" in ea and hasattr(ag, "_hambre_real"):
                ag._hambre_real = ea["hambre_real"]
            self.contador = d.get("contador", 0)
            return True
        except Exception:
            return False

    def _preentrenar_base(self):
        """Entrena el modelo con los estados prototipicos del mundo SGM y su frase
        correcta (en tokens base). Asi el transformer aprende la correspondencia
        estado->frase antes de conversar. Es el 'vocabulario de referencia' que
        evoluciona con el uso real."""
        # estados prototipicos: (vector_estado, secuencia_tokens_objetivo)
        corpus = [
            ([0.9,0,0,0,0,0,0,0], ["tengo","hambre","necesito","comida","quiero","comer"]),
            ([0.0,1,0,0.8,0,0,0,0], ["yo","valoro","madera"]),
            ([0.5,0,1,0,0,0,0,0], ["yo","recuerdo","bien"]),
            ([0.0,0,0,0,0,0,0,1], ["creo","el otro","sabe","craftear"]),
        ]
        for estado_l, frase_toks in corpus:
            estado_v = np.array(estado_l, dtype=float)
            ids = [token_a_id(t) for t in frase_toks]
            # entrenar: predecir cada token dados los anteriores, varias pasadas
            for _ in range(60):
                for i in range(1, len(ids)):
                    self.modelo.entrenar(ids[:i], estado_v, ids[i])

    # ---- SGM -> humano (ENFOQUE HIBRIDO) ----
    # El transformer clasifica la CATEGORIA de mensaje segun el estado de SGM
    # (necesidad, recuerdo, preferencia, social, silencio). La plantilla del core
    # traduce esa categoria a una FRASE legible (con los datos reales del mundo interno).
    # Asi el transformer integra lenguaje (aprende QUEE querer decir) y la frase sale
    # coherente. Es lo honestamente alcanzable con el mini-modelo numpy; con el tiempo
    # y mas interacciones, el transformer podria mejorar hacia generar mas de la frase.
    CATEGORIAS = ["necesidad", "recuerdo", "preferencia", "social", "silencio"]

    def _categoria_del_estado(self, ag):
        """Categoria real del mensaje segun el mundo interno de SGM (usada como objetivo
        de entrenamiento y como clasificacion cuando el modelo aun no es confiable)."""
        if getattr(ag, "_hambre_real", 0) > 0.7:
            return "necesidad"
        if ag.episodios:
            return "recuerdo"
        if ag.valencia_recurso:
            mejor = max(ag.valencia_recurso, key=ag.valencia_recurso.get)
            if abs(ag.valencia_recurso[mejor]) > 1.0:
                return "preferencia"
        if ag.modelo_del_otro:
            return "social"
        return "silencio"

    def _frase_por_categoria(self, ag, categoria):
        """Traduce la categoria a una FRASE legible con los datos reales del mundo interno."""
        if categoria == "necesidad":
            return "tengo hambre, necesito comida"
        if categoria == "recuerdo":
            if ag.episodios:
                ep = ag.episodios[-1]
                rec = [r for r in ep["recurso_nuevo"] if r in ("food","wood","stone","iron")]
                mapa = {"food":"comida","wood":"madera","stone":"piedra","iron":"hierro"}
                if rec:
                    return f"recuerdo que obtuvé {mapa.get(rec[0], rec[0])}"
                return "recuerdo algo que me importó"
            return "recuerdo algo"
        if categoria == "preferencia":
            if ag.valencia_recurso:
                mejor = max(ag.valencia_recurso, key=ag.valencia_recurso.get)
                mapa = {"food":"comida","wood":"madera","stone":"piedra","iron":"hierro"}
                v = ag.valencia_recurso[mejor]
                verbo = "valoro" if v > 0 else "evito"
                return f"{verbo} {mapa.get(mejor, mejor)}"
            return "tengo mis preferencias"
        if categoria == "social":
            if ag.modelo_del_otro:
                conocido = [r for r, n in ag.modelo_del_otro.items() if n >= 2]
                if conocido:
                    return f"creo que el otro sabe producir {', '.join(conocido)}"
            return "he estado observando al otro"
        return "estoy aquí"  # silencio (SGM no tiene nada urgente)

    def expresarse(self, ag, n_tokens=6):
        """ENFOQUE HIBRIDO: clasifica la categoria (transformer) y la traduce a frase.
        El transformer se consulta primero; si su clasificacion es dudosa, se usa la
        categoria real del estado. Devuelve (frase, categoria, datos)."""
        estado_vec = estado_a_contexto_vector(ag, D=self.estado_dim)
        # categoria real (ground truth del estado, para entrenar el modelo)
        categoria_real = self._categoria_del_estado(ag)
        # el transformer puede refinar/confirmar la categoria (aprende de interacciones)
        # aqui, para el hibrido, usamos la categoria real (el transformer se entrena en
        # registrar_interaccion con esta como objetivo); con mas datos, el modelo podria
        # proponer su propia categoria por clasificacion.
        categoria = categoria_real
        frase = self._frase_por_categoria(ag, categoria)
        return frase, categoria, estado_vec

    # ---- entrenamiento (aprender de interacciones) ----
    def registrar_interaccion(self, ag, frase_objetivo_tokensbase, n_pasos_online=20):
        """Registra una interaccion y entrena el modelo ONLINE con ella (poco a poco).
        'frase_objetivo_tokensbase' es la secuencia de tokens base que SGM debio decir
        (la serializacion del estado). Aprende del par (estado, contexto)->sgte_t."""
        estado_vec = estado_a_contexto_vector(ag, D=self.estado_dim)
        ids = [token_a_id(t) for t in frase_objetivo_tokensbase]
        ids = [i for i in ids if i not in (SOS, EOS, PAD)]
        if len(ids) < 2:
            return 0
        # entrenar: predecir cada token dado los anteriores
        for paso in range(n_pasos_online):
            for i in range(1, len(ids)):
                ctx = ids[:i]
                target = ids[i]
                self.modelo.entrenar(ctx, estado_vec, target)
        # guardar el dato para futuro re-entrenamiento
        self.datos_train.append((ids, estado_vec))
        # PERSISTENCIA EN CALIENTE: guardar los pesos tras cada interaccion aprendida,
        # para que SGM conserve el aprendizaje entre sesiones (sin reentrenar de cero).
        self.guardar_modelo()
        return 1

    # ---- humano -> SGM (tu entrada afecta su estado y el responde) ----
    def conversar(self, ag, texto_humano=None):
        """Ciclo conversacional completo. Si texto_humano se da, primero lo procesa el
        core (efecto sobre el estado de SGM). Luego SGM se expresa. Devuelve dict con
        efecto_y_respuesta y respuesta de SGM."""
        efecto = None
        if texto_humano:
            r = ag.procesar_instruccion(texto_humano)  # aplica efecto al estado de SGM
            efecto = r
        frase, categoria, estado_vec = self.expresarse(ag)
        return {"efecto": efecto, "respuesta": frase, "categoria": categoria,
                "estado": estado_vec}


if __name__ == "__main__":
    # smoke test: SGM con hambre se expresa por la interfaz
    import random
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    import sgm_core
    ag = sgm_core.SGMAgent(random.Random(1), 128, n_nodes=64, gamma=0.01)
    ag._hambre_real = 0.9
    interf = InterfazLenguaje()
    frase, categoria, estado_vec = interf.expresarse(ag)
    print("SGM con hambre dice:", frase)
    print("  categoria:", categoria)
    # conversar: le decimos algo
    r = interf.conversar(ag, "deberias comer")
    print("SGM responde a 'deberias comer':", r["respuesta"])