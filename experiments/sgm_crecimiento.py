#!/usr/bin/env python3
"""sgm_crecimiento.py — CRECIMIENTO LIBRE de Pandora.

El sistema crea conceptos, acciones y conexiones libremente a través de su
experiencia en el mundo. No hardcodea todo — aprende y crea dinámicamente.

Alineado con el documento PURE-L2: "el grafo evoluciona libremente (aprender de
internet sin filtro)" y "el decodificador L2 sea entrenado y curado académicamente".
"""
import sys, os, random, hashlib
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import importlib, sgm_core; importlib.reload(sgm_core)
from sgm_core import SGMAgent
from sgm_lang import TOKEN2ID, ID2TOKEN, token_a_id


class CreadorConceptos:
    """Crea nuevos conceptos (nodos) en el grafo a partir de la experiencia.
    Cada nueva palabra, objeto o acción que Pandora encuentra se convierte
    en un nodo del grafo con su propio omega (vector semántico)."""

    def __init__(self, agente):
        self.agente = agente

    def crear_concepto(self, nombre, contexto=None):
        """Crea un nuevo nodo-concepto en el grafo.
        nombre: string (p.ej. 'diamond', 'misterioso', 'saltar_al_vacio')
        contexto: lista de palabras cercanas (para el omega inicial)
        Devuelve el ID del nuevo nodo."""
        # Verificar si ya existe
        if nombre in TOKEN2ID:
            return TOKEN2ID[nombre]

        # Crear token en el diccionario
        token_id = token_a_id(nombre)

        # Crear nodo en el grafo
        nuevo_id = len(self.agente.omega)
        D = self.agente.D

        # Omega inicial: ruido + influencia del contexto
        omega = [random.gauss(0, 0.1) for _ in range(D)]
        if contexto:
            for palabra in contexto:
                if palabra in TOKEN2ID:
                    # Influencia de palabras cercanas
                    influencia = 0.3
                    for i in range(D):
                        omega[i] += influencia * random.gauss(0, 1)

        # Normalizar
        norma = sum(x*x for x in omega) ** 0.5
        if norma > 0:
            omega = [x / norma for x in omega]

        # Agregar al grafo
        self.agente.omega.append(omega)
        self.agente.vitalidad.append(0.5)
        self.agente.edges[nuevo_id] = []
        self.agente.phi.append(random.uniform(0, 6.28))
        self.agente.resolucion_nivel.append(0)
        self.agente.scope_depth.append(0)

        # Conectar con palabras del contexto
        if contexto:
            for palabra in contexto:
                if palabra in TOKEN2ID:
                    vecino_id = TOKEN2ID[palabra]
                    if vecino_id < len(self.agente.omega) - 1:
                        self.agente.edges[nuevo_id].append(vecino_id)
                        self.agente.edges[vecino_id].append(nuevo_id)

        return nuevo_id

    def aprender_experiencia(self, palabras, intensidad=1.0):
        """Aprende de una experiencia: crea/actualiza nodos y conexiones.
        palabras: lista de palabras que aparecieron juntas en una experiencia.
        intensidad: qué tan fuerte es esta experiencia (0-1).
        """
        # Crear nodos para palabras nuevas
        ids = []
        for palabra in palabras:
            if palabra not in TOKEN2ID:
                nid = self.crear_concepto(palabra, contexto=[p for p in palabras if p != palabra])
                ids.append(nid)
            else:
                ids.append(TOKEN2ID[palabra])

        # Crear conexiones entre todas las palabras de la experiencia
        for i in range(len(ids)):
            for j in range(i + 1, len(ids)):
                if ids[j] not in self.agente.edges.get(ids[i], []):
                    if ids[i] not in self.agente.edges:
                        self.agente.edges[ids[i]] = []
                    self.agente.edges[ids[i]].append(ids[j])
                    if ids[j] not in self.agente.edges:
                        self.agente.edges[ids[j]] = []
                    self.agente.edges[ids[j]].append(ids[i])

        # Reforzar omega de los nodos involucrados
        for nid in ids:
            if nid < len(self.agente.omega):
                refuerzo = 0.1 * intensidad
                for k in range(self.agente.D):
                    self.agente.omega[nid][k] += refuerzo * random.gauss(0, 1)
                # Normalizar
                norma = sum(x*x for x in self.agente.omega[nid]) ** 0.5
                if norma > 0:
                    self.agente.omega[nid] = [x / norma for x in self.agente.omega[nid]]


class CreadorAcciones:
    """Crea nuevas acciones dinámicamente a partir de la experiencia.
    Las acciones no son hardcodeadas — emergen de lo que Pandora hace."""

    def __init__(self, agente):
        self.agente = agente
        self.acciones_aprendidas = {}

    def registrar_accion(self, nombre, contexto, resultado):
        """Registra una nueva acción aprendida.
        nombre: string (p.ej. 'talar_arbol', 'esquivar_zombie')
        contexto: lista de condiciones (palabras)
        resultado: lista de consecuencias (palabras)
        """
        self.acciones_aprendidas[nombre] = {
            "contexto": contexto,
            "resultado": resultado,
            "exitos": 1,
            "fracasos": 0
        }

        # Crear nodos para la acción y sus componentes
        for palabra in contexto + resultado:
            if palabra not in TOKEN2ID:
                token_a_id(palabra)

    def elegir_accion(self, estado_actual):
        """Elige una acción basada en el estado actual y lo aprendido.
        estado_actual: lista de palabras que describen el estado.
        Devuelve el nombre de la acción o None."""
        mejor_accion = None
        mejor_score = 0

        for nombre, datos in self.acciones_aprendidas.items():
            # Score: cuánto coincide el contexto con el estado actual
            coincidencias = sum(1 for c in datos["contexto"] if c in estado_actual)
            score = coincidencias / max(1, len(datos["contexto"]))
            score *= (datos["exitos"] / max(1, datos["exitos"] + datos["fracasos"]))

            if score > mejor_score:
                mejor_score = score
                mejor_accion = nombre

        return mejor_accion if mejor_score > 0.3 else None


class CreadorLenguaje:
    """Crea lenguaje libremente a partir del estado interno.
    No usa plantillas — genera frases desde el grafo."""

    def __init__(self, agente):
        self.agente = agente

    def expresarse(self, estado, max_palabras=5):
        """Genera una expresión basada en el estado interno.
        estado: dict con hambre, amenaza, curiosidad, etc.
        Devuelve una lista de palabras."""
        palabras = []

        # Hambre
        if estado.get("hambre", 0) > 0.6:
            palabras.extend(self._buscar_relacionados("hambre", 2))

        # Amenaza
        if estado.get("amenaza", 0) > 0.5:
            palabras.extend(self._buscar_relacionados("peligro", 2))

        # Curiosidad
        if estado.get("curiosidad", 0) > 0.7:
            palabras.extend(self._buscar_relacionados("explorar", 2))

        # Si no hay nada, expresar estado base
        if not palabras:
            palabras = ["estoy", "aqui"]

        return palabras[:max_palabras]

    def _buscar_relacionados(self, palabra, max_relacionados=2):
        """Busca palabras relacionadas en el grafo."""
        if palabra not in TOKEN2ID:
            return [palabra]

        token_id = TOKEN2ID[palabra]
        vecinos = self.agente.edges.get(token_id, [])
        relacionados = []

        for vecino_id in vecinos[:max_relacionados]:
            if vecino_id in ID2TOKEN:
                relacionados.append(ID2TOKEN[vecino_id])

        return relacionados if relacionados else [palabra]


if __name__ == "__main__":
    print("=== DEMO: CRECIMIENTO LIBRE DE PANDORA ===")
    ag = SGMAgent(random.Random(42), 128, n_nodes=64, gamma=0.01)
    ag.set_edges({i: random.sample(range(64), min(5, 63)) for i in range(64)})

    creador = CreadorConceptos(ag)

    # Simular experiencias
    experiencias = [
        (["tala", "arbol", "madera"], 1.0),
        (["mata", "zombie", "carne"], 0.8),
        (["mina", "piedra", "carbon"], 0.9),
        (["craftea", "mesa", "pico"], 0.7),
        (["explora", "cueva", "diamante"], 1.0),
    ]

    for palabras, intensidad in experiencias:
        creador.aprender_experiencia(palabras, intensidad)
        print(f"  Experiencia: {palabras} -> nodos creados")

    print(f"\nNodos del grafo: {len(ag.omega)}")
    print(f"Tamaño diccionario: {len(TOKEN2ID)}")

    # Crear acción
    accion_creator = CreadorAcciones(ag)
    accion_creator.registrar_accion("talar_arbol", ["arbol", "cerca"], ["madera", "obtenida"])
    accion_creator.registrar_accion("defender_zombie", ["zombie", "cerca", "peligro"], ["atacar", "defender"])

    accion = accion_creator.elegir_accion(["arbol", "cerca"])
    print(f"\nAcción elegida (arbol cerca): {accion}")

    accion = accion_creator.elegir_accion(["zombie", "cerca", "peligro"])
    print(f"Acción elegida (zombie cerca): {accion}")

    # Expresarse
    lenguaje = CreadorLenguaje(ag)
    estado = {"hambre": 0.8, "amenaza": 0.0, "curiosidad": 0.5}
    frase = lenguaje.expresarse(estado)
    print(f"\nExpresión (hambre alta): {frase}")

    estado = {"hambre": 0.2, "amenaza": 0.8, "curiosidad": 0.3}
    frase = lenguaje.expresarse(estado)
    print(f"Expresión (peligro alto): {frase}")

    print("\n=== CRECIMIENTO LIBRE FUNCIONANDO ===")