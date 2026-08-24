#!/usr/bin/env python3
"""sgm_metacognicion.py — METACOGNICIÓN de Pandora.

Pandora razona sobre sí misma, duda de sus creencias, prueba hipótesis
y experimenta en el mundo para validar su conocimiento.

Alineado con el documento PURE-L2: "identidad en trayectoria, no en nodos"
y "Kuramoto: la sincronización es proxy de relevancia cognitiva".

La metacognición opera en 3 niveles:
1. AUTO-RAZONAMIENTO: aplicar inducción/deducción/abducción a sus propias creencias
2. DUDA: detectar contradicciones, incertidumbre, zonas ciegas
3. EXPERIMENTACIÓN: generar hipótesis, probarlas, aprender del resultado
"""
import sys, os, random, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import importlib, sgm_core; importlib.reload(sgm_core)
from sgm_core import SGMAgent


class Metacognicion:
    """Sistema de metacognición: razonar sobre el propio razonamiento."""

    def __init__(self, agente):
        self.agente = agente
        self.creencias = {}          # creencia -> confianza (0-1)
        self.historial_dudas = []    # registro de dudas pasadas
        self.experimentos = []       # experimentos realizados
        self.reflexiones = []        # reflexiones sobre acciones pasadas

    def reflexionar(self):
        """Reflexiona sobre el estado actual y sus propias creencias.
        Devuelve una reflexión (dict con tipo, contenido, confianza)."""
        # Detectar contradicciones entre creencias
        contradicciones = self._detectar_contradicciones()

        # Detectar incertidumbre alta
        incertidumbre = getattr(self.agente, 'incertidumbre_acum', 0)

        # Detectar zonas ciegas (nodos sin explorar)
        zonas_ciegas = self._detectar_zonas_ciegas()

        reflexion = {
            "contradicciones": contradicciones,
            "incertidumbre": incertidumbre,
            "zonas_ciegas": zonas_ciegas,
            "confianza_global": self._calcular_confianza_global(),
        }

        self.reflexiones.append(reflexion)
        return reflexion

    def dudar(self, creencia, contexto=None):
        """Genera duda sobre una creencia específica.
        Evalúa si la creencia es confiable dado el contexto.
        Devuelve (es_confiable, razon)."""
        confianza = self.creencias.get(creencia, 0.5)

        # Si la confianza es baja, dudar
        if confianza < 0.3:
            return False, f"confianza baja ({confianza:.2f})"

        # Si hay contradicciones con otras creencias
        for otra_creencia, otra_confianza in self.creencias.items():
            if otra_creencia != creencia:
                # Si dos creencias se contradicen (simplificación: si tienen confianza opuesta)
                if abs(confianza - otra_confianza) > 0.5:
                    return False, f"contradice {otra_creencia}"

        # Si el contexto sugiere que la creencia es obsoleta
        if contexto:
            for palabra in contexto:
                if palabra in self.creencias and self.creencias[palabra] < confianza:
                    return False, f"contexto sugiere otra cosa ({palabra})"

        return True, "creencia consistente"

    def experimentar(self, hipotesis, accion, contexto):
        """Diseña y ejecuta un experimento para probar una hipótesis.
        hipotesis: string (p.ej. "si tala arbol obtengo madera")
        accion: función a ejecutar
        contexto: dict con el estado actual
        Devuelve (resultado, aprendido)"""
        # Registrar el experimento
        experimento = {
            "hipotesis": hipotesis,
            "estado_inicial": contexto.copy(),
            "resultado": None,
            "aprendido": None,
        }

        # Ejecutar la acción
        try:
            resultado = accion()
            experimento["resultado"] = resultado

            # Evaluar si la hipótesis se confirmó
            if resultado:
                experimento["aprendizado"] = f"hipótesis confirmada: {hipotesis}"
                # Aumentar confianza en la creencia
                for palabra in hipotesis.split():
                    self.creencias[palabra] = min(1.0, self.creencias.get(palabra, 0.5) + 0.1)
            else:
                experimento["aprendido"] = f"hipótesis refutada: {hipotesis}"
                # Disminuir confianza
                for palabra in hipotesis.split():
                    self.creencias[palabra] = max(0.0, self.creencias.get(palabra, 0.5) - 0.1)

        except Exception as e:
            experimento["resultado"] = f"error: {e}"
            experimento["aprendido"] = "experimento falló"

        self.experimentos.append(experimento)
        return experimento["resultado"], experimento["aprendido"]

    def razonar_sobre_si_mismo(self):
        """Auto-razonamiento: aplica inducción, deducción y abducción a sí mismo.
        Devuelve un dict con el análisis."""
        analisis = {}

        # INDUCCIÓN: de casos particulares a reglas generales sobre sí mismo
        if len(self.reflexiones) >= 3:
            # Buscar patrones en reflexiones pasadas
            confianza_promedio = sum(r["confianza_global"] for r in self.reflexiones[-3:]) / 3
            analisis["induccion"] = f"mi confianza promedio es {confianza_promedio:.2f}"

        # DEDUCCIÓN: de reglas generales a conclusiones específicas
        if analisis.get("induccion"):
            if "confianza" in analisis["induccion"]:
                confianza_valor = float(analisis["indiccion"].split()[-1])
                if confianza_valor > 0.7:
                    analisis["deduccion"] = "puedo confiar en mi conocimiento"
                else:
                    analisis["deduccion"] = "debo dudar de mi conocimiento"

        # ABDUCCIÓN: inferir la mejor explicación para el estado actual
        incertidumbre = getattr(self.agente, 'incertidumbre_acum', 0)
        if incertidumbre > 5:
            analisis["abduccion"] = "hay algo que no entiendo bien"
        elif incertidumbre < 2:
            analisis["abduccion"] = "comprendo mi situación"

        return analisis

    def _detectar_contradicciones(self):
        """Detecta contradicciones entre creencias."""
        contradicciones = []
        creencias_list = list(self.creencias.items())
        for i in range(len(creencias_list)):
            for j in range(i + 1, len(creencias_list)):
                c1, v1 = creencias_list[i]
                c2, v2 = creencias_list[j]
                if abs(v1 - v2) > 0.6:
                    contradicciones.append((c1, c2))
        return contradicciones

    def _detectar_zonas_ciegas(self):
        """Detecta nodos del grafo con poca exploración."""
        zonas_ciegas = []
        for i, vitalidad in enumerate(self.agente.vitalidad):
            if vitalidad < 0.2:
                zonas_ciegas.append(i)
        return zonas_ciegas[:5]  # top 5

    def _calcular_confianza_global(self):
        """Calcula la confianza global del sistema en su conocimiento."""
        if not self.creencias:
            return 0.5
        return sum(self.creencias.values()) / len(self.creencias)

    def generar_duda_texto(self):
        """Genera una expresión de duda en lenguaje natural."""
        reflexion = self.reflexionar()

        if reflexion["contradicciones"]:
            return "tengo contradicciones en mi conocimiento"
        elif reflexion["incertidumbre"] > 5:
            return "no estoy seguro de lo que sé"
        elif reflexion["zonas_ciegas"]:
            return "hay cosas que no conozco"
        elif reflexion["confianza_global"] < 0.4:
            return "dudo de mi propio entendimiento"
        else:
            return "estoy razonablemente seguro"


class Experimentador:
    """Sistema de experimentación activa: probar hipótesis en el mundo."""

    def __init__(self, agente, metacognicion):
        self.agente = agente
        self.meta = metacognicion
        self.hipotesis_por_probar = []

    def generar_hipotesis(self):
        """Genera hipótesis a partir del conocimiento actual."""
        hipotesis = []

        # Hipótesis sobre acciones y resultados
        for accion in ["talar", "minar", "craftear", "atacar"]:
            for recurso in ["madera", "piedra", "hierro", "comida"]:
                hipotesis.append(f"si {accion} obtengo {recurso}")

        # Hipótesis sobre el mundo
        hipotesis.append("si exploro encuentro recursos")
        hipotesis.append("si me alejo del peligro sobrevivo")

        return hipotesis

    def priorizar_experimentos(self):
        """Prioriza qué experimentar primero (los más inciertos)."""
        hipotesis = self.generar_hipotesis()
        # Ordenar por confianza (los menos confiados primero)
        hipotesis.sort(key=lambda h: self.meta.creencias.get(h, 0.5))
        return hipotesis[:3]

    def simular_experimento(self, hipotesis):
        """Simula un experimento mental (sin ejecutar en el mundo).
        Devuelve (resultado_probable, confianza)."""
        # Buscar conexiones en el grafo que apoyen la hipótesis
        palabras = hipotesis.split()
        nodos_relacionados = []
        for palabra in palabras:
            if palabra in self.agente.edges:
                nodos_relacionados.extend(self.agente.edges[palabra])

        # Si hay conexiones, la hipótesis es más probable
        probabilidad = min(1.0, len(nodos_relacionados) * 0.2)
        return probabilidad > 0.5, probabilidad


if __name__ == "__main__":
    print("=== DEMO: METACOGNICIÓN DE PANDORA ===")
    ag = SGMAgent(random.Random(42), 128, n_nodes=64, gamma=0.01)
    ag.set_edges({i: random.sample(range(64), min(5, 63)) for i in range(64)})

    meta = Metacognicion(ag)

    # Establecer algunas creencias
    meta.creencias["talar"] = 0.8
    meta.creencias["madera"] = 0.7
    meta.creencias["zombie"] = 0.3
    meta.creencias["peligro"] = 0.6

    # Reflexionar
    print("\n[Reflexión]")
    reflexion = meta.reflexionar()
    print(f"  Confianza global: {reflexion['confianza_global']:.2f}")
    print(f"  Incertidumbre: {reflexion['incertidumbre']:.2f}")
    print(f"  Contradicciones: {reflexion['contradicciones']}")

    # Dudar
    print("\n[Duda]")
    for creencia in ["talar", "zombie", "inexistente"]:
        confiable, razon = meta.dudar(creencia)
        print(f"  '{creencia}': {'confiable' if confiable else 'dudoso'} ({razon})")

    # Razonar sobre sí mismo
    print("\n[Auto-razonamiento]")
    analisis = meta.razonar_sobre_si_mismo()
    for tipo, contenido in analisis.items():
        print(f"  {tipo}: {contenido}")

    # Generar duda en texto
    print(f"\n[Expresión de duda]: '{meta.generar_duda_texto()}'")

    # Experimentar
    print("\n[Experimentación]")
    experimentador = Experimentador(ag, meta)
    for hipotesis in experimentador.priorizar_experimentos()[:3]:
        resultado, confianza = experimentador.simular_experimento(hipotesis)
        print(f"  '{hipotesis}': probable={resultado}, confianza={confianza:.2f}")

    print("\n=== METACOGNICIÓN FUNCIONANDO ===")