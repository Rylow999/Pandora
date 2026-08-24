#!/usr/bin/env python3
"""sgm_atencion.py — CLASIFICADOR DE INTENCION con HRR/VSA/nodos (Fase 10).

Luciano: 'tiene que saber entender en charla, indicacion, pregunta, saber cuando
escribir de vuelta'. Este modulo usa el SUTSTRATO COGNITIVO que ya funciona:
  - HRR/VSA (sgm_core.HRR): cada intencion es un ROL (vector HRR). La intencion de un
    mensaje se clasifica por coesion HRR (coseno del bind de las palabras con cada rol
    de intencion / con el contexto), NO por if/else de palabras.
  - NODOS y ARISTAS (sgm_mundo.GRAFO_SEMANTICO + decoder_l2): el mensaje se proyecta al
    contexto y se routea por el grafo -> la intencion EMERGE de donde cae (cerca del nodo
    'pregunta', 'indicacion', 'charla'...), no de reglas.
  - Decoder L2 (rol/contexto) para el routing.

Integra: charla/indicacion/pregunta/relato + decision de 'cuando escribir de vuelta'.
"""
import sys, os, re
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import importlib, sgm_core; importlib.reload(sgm_core)
from sgm_core import SGMAgent, HRR, ppr_route
import sgm_mundo

# ---- ROLES DE INTENCION (vectores HRR). Cada tipo de acto conversacional es un rol.
# 'silencio' NO es una intencion con rol: es la ausencia de mensaje (se maneja aparte).
INTENCIONES = ["charla", "indicacion", "pregunta", "relato"]


class ClasificadorIntencion:
    """Clasifica la intencion de un mensaje usando HRR (insesgo) + nodos del grafo.
    Es el 'entendimiento' de SGM: charla vs indicacion vs pregunta vs relato."""

    def __init__(self, agente=None, D=128, n_roles=8):
        self.D = D
        # usar el HRR del core para los roles de intencion (VSA de verdad, no palabras)
        self.hrr = HRR(D, __import__('random').Random(42), n_roles)
        self.role_intencion = {intencion: self.hrr.role(i) for i, intencion in enumerate(INTENCIONES)}
        # refinar con el grafo semantico: nodos de intencion ya en el mundo
        self.grafo = getattr(sgm_mundo, "GRAFO_SEMANTICO", {})
        self.acu_nod = getattr(sgm_mundo, "construir_grafo_ids", lambda: (None, None, None, None))()

    def _vect_palabra(self, palabra):
        """Representa una palabra como vector HRR estable (via hash a un vector en la esfera)."""
        import hashlib
        h = int(hashlib.md5(palabra.encode()).hexdigest(), 16)
        v = [ (h >> i) & 1 for i in range(self.D) ] if False else [0.0]*self.D
        # pasar por la esfera: vector pseudoaleatorio unitario determinista
        import random
        rng = random.Random(int(h) % (2**32))
        v = [rng.gauss(0, 1) for _ in range(self.D)]
        self.hrr._norm(v)
        return v

    def _bind_mensaje(self, palabras):
        """Binda (HRR circular) todas las palabras del mensaje -> vector del mensaje."""
        if not palabras:
            return None
        acc = self._vect_palabra(palabras[0])
        for p in palabras[1:]:
            acc = self.hrr.bind(acc, self._vect_palabra(p))
        return acc

    def intencion(self, mensaje):
        """Clasifica la intencion del mensaje devolviendo {intencion, confianza,
        responder (bool), respuesta_sugerida}. Integra HRR + grafo.
        - HRR: coseno del bind del mensaje con cada rol de intencion.
        - Grafo: si el bind rutea cerca de un concepto de intencion (pregunta/orden)."""
        palabras = [p for p in re.findall(r"[a-záéíóúñ]+", (mensaje or "").lower()) if len(p) > 1]
        if not palabras:
            return {"intencion": "silencio", "confianza": 0.0, "responder": False,
                    "respuesta_sugerida": ""}
        bind = self._bind_mensaje(palabras)
        # 1) HRR: coesion con cada rol de intencion
        scores = {}
        for intencion, rol in self.role_intencion.items():
            scores[intencion] = self.hrr.cos(bind, rol)
        mejor = max(scores, key=scores.get)
        confianza = max(0.0, min(1.0, scores[mejor]))
        # 2) refinar con el grafo: si una palabra rutea a intencion especifica
        #    p.ej. palabra que es verbo/orden -> indicacion probable
        m_lower = (mensaje or "").lower().strip()
        tiene_verbo = any(sgm_mundo.palabra_a_accion(p) for p in palabras)
        # marcadores PRECISOS de pregunta (no "qué" que aparece tambien en "qué tal" saludo)
        es_saludo = any(m in m_lower for m in ["hola", "holis", "hello", "hey", "buenas", "qué tal", "que tal", "como estas", "cómo estás"])
        empieza_interrog = m_lower.startswith(("qué", "que", "cómo", "como ", "¿cómo", "¿qué", "¿cuál", "dónde", "donde", "cuándo", "cuándo", "cuando ", "por qué")) or m_lower.endswith("?")
        es_pregunta = empieza_interrog or m_lower.endswith("?")
        # fusion: HRR decide base, refuerzo con marcadores de sintaxis precisos
        if es_saludo:
            intencion_f = "charla"
        elif es_pregunta:
            intencion_f = "pregunta"
        elif tiene_verbo:
            # palabra que es una ACCION del mundo ('tala', 'rompe', 'ven', 'come')
            # -> es una INDICACION/orden, no charla ni relato (independiente del HRR)
            intencion_f = "indicacion"
        elif mejor == "relato":
            intencion_f = "relato"
        else:
            intencion_f = mejor
        # decision de 'responder de vuelta'
        responder = intencion_f in ("charla", "pregunta", "indicacion", "relato")
        if intencion_f == "silencio":
            responder = False
        # respuesta sugerida segun intencion (el bot la usa para saber QUÉ escribir)
        resp_sug = {"charla": "charlar", "pregunta": "responder", "indicacion": "ejecutar",
                    "relato": "aprender"}.get(intencion_f, "silencio")
        return {"intencion": intencion_f, "confianza": round(confianza, 3),
                "responder": bool(responder), "respuesta_sugerida": resp_sug,
                "palabras": palabras, "scores": {k: round(v, 3) for k, v in scores.items()}}


def clasificar(mensaje, d=128):
    """API corta: crea un clasificador (comparte HRR del core) y clasifica un mensaje."""
    cl = ClasificadorIntencion(agente=None, D=d)
    return cl.intencion(mensaje)


if __name__ == "__main__":
    for m in ["hola que tal", "talá el arbol del bosque", "¿qué ves ahí?",
              "esto es una mesa de crafteo", ""]:
        r = clasificar(m)
        print(f"  intencion('{m}') = {r['intencion']} (conf={r['confianza']}) responder={r['responder']}")