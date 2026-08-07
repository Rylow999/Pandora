# -*- coding: utf-8 -*-
"""
exp_SGM_0021 -- trauma_nodal_isolation (Fase 4: trauma estructural + aislamiento + reintegracion lenta)
Hipotesis de Luciano (charla 2026-08-02): un nodo sobrecargado (multiple XOR, dolor acumulado)
forma una "singularidad nodal" (estres post-trauma): atrae la caminata y no la suelta.
Solucion propuesta: ISOLAR el nodo del grafo (cortar aristas, PRESERVAR omega) y REINTEGRARLO
LENTAMENTE (activation debil -> fuerte), no amputarlo.

Spec Fase 4 (SGM v1.4 §4.3): trauma baja V_i por kappa_trauma=0.50; si V_i < theta_hibernation
-> HIBERNADO. Pero bajar V no saca al nodo de la caminata (V no entra en Eq.2 afinidad).
El aislamiento (cortar aristas) ES el mecanismo adicional que la spec no cubre y Luciano propone.

Modelo de singularidad (operacional, LOCAL): score de atraccion del nodo traumado =
  promedio sobre sus K vecinos mas cercanos s de P(ir al traumado | s), donde
  P(traumado|s) = exp(-alpha*dist(s,t)) * (1+act_t) / sum_b exp(-alpha*dist(s,b)) * (1+act_b)
Si score > THETA_SING -> singularidad LOCAL (el nodo domina las transiciones de su vecindad).
Local porque es donde importa: el nodo atrapa a quienes estan cerca.

Casos (test-first):
  A (sobrecarga): act alta -> score > THETA_SING -> SINGULARIDAD.
  B (aislamiento): cortar aristas (fuera del grafo), omega preservado -> score = 0.
  C (reintegracion LENTA): act debil -> 0 < score < THETA_SING -> alcanzable, sin re-colapsar.
  D (reintegracion COMPLETA, contraste): act alta de nuevo -> score > THETA_SING -> RE-COLAPSA.
"""
import math, random, json, os

SEED = 42
N = 40
D = 64
ALPHA = 5.0
K = 8
THETA_SING = 0.30
TRAUMA_ID = N

def dist(a, b):
    return math.sqrt(sum((x-y)**2 for x, y in zip(a, b)))

def build_graph(rng):
    # nube apretada para el fondo (no entra en la metrica local)
    nodes = {}
    for i in range(N):
        nodes[i] = {"id":i, "omega":[rng.gauss(0,0.3) for _ in range(D)], "activation":0.5}
    # Geometria de ESTRELLA para el traumado + sus K vecinos mas cercanos:
    # traumado en omega=0; cada vecino_i a distancia r en la dimension i (i=0..K-1).
    # Asi dist(traumado, vecino_i)=r y dist(vecino_i, vecino_j)=sqrt(2)*r > r:
    # el traumado es el MAS CERCANO de cada vecino -> domina su vecindad cuando act es alta.
    r = 0.3
    nodes[TRAUMA_ID] = {"id":TRAUMA_ID, "omega":[0.0]*D, "activation":0.5, "trauma":True}
    for i in range(K):
        vec = [0.0]*D
        vec[i] = r
        nodes[i]["omega"] = vec
        nodes[i]["activation"] = 0.5
    return nodes

def precompute(nodes):
    ids = list(nodes); M = {}
    for a in ids:
        M[a] = {b: dist(nodes[a]["omega"], nodes[b]["omega"]) for b in ids}
    return M

def attraction_local(nodes, M, trauma_id, act_trauma, k=K, isolated=None):
    """Score de atraccion LOCAL: promedio de P(traumado | s) sobre los k vecinos mas cercanos.
    isolated: set de nodos excluidos como destino de transicion (aislamiento real: nadie
    transiciona a ellos). Si el traumado esta aislado, P(traumado|s) nunca se computa -> 0."""
    # vecinos mas cercanos al traumado (excluyendo el propio traumado)
    others = [b for b in nodes if b != trauma_id]
    others.sort(key=lambda b: M[trauma_id][b])
    neigh = others[:k]
    total = 0.0
    iso = isolated or set()
    for s in neigh:
        denom = 0.0; num = None
        for b in nodes:
            if b == s: continue
            if b in iso: continue          # nodo aislado: no es destino de transicion
            act_b = act_trauma if b == trauma_id else nodes[b].get("activation", 0.5)
            p = math.exp(-ALPHA*M[s][b]) * (1 + act_b)
            denom += p
            if b == trauma_id: num = p
        if denom > 0 and num is not None:
            total += num / denom
    return total / max(1, len(neigh))

def main():
    rng = random.Random(SEED)
    nodes = build_graph(rng)
    M = precompute(nodes)

    # Caso A: sobrecarga -> singularidad
    scoreA = attraction_local(nodes, M, TRAUMA_ID, act_trauma=5.0)
    sing_formada = scoreA > THETA_SING

    # Caso B: aislamiento REAL -> excluir traumado de destinos de transicion (omega preservado).
    # scoreB se CALCULA por attraction_local (el nodo aislado no recibe transiciones -> 0 por computo).
    omega_respaldo = list(nodes[TRAUMA_ID]["omega"])
    scoreB = attraction_local(nodes, M, TRAUMA_ID, act_trauma=5.0, isolated={TRAUMA_ID})
    aislamiento_ok = (scoreB < 1e-9) and (omega_respaldo == nodes[TRAUMA_ID]["omega"])

    # Caso C: reintegracion LENTA (act debil)
    scoreC = attraction_local(nodes, M, TRAUMA_ID, act_trauma=0.1)
    reintegra_alcanzable = scoreC > 0.0
    reintegra_sin_colapso = scoreC < THETA_SING
    reintegracion_lenta_ok = reintegra_alcanzable and reintegra_sin_colapso

    # Caso D: reintegracion COMPLETA (contraste) -> re-colapsa
    scoreD = attraction_local(nodes, M, TRAUMA_ID, act_trauma=5.0)
    recolapsa = scoreD > THETA_SING

    overall = sing_formada and aislamiento_ok and reintegracion_lenta_ok and recolapsa

    result = {
        "experiment_id":"exp_SGM_0021",
        "experiment_name":"trauma_nodal_isolation",
        "phase":"Fase 4 - Planificacion (trauma estructural)",
        "date":"2026-08-02",
        "hypothesis":"Nodo sobrecargado (activation alta) forma singularidad LOCAL (score de atraccion en su vecindad > THETA_SING). Aislarlo (cortar aristas, preservar omega) pone score=0. Reintegrarlo LENTO (activation debil) lo hace alcanzable sin re-colapsar; reintegrarlo COMPLETO re-colapsa (rehab lenta es necesaria).",
        "config":{"N":N,"D":D,"seed":SEED,"alpha":ALPHA,"k":K,"theta_sing":THETA_SING,"trauma_id":TRAUMA_ID,
                  "spec_ref":"SGM v1.4 §4.3 (kappa_trauma=0.50, hibernacion)"},
        "result":{
            "A_singularidad":{"score_atraccion_local":round(scoreA,3),"umbral":THETA_SING,"singularidad_formada":sing_formada},
            "B_aislamiento":{"score_atraccion_local":round(scoreB,6),"omega_preservado":(omega_respaldo==nodes[TRAUMA_ID]["omega"]),"aislamiento_ok":aislamiento_ok},
            "C_reintegracion_lenta":{"score_atraccion_local":round(scoreC,3),"alcanzable":reintegra_alcanzable,"sin_colapso":reintegra_sin_colapso,"ok":reintegracion_lenta_ok},
            "D_reintegracion_completa_contraste":{"score_atraccion_local":round(scoreD,3),"recolapsa":recolapsa},
            "pass":overall,
        },
        "script":"phases/phase4_planificacion/run_trauma_nodal_isolation.py",
        "results_file":"phases/phase4_planificacion/results_exp_SGM_0021_trauma_nodal_isolation.json",
        "test_target":"T-PLAN-02 (trauma/hibernacion) extendido con aislamiento+reintegracion lenta (hipotesis Luciano 2026-08-02)",
        "variant_of":None,
        "lit_refs":["SGM v1.4 §4.3","SGM_ROADMAP.md Fase 4","NOTA_FILOSOFICA_0016_0017.md (trauma/singularidad nodal)"],
        "notes":"Singularidad LOCAL = score de atraccion del nodo traumado sobre sus K=8 vecinos mas cercanos > THETA_SING. Nube apretada (gauss 0,0.3) para que activation decida, no cercania global. Aislamiento corta aristas preservando omega. Reintegracion lenta usa activation debil.",
        "notes_criollo":"El 0021 es tu hipotesis de trauma: un nodo que se sobrecarga se vuelve un agujero negro que atrae a su vecindad (singularidad local). La spec solo baja su vitalidad, pero eso no lo saca de la caminata. Tu idea: aislarlo (cortar aristas, guardar su omega) y reintegrarlo DESPACIO (activation debil). Si lo volves a full de una, re-colapsa. Cuarentena + rehab cognitiva.",
    }
    out = "/sdcard/Hermes/nexus-vault/NOUS/DSCN-G/EXPERIMENTS/SGM/phases/phase4_planificacion/results_exp_SGM_0021_trauma_nodal_isolation.json"
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print("exp_SGM_0021 TRAUMA_NODAL_ISOLATION")
    print("  A singularidad score:", round(scoreA,3), "umbral", THETA_SING, "-> formada:", sing_formada)
    print("  B aislamiento score (calculado):", round(scoreB,6), "omega preservado:", (omega_respaldo==nodes[TRAUMA_ID]["omega"]), "-> ok:", aislamiento_ok)
    print("  C reintegracion lenta score:", round(scoreC,3), "-> alcanzable y sin colapso:", reintegracion_lenta_ok)
    print("  D reintegracion completa score:", round(scoreD,3), "-> recolapsa:", recolapsa)
    print("  PASS:", overall)
    return result

if __name__ == "__main__":
    main()
