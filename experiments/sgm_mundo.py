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

# DICCIONARIO ANCLADO AL MUNDO DE MINECRAFT (Luciano: relacionar mundo con lenguaje).
# Cada ACCION y cada OBJETO/BLOQUE/ENTIDAD del juego con sus palabras espanolas + sinonimos.
# Esto es lo que permite a SGM vincular lenguaje <-> mundo: "rompe el arbol" ->
#   action "romper" + objeto "arbol"(arbol,roble,tronco,oak) + relacion "romper_arbol -> madera".
# Y usar la SINTAXIS (sujeto/verbo/objeto) + el grafo para entender de verdad.
DICCIONARIO_MUNDO_MC = {
    # ------- ACCIONES: palabra -> accion del repertorio -------
    "acciones": {
        "mover": ["mover", "moverse", "caminar", "andar", "ir", "desplazar", "venir", "acercarse", "seguir", "vete", "anda"],
        "saltar": ["saltar", "brincar", "salta"],
        "romper": ["romper", "quebrar", "destruir", "talar", "picar", "minar", "rompe", "rompé", "tala", "tirá"],
        "colocar": ["colocar", "poner", "construir", "coloca", "poné", "construí"],
        "recolectar": ["recolectar", "recoger", "juntar", "cosechar", "reunir", "obtener", "recolecta", "recogé", "cosecha"],
        "craftear": ["craftear", "fabricar", "crear", "hacer", "elaborar", "craftea", "fabricá"],
        "atacar": ["atacar", "pegar", "golpear", "dañar", "matar", "defender", "atacá", "pega", "matá"],
        "comer": ["comer", "alimentarse", "tomar", "ingerir", "devorar", "come", "comé", "como", "comer"],
        "explorar": ["explorar", "buscar", "investigar", "recorrer", "descubrir", "explora", "busca", "recorre"],
        "huir": ["huir", "escapar", "correr", "alejarse", "retirarse", "esquivar", "huí", "escape", "corré"],
    },
    # ------- OBJETOS / BLOQUES / RECURSOS -------
    "objetos": {
        "arbol": ["arbol", "roble", "tronco", "oak", "madera_natural", "planta", "bosque"],
        "madera": ["madera", "tabla", "leña", "tronco_transformado", "wood"],
        "piedra": ["piedra", "roca", "mineral", "canto", "stone"],
        "hierro": ["hierro", "metal", "mineral_de_hierro", "iron"],
        "comida": ["comida", "alimento", "carne", "fruta", "manzana", "pan", "bizcocho"],
        "mesa": ["mesa", "mesa_de_crafteo", "crafting", "banco_de_trabajo", "workbench"],
        "herramienta": ["herramienta", "pico", "espada", "hacha", "azada", "pala"],
        "pico": ["pico", "pico_de_piedra", "pico_de_madera", "pickaxe"],
        "espada": ["espada", "arma", "sword"],
        "bloque": ["bloque", "cubo", "bloque_de_oro", "bloque_de_hierro"],
    },
    # ------- ENTIDADES / CRIATURAS / JUGADOR -------
    "entidades": {
        "vaca": ["vaca", "res", "juvenil"],
        "cerdo": ["cerdo", "chancho", "cerdito"],
        "pollo": ["pollo", "gallina", "pollo_muerto"],
        "zombie": ["zombie", "zombi", "muerto_viviente", "monstruo", "enemigo", "no_vivo"],
        "esqueleto": ["esqueleto", "huesos_vivientes", "esquelet", "monstruo"],
        "creeper": ["creeper", "explosivo", "verde", "monstruo_explosivo"],
        "araña": ["araña", "arana", "monstruo"]
    },
}

# SINTAXIS: tipos de palabra / roles. SGM usa estos para distinguir SUJETO/VERBO/OBJETO
# y CONECTORES, de modo que "yo rompo arbol" != "arbol rompe yo".
TIPOS_PALABRA = {
    "verbo": ["romper", "mover", "comer", "recoger", "craftear", "atacar", "colocar", "saltar", "explorar", "huir"],
    "sujeto": ["yo", "el", "ella", "sgm", "tu", "vos", "usted", "jugador", "humano"],
    "objeto_mundo": ["arbol", "madera", "piedra", "hierro", "comida", "mesa", "herramienta", "pico",
                     "espada", "bloque", "vaca", "cerdo", "pollo", "zombie", "esqueleto", "creeper", "araña"],
    "conector": ["el", "la", "los", "las", "un", "una", "de", "a", "hacia", "y", "para", "en"],
}


def palabra_a_accion(palabra):
    """Mapea una palabra espanola a la ACCION del repertorio (via DICCIONARIO_MUNDO_MC).
    Devuelve el nombre de accion (p.ej. 'romper') o None si la palabra no es una accion."""
    p = palabra.lower()
    for accion, palabras in DICCIONARIO_MUNDO_MC["acciones"].items():
        if p in palabras or p == accion:
            return accion
    return None


def palabra_a_objeto(palabra):
    """Mapea una palabra espanola a un OBJETO/recurso/entidad del mundo.
    Devuelve el nombre canonico (p.ej. 'arbol') o None si no es un objeto conocido."""
    p = palabra.lower()
    for cat in ("objetos", "entidades"):
        for obj, palabras in DICCIONARIO_MUNDO_MC[cat].items():
            if p in palabras or p == obj:
                return obj
    return None


def analizar_instruccion(texto):
    """SINTAXIS esencial: descompone una instruccion en (accion, objeto, sujeto).
    Ej: "rompe el arbol del bosque" -> (accion='romper', objeto='arbol', sujeto=None).
    Usa DICCIONARIO_MUNDO_MC + TIPOS_PALABRA. Devuelve un dict {accion, objeto, sujeto,
    conectores, palabras_no_reconocidas}."""
    import re as _re
    palabras = _re.findall(r"[a-záéíóúñ]+", texto.lower())
    accion, objeto, sujeto = None, None, None
    para_palabra = TIPOS_PALABRA
    for p in palabras:
        # acciones
        if accion is None:
            accion = palabra_a_accion(p)
        # objetos del mundo
        if objeto is None:
            objeto = palabra_a_objeto(p)
        # sujetos
        if p in para_palabra["sujeto"]:
            sujeto = p
    return {"accion": accion, "objeto": objeto, "sujeto": sujeto,
            "palabras": palabras}

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