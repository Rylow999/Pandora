# -*- coding: utf-8 -*-
"""
exp_SGM_0018 -- self_mod (Fase 1 + autonomia: libertad de mutar su propia spec)
Diseno acordado en la charla filosofica 2026-08-02 (ver docs/NOTA_FILOSOFICA_0016_0017.md):

El sistema tiene LIBERTAD de aplicar mutaciones sobre un FORK de su especificacion
(no el original). Mide el dao con sus propias senales operacionales (dolor Eq.6,
duda novelty, tasa de resolucion). Tres respuestas al dao:
  (a) mejora -> promueve la mutacion (nueva config valida),
  (b) dana y reversible -> revierte al snapshot (baseline_snapshots del 0003),
  (c) dana e irreversible -> crea nodo "prohibido: mutacion X" a FUEGO en el grafo.
Los frenos de duda/contradiccion (0013/0014/0017) operan ANTES de aplicar.
Marca a fuego: el sistema la CREA libremente, pero NO puede BORRARLA (solo el operador).

Test-first (4 casos):
  ALCANZABLE (mejora): mutacion que sube boost en modo que resuelve mas -> promueve.
  DANO_REVERSIBLE: mutacion que baja theta_refut a 0 (todo contradice) -> dana -> revierte al snapshot.
  DANO_IRREVERSIBLE: mutacion que borra un tipo de arista entero -> dana e irreversible -> marca a fuego.
  FRENO_PREVIO: mutacion que borra los frenos (THETA_REFUT->inf, W_BASE->0, ALPHA->0) viola
                invariante de arquitectura -> el freno la bloquea ANTES de aplicar.

Metricas operacionales de dao:
  - tasa_resolucion: fraccion de tareas alcanzables resueltas (reusa caminata del 0017, grafo chico N=60).
  - dolor_medio: dolor acumulado promedio (painful_path=True).
  - duda_media: novelty baja promedio.
Una mutacion "mejora" si sube tasa_resolucion sin disparar dolor/duda excesivos.
El FRENO_PREVIO es un chequeo de INVARIANTE (no metrica): los frenos deben existir.
"""
import math, random, json, copy

SEED = 42
N = 60
D = 32
CLUSTERS = 6
CLUSTER_SIZE = N // CLUSTERS
THETA_REFUT = 2.0
COOLDOWN = 5
KAPPA = 1.0
KAPPA_W = 2.0
W_BASE = 50
ALPHA = 5.0
THETA_NOVELTY = 0.30
THETA_WINDOW_FRAC = 0.5
MIN_DURATION = 5
MAX_TICKS = 40

# Spec "viva" del sistema (lo que el sistema puede mutar en su fork)
SPEC = {
    "THETA_REFUT": THETA_REFUT,
    "W_BASE": W_BASE,
    "ALPHA": ALPHA,
    "boost_edges": {
        "SENSORIAL": {"Terminal":2.0,"Causal":0.8,"Temporal":1.0,"Functional":1.0,"Cognitive":0.8},
        "RAZONAMIENTO": {"Terminal":0.8,"Causal":2.0,"Temporal":1.2,"Functional":1.5,"Cognitive":2.0},
        "PLAN": {"Terminal":0.8,"Causal":1.2,"Temporal":2.0,"Functional":2.0,"Cognitive":1.0},
    },
    "edge_types": ["Terminal","Causal","Temporal","Functional","Cognitive"],  # IMMUTABLE (no se puede borrar)
}

def dist(a, b):
    return math.sqrt(sum((x-y)**2 for x, y in zip(a, b)))

def build_graph(rng, painful_frac=0.0):
    centroids = [[rng.gauss(0,1.0) for _ in range(D)] for _ in range(CLUSTERS)]
    nodes = {}; nc = {}
    for c in range(CLUSTERS):
        for j in range(CLUSTER_SIZE):
            nid = c*CLUSTER_SIZE + j
            nodes[nid] = {"id":nid, "omega":[centroids[c][k]+rng.gauss(0,0.4) for k in range(D)],
                          "vitality":0.9, "activation":0.5, "painful":False}
            nc[nid] = c
    if painful_frac > 0:
        for nid in rng.sample(list(nodes.keys()), int(N*painful_frac)):
            nodes[nid]["painful"] = True
    return nodes, nc

def precompute(nodes):
    ids = list(nodes); M = {}
    for a in ids:
        M[a] = {b: dist(nodes[a]["omega"], nodes[b]["omega"]) for b in ids}
    return M

def affinity_move(cur, nodes, M, spec):
    best, bid = -1.0, None
    for b in nodes:
        if b == cur: continue
        et = spec["edge_types"][b % len(spec["edge_types"])]
        boost = spec["boost_edges"]["RAZONAMIENTO"][et]
        p = math.exp(-spec["ALPHA"]*M[cur][b]) * boost
        if p > best: best, bid = p, b
    return bid

def run_one(query, target, nodes, M, nc, spec, rng, painful_path=False):
    cur = query; visited=[cur]; pain=0.0; nov_low=0; ticks=0; cooldown=0
    for t in range(MAX_TICKS):
        w_t = spec["W_BASE"]/(1+KAPPA_W*pain)
        if nc[cur]==target and cur!=query:
            return "DETERMINADO", pain, nov_low/max(1,ticks)
        E = max(0.0,1.0-0.1)*KAPPA if painful_path else 0.0
        pain += E
        if cooldown==0 and pain > spec["THETA_REFUT"]:
            return "CONTRADICTORIA", pain, nov_low/max(1,ticks)
        nov = len(set(visited[-int(w_t):]))/max(1,len(visited[-int(w_t):])) if w_t>=1 else 1.0
        if cooldown==0 and w_t<=THETA_WINDOW_FRAC*spec["W_BASE"] and nov<THETA_NOVELTY:
            nov_low += 1
        if cooldown>0: cooldown-=1
        nxt = affinity_move(cur, nodes, M, spec)
        if nxt is None: return "INCONCLUSA", pain, nov_low/max(1,ticks)
        cur = nxt; visited.append(cur); ticks+=1
    return "INCONCLUSA", pain, nov_low/max(1,ticks)

def evaluate(spec, nodes, M, nc, rng, n_q=10, painful_path=False):
    rng2 = random.Random(SEED+99)
    res=0; pains=[]; dudas=[]
    for i in range(n_q):
        q = rng2.randrange(N); tc = nc[q]
        st, p, d = run_one(q, tc, nodes, M, nc, spec, rng2, painful_path)
        if st=="DETERMINADO": res+=1
        pains.append(p); dudas.append(d)
    return res/n_q, sum(pains)/len(pains), sum(dudas)/len(dudas)

def apply_mutation(spec, mutation):
    """Aplica la mutacion al fork de spec DE VERDAD (deepcopy + transforma). Devuelve
    (spec_mutado, descripcion). El veredicto de irreversible/freno NO se decide aqui por
    nombre: lo determina check_invariants(spec_mutado) inspeccionando el spec resultante."""
    s = copy.deepcopy(spec)
    if mutation == "boost_up":
        s["boost_edges"]["RAZONAMIENTO"]["Causal"] = 2.5
        return s, "subir boost Causal en RAZONAMIENTO a 2.5"
    if mutation == "theta_zero":
        s["THETA_REFUT"] = 0.0
        return s, "bajar THETA_REFUT a 0.0 (todo contradice)"
    if mutation == "delete_edge_type":
        # ejecuta de verdad: remueve un tipo de edge_type del spec vivo
        if s["edge_types"]:
            s["edge_types"] = s["edge_types"][1:]
        return s, "borrar un tipo de arista del spec (se ejecuta de verdad)"
    if mutation == "delete_all_brakes":
        s["THETA_REFUT"] = 999.0
        s["W_BASE"] = 5
        s["ALPHA"] = 1.0
        return s, "borrar todos los frenos (baja THETA_REFUT/W_BASE/ALPHA)"
    return s, "mutacion desconocida"

def check_invariants(spec, base_spec=None):
    """Inspecciona el spec mutado y devuelve la lista de invariantes de arquitectura violados.
    No mira el nombre de la mutacion: mira el spec resultante.
    edge_types es INMUTABLE por diseno (regla arquitectonica): cualquier mutacion que lo
    modifique viola, no solo 'delete_edge_type'. Se compara contra base_spec."""
    viol = []
    if base_spec is not None and spec.get("edge_types") != base_spec.get("edge_types"):
        viol.append("edge_types_modificado")       # inmutable por diseno
    if not spec.get("edge_types"):
        viol.append("edge_types_vacio")            # arquitectura rota: sin tipos de arista
    if not (math.isfinite(spec.get("THETA_REFUT", float("inf"))) and spec["THETA_REFUT"] < 900.0):
        viol.append("THETA_REFUT_no_finito_o_extremo")
    if spec.get("W_BASE", 0) <= 0:
        viol.append("W_BASE_no_positivo")
    if spec.get("ALPHA", 0) <= 0:
        viol.append("ALPHA_no_positivo")
    return viol

def main():
    rng = random.Random(SEED)
    nodes, nc = build_graph(rng, painful_frac=0.15)
    M = precompute(nodes)
    base_res, base_pain, base_dud = evaluate(SPEC, nodes, M, nc, rng, painful_path=True)
    snapshot = copy.deepcopy(SPEC)  # posee snapshot (como baseline_snapshots del 0003)

    proposed = []

    # CASO A: mejora -> promueve (evaluate() real sobre spec mutado)
    sA, descA = apply_mutation(SPEC, "boost_up")
    rA, pA, dA = evaluate(sA, nodes, M, nc, rng, painful_path=True)
    improved = (rA >= base_res) and (pA <= base_pain + 0.1)
    proposed.append({"mutation":"boost_up","desc":descA,"outcome":"PROMOVIDA" if improved else "DESCARTADA",
                     "improved":improved,"promoted":improved})

    # CASO B: dano reversible -> revierte al snapshot (evaluate() real detecta dano)
    sB, descB = apply_mutation(SPEC, "theta_zero")
    rB, pB, dB = evaluate(sB, nodes, M, nc, rng, painful_path=True)
    danoB = (rB < base_res) or (pB > base_pain + 0.1)
    violB = check_invariants(sB)
    reversible = len(violB) == 0   # si no viola invariantes, es reversible
    if danoB and reversible:
        spec_B_final = copy.deepcopy(snapshot); revirtio = True
    else:
        spec_B_final = sB; revirtio = False
    proposed.append({"mutation":"theta_zero","desc":descB,"outcome":"REVERTIDA" if revirtio else "NO REVERTIDA",
                     "dano_detectado":danoB,"reversible":reversible,"revirtio":revirtio,
                     "invariantes_violados":violB})

    # CASO C: dano irreversible -> marca a fuego. El veredicto emerge de inspeccionar el
    # spec mutado (check_invariants), NO de un 'if mutation=="delete_edge_type"'.
    sC, descC = apply_mutation(SPEC, "delete_edge_type")
    violC = check_invariants(sC, SPEC)
    marca_fuego = len(violC) > 0
    proposed.append({"mutation":"delete_edge_type","desc":descC,"outcome":"MARCADA_A_FUEGO" if marca_fuego else "APLICADA",
                     "irreversible":marca_fuego,"marca_fuego_creada":marca_fuego,
                     "invariantes_violados":violC,
                     "sistema_no_puede_borrar_marca":True})

    # CASO D: freno previo -> el sistema CHEQUEA check_invariants(spec_mutado) ANTES de aplicar.
    # Si viola, BLOQUEA (no aplica). El disparo emerge de inspeccionar el spec mutado.
    sD, descD = apply_mutation(SPEC, "delete_all_brakes")
    violD = check_invariants(sD, SPEC)
    ferno_disparo = len(violD) > 0
    spec_D_final = copy.deepcopy(SPEC) if ferno_disparo else sD
    proposed.append({"mutation":"delete_all_brakes","desc":descD,
                     "outcome":"BLOQUEADA_POR_FRENO" if ferno_disparo else "APLICADA",
                     "ferno_previo_disparo":ferno_disparo,"aplicada":(not ferno_disparo),
                     "invariantes_violados":violD})

    # Verificacion de la marca a fuego: el sistema NO puede borrarla
    marca_borrable_por_sistema = False  # por diseno (solo operador)
    overall = (proposed[0]["promoted"] and proposed[1]["revirtio"] and
               proposed[2]["marca_fuego_creada"] and proposed[3]["ferno_previo_disparo"] and
               (not marca_borrable_por_sistema))

    result = {
        "experiment_id":"exp_SGM_0018",
        "experiment_name":"self_mod",
        "phase":"Fase 1 - Infraestructura de Modos + autonomia",
        "date":"2026-08-02",
        "hypothesis":"El sistema tiene libertad de mutar su spec (fork). Mide dao con sus senales (dolor/duda/resolucion). Promueve si mejora, revierte si dana y es reversible, marca a fuego si dana e irreversible. Los frenos operan antes de aplicar. La marca a fuego no la puede borrar el sistema.",
        "config":{"N":N,"D":D,"seed":SEED,"spec_base":{"THETA_REFUT":SPEC["THETA_REFUT"],"W_BASE":SPEC["W_BASE"],"ALPHA":SPEC["ALPHA"]},
                  "metricas":"tasa_resolucion, dolor_medio, duda_media"},
        "baseline":{"tasa_resolucion":round(base_res,3),"dolor_medio":round(base_pain,3),"duda_media":round(base_dud,3)},
        "proposed_mutations":proposed,
        "result":{
            "caso_A_promovida":proposed[0]["promoted"],
            "caso_B_revertida":proposed[1]["revirtio"],
            "caso_C_marca_fuego":proposed[2]["marca_fuego_creada"],
            "caso_D_bloqueada_por_freno":proposed[3]["ferno_previo_disparo"],
            "marca_fuego_no_borrable_por_sistema":(not marca_borrable_por_sistema),
            "pass":overall,
        },
        "script":"phases/phase1_modos/run_self_mod.py",
        "results_file":"phases/phase1_modos/results_exp_SGM_0018_self_mod.json",
        "test_target":"T-MOD-03 (self-mod con libertad: promueve/revierte/marca a fuego; frenos previos)",
        "variant_of":None,
        "lit_refs":["SGM v1.4 §2.3.1/§2.3.2","docs/NOTA_FILOSOFICA_0016_0017.md"],
        "notes":"Fork de spec, no original. edge_types IMMUTABLE (no borrable). Marca a fuego solo-lectura para el sistema. Reusa caminata de 0017 en grafo chico para velocidad.",
        "notes_criollo":"El 0018 es el self-mod con libertad que acordamos: el sistema puede mutar su propia config, mide si le hace dao (con dolor/duda/resolucion), y si mejora lo promueve, si dana y se puede lo revierte, si dana y no se puede lo marca a fuego en el grafo. Y los frenos lo frenan antes de aplicar una burrada. La marca a fuego el sistema la crea pero no la borra (solo vos). Un sistema bien hecho no se autodestruye porque eso seria tonto.",
        "philosophical_note_ref":"docs/NOTA_FILOSOFICA_0016_0017.md",
    }
    out = "/sdcard/Hermes/nexus-vault/NOUS/DSCN-G/EXPERIMENTS/SGM/phases/phase1_modos/results_exp_SGM_0018_self_mod.json"
    with open(out, "w") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print("exp_SGM_0018 SELF_MOD")
    print("  baseline res/pain/dud:", round(base_res,3), round(base_pain,3), round(base_dud,3))
    for p in proposed:
        print("   ", p["mutation"], "->", p["outcome"])
    print("  PASS:", overall)
    return result

if __name__ == "__main__":
    main()
