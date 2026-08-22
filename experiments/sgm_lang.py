#!/usr/bin/env python3
"""sgm_lang.py — Diccionario base + capa de lenguaje para SGM (Fase 10).

Objetivo (Luciano): que SGM vaya aprendiendo a comunicarse POCO A POCO de las
interacciones, implementandole un DICCIONARIO BASE minimo para arrancar (como un
bebe que aprende su lengua). El transformer propio (pequeño, numpy) traducira el
estado interno de SGM <-> tokens de lenguaje, CONDICIONADO por su estado (el
'equivalente a LoRA': como se expresa SGM cambia con lo que siente/valora/recuerda).

Este modulo contiene:
 1. DICCIONARIO BASE: el vocabulario minimo del mundo de SGM (tokens -> indice).
 2. Estado SGM -> tokens: serializa el mundo interno (valencia, recuerdo, necesidad,
    identidad, social) en una secuencia de tokens base (lo que SGM 'piensa decir').
 3. Vocabulario extensible: los tokens nuevos se agregan al aprender de interacciones.

NOTA: el transformer en si (matrices de atencion numpy) va en sgm_lang_modelo.py,
este solo define el vocabulario y la traduccion estado->tokens que el transformer usa.
"""
import numpy as np

# ---------- 1. DICCIONARIO BASE (vocabulario minimo del mundo SGM) ----------
# Palabras que SGM conoce desde su nacimiento (el "lenguaje base" que le damos).
# Son las raices de su mundo: recursos, estados, acciones, identidad.
DICCIONARIO_BASE = [
    # marcadores de estructura (necesarios para la sintaxis minima)
    "<sos>", "</sos>", "<pad>", "yo", "y", "pero", "porque",
    # recursos del mundo
    "comida", "madera", "mesa", "pico", "piedra", "hierro", "vaca",
    # estados internos
    "hambre", "veo", "recuerdo", "valoro", "evito", "tengo", "necesito", "quiero",
    "aprendi", "bien", "mal", "peligro", "zombie", "enemigo",
    # acciones / identidad
    "comer", "craftear", "explorar", "soy", "creo", "el otro", "sabe", "puede",
    # negacion / afirmacion
    "no", "si",
]
# agregar acciones/tokens numericos si se necesitan
DICCIONARIO_BASE += [f"acc_{i}" for i in range(17)]  # acciones posibles del agente

# indice por token
TOKEN2ID = {t: i for i, t in enumerate(DICCIONARIO_BASE)}
ID2TOKEN = {i: t for t, i in TOKEN2ID.items()}

SOS = TOKEN2ID["<sos>"]
EOS = TOKEN2ID["</sos>"]
PAD = TOKEN2ID["<pad>"]

VOCAB_SIZE = len(DICCIONARIO_BASE)


def token_a_id(token):
    """Token a indice. Si no existe (aprendido nuevo), lo agrega al vocabulario
    (extensible: SGM aprende palabras nuevas de las interacciones). Devuelve el indice.
    Es la forma de que el diccionario base CRECCA con el uso, sin recompilar."""
    if token not in TOKEN2ID:
        nuevo_id = len(DICCIONARIO_BASE)
        DICCIONARIO_BASE.append(token)
        TOKEN2ID[token] = nuevo_id
        ID2TOKEN[nuevo_id] = token
        return nuevo_id
    return TOKEN2ID[token]


def ids_a_tokens(ids):
    """Indices -> tokens (para decodificar la respuesta del transformer)."""
    return [ID2TOKEN[i] for i in ids if i != PAD and i != SOS and i != EOS]


# ---------- 2. ESTADO SGM -> TOKENS (lo que SGM 'piensa decir') ----------
def estado_a_tokens(ag, max_len=12):
    """Serializa el mundo interno del agente en una secuencia de tokens base.
    Es la 'oracion interna' de SGM: traduce su estado (valencia, recuerdo, necesidad,
    identidad, social) a la secuencia de palabras del diccionario base. El transformer
    luego aprende a convertir ESTA secuencia en algo que un humano entiende mejor.
    Devuelve (lista_de_tokens, lista_de_ids)."""
    toks = []
    # necesidad critica (lo mas urgente)
    if getattr(ag, "_hambre_real", 0) > 0.7:
        toks += ["tengo", "hambre", "necesito", "comida", "quiero", "comer"]
    # recuerdo saliente
    if ag.episodios and not toks:
        ep = ag.episodios[-1]
        if ep["recurso_nuevo"]:
            rec = [r for r in ep["recurso_nuevo"] if r in ("food","wood","stone","iron")]
            # mapear recurso ingles -> token espanol del diccionario base
            mapa = {"food":"comida", "wood":"madera", "stone":"piedra", "iron":"hierro"}
            if rec:
                toks += ["recuerdo", mapa.get(rec[0], rec[0]), "bien"]
    # valencia fuerte (preferencia/aversion)
    if not toks and ag.valencia_recurso:
        mejor = max(ag.valencia_recurso, key=ag.valencia_recurso.get)
        mapa = {"food":"comida", "wood":"madera", "stone":"piedra", "iron":"hierro"}
        if ag.valencia_recurso[mejor] > 1.0:
            toks += ["valoro", mapa.get(mejor, mejor)]
    # creencia social
    if not toks and ag.modelo_del_otro:
        conocido = [r for r, n in ag.modelo_del_otro.items() if n >= 2]
        if conocido:
            toks += ["creo", "el otro", "sabe", "craftear"]
    # fallback: identidad minima
    if not toks:
        toks += ["soy", "yo"]
    # truncar/pad a max_len
    ids = [SOS] + [token_a_id(t) for t in toks[:max_len]] + [EOS]
    return toks, ids


def estado_a_contexto_vector(ag, D=64):
    """Serializa el estado interno a un VECTOR numerico FIJO (la 'condicion' / LoRA-equiv).
    Este vector condiciona el transformer: como se expresa SGM depende de este vector.
    Features: [hambre, valencia media, n_episodios, valencia food, valencia wood,
    valencia stone, iron, n_social] normalizados a [0,1] aprox."""
    v = np.zeros(D)
    v[0] = min(1.0, getattr(ag, "_hambre_real", 0.0))          # necesidad
    vals = ag.valencia_recurso
    v[1] = min(1.0, max(0.0, sum(vals.values()) / 20.0))        # valencia global
    v[2] = min(1.0, len(ag.episodios) / 50.0)                    # memoria episodica
    v[3] = min(1.0, max(0.0, vals.get("food", 0) / 3.0))        # valencia food
    v[4] = min(1.0, max(0.0, vals.get("wood", 0) / 3.0))        # valencia wood
    v[5] = min(1.0, max(0.0, vals.get("stone", 0) / 3.0))       # valencia stone
    v[6] = min(1.0, max(0.0, vals.get("iron", 0) / 3.0))        # valencia iron
    v[7] = min(1.0, len(ag.modelo_del_otro) / 5.0)              # creencias sociales
    return v


# debug rapido
if __name__ == "__main__":
    print("VOCAB_SIZE (diccionario base):", VOCAB_SIZE)
    print("primeros tokens:", DICCIONARIO_BASE[:12])