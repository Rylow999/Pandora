#!/usr/bin/env python3
"""sgm_mundo.py — Repertorio de acciones Minecraft + grafo semantico del dominio (Fase 10).

Objetivo (Luciano): ensenar a SGM TODOS los movimientos/acciones que puede hacer en
Minecraft, con un diccionario de la lengua (grafo de conexiones) para que aprenda por
su cuenta + las interacciones del humano. Esta es la base que SGM usa para:
  1. Conocer su CATALOGO de acciones (repertorio) -> que pueda elegir cualquiera.
  2. Tener un GRAFO de conexiones entre conceptos del dominio -> que decoder_l2 (rol/
     contexto) rutee por el para generar/comprender mejor.
  3. Aprender de las interacciones (el transformer + reconciliacion).

Se integra suavemente con sgm_core (decoder_l2) y sgm_lang (diccionario).
El escalado (mas dimensiones D y nodos) se planea para la migracion a Rust.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

DICCIONARIO_ACCIONES_MC = [
    # movimiento
    "caminar_norte", "caminar_sur", "caminar_este", "caminar_oeste",
    "saltar", "agacharse",
    # interaccion con bloques
    "romper_arbol", "romper_piedra", "romper_hierro", "romper_tierra",
    "colocar_bloque", "romper_bloque",
    # recoleccion / crafteo
    "recoger_madera", "recoger_piedra", "recoger_comida",
    "craftear_mesa", "craftear_pico", "craftear_espada",
    # social / lenguaje
    "saludar", "expresarse", "seguir_humano",
    # defensa
    "atacar_zombie", "atacar_esqueleto", "huir",
]
# es tambien el 'vocabulario de acciones' que SGM conoce de su mundo

# GRAFO SEMANTICO DEL DOMINIO: conexiones entre conceptos del mundo de SGM.
# Es el 'diccionario con conexiones' que decoder_l2 rutea por rol. Formato:
#   nodo: lista de (vecino, rol) donde rol = tipo de relacion.
# Los roles permiten desambiguar por contexto (el rol R, no la palabra plana).
# Cobertura de supervivencia, recursos, herramientas, amenazas, social, lenguaje.
GRAFO_SEMANTICO = {
    # recursos
    "arbol": [("madera", "produce"), ("sombra", "ofrece")],
    "madera": [("herramienta", "es_material_de"), ("mesa", "permite_craftear")],
    "piedra": [("herramienta", "es_material_de")],
    "hierro": [("herramienta", "es_material_de"), ("mineral", "es")],
    "comida": [("vaca", "procede_de"), ("hambre", "quita")],
    "vaca": [("comida", "produce"), ("leche", "produce")],
    # herramientas -> capacidades
    "pico": [("romper_piedra", "habilita"), ("romper_hierro", "habilita")],
    "espada": [("atacar_zombie", "habilita"), ("defensa", "es")],
    "mesa": [("craftear_pico", "permite"), ("craftear_espada", "permite")],
    # instintos
    "hambre": [("comer", "necesita"), ("comida", "quita")],
    "peligro": [("huir", "provoca"), ("defensa", "necesita")],
    "zombie": [("peligro", "es"), ("atacar_zombie", "requiere")],
    "esqueleto": [("peligro", "es")],
    # estados internos (conecta con sgm_lang)
    "valoro": [("madera", "hacia"), ("pico", "hacia")],
    "recuerdo": [("comida", "de"), ("madera", "de")],
    "tengo": [("hambre", "estado"), ("madera", "inventario")],
    "necesito": [("comida", "para"), ("herramienta", "para")],
    # social / lenguaje (Fase 10)
    "humano": [("seguir_humano", "interactua_con"), ("expresarse", "se_comunica_con")],
    "expresarse": [("humano", "se_comunica_con"), ("estado_interno", "refleja")],
    "aprender": [("interaccion", "es_mecanismo"), ("grafo", "refina")],
    "grafo": [("decoder_l2", "lo_rutea"), ("conocimiento", "almacena")],
}

# ROlES (tipos de relacion) - el 'diccionario de la lengua' en cuanto a tipos de conexion
ROLES = sorted({r for vecinos in GRAFO_SEMANTICO.values() for _, r in vecinos})


def construir_grafo_ids():
    """Convierte el grafo semantico (nombres) a un grafo de IDs usable por decoder_l2.
    Devuelve (nodo_a_id, id_a_nombre, edges_ids, nombres_nodo).
    Incluye automaticamente los nodos que aparecen SOLO como vecinos (no como clave)."""
    import hashlib
    nodo_a_id = {}
    def _id_de(nombre):
        if nombre not in nodo_a_id:
            h = int(hashlib.md5(nombre.encode()).hexdigest(), 16) % 100000
            nodo_a_id[nombre] = h
        return nodo_a_id[nombre]
    # pasar por todas las claves Y vecinos
    for nodo in GRAFO_SEMANTICO:
        _id_de(nodo)
        for vec, _ in GRAFO_SEMANTICO[nodo]:
            _id_de(vec)
    id_a_nombre = {v: k for k, v in nodo_a_id.items()}
    edges = {}
    for nodo, vecinos in GRAFO_SEMANTICO.items():
        nid = _id_de(nodo)
        edges[nid] = [_id_de(vec) for vec, _ in vecinos]
    return nodo_a_id, id_a_nombre, edges, GRAFO_SEMANTICO


if __name__ == "__main__":
    print("Repertorio de acciones Minecraft:", len(DICCIONARIO_ACCIONES_MC))
    print("  ", DICCIONARIO_ACCIONES_MC)
    print("Grafo semantico del dominio:", len(GRAFO_SEMANTICO), "conceptos")
    print("Roles (tipos de conexion):", ROLES)
    na, ia, ed, g = construir_grafo_ids()
    print("Grafo a IDs: %d nodos, %d aristas" % (len(na), sum(len(v) for v in ed.values())))