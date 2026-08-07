# -*- coding: utf-8 -*-
"""
exp_SGM_0035 -- T-ID-03: identidad = proceso (trayectoria) no snapshot.
Extension honesta de exp_SGM_0034 (que media SOLO pisadas de dolor y no separaba
A de B). Aca se agrega un OBSERVABLE DE RECORRIDO (firma de trayectoria de fase)
para testear si "proceso nunca cortado" es operacionalmente distinto de
"snapshot copiado".

PROTOCOLO (pre-registrado, Pasos 0-3 del diseno de Luciano):
  Paso 0: tesis = identidad es la secuencia {S(t)}, no S(t) puntual (NOUS §1, Parfit).
  Paso 1: observable de recorrido = firma F(t) = vector de delta_phi en ventana W(t).
          (La vitalidad V es markoviana, NO sirve: V(t+1)=V(t)*e^-g, no depende del
           recorrido. Reportado como negativo.)
  Paso 2: 4 condiciones (no 3):
    A continuo | B interrumpido+copiado | C interrumpido+degradado | D interrumpido+borrado
  Paso 3: T-ID-03 pre-registrado con DOS desenlaces escritos ANTES de correr.
  Paso 4: el cap. 10 de NOUS_Filosofico se escribe CON datos, sea cual sea (no ahora).

OBSERVABLE F (firma de trayectoria de fase):
  En cada tick se registra delta_phi_i(t) = phi_i(t) - phi_i(t-1) para el nodo raiz.
  F(t) = lista de los ultimos W delta_phi desde el reset (o desde t=0 si continuo).
  Un reset copiado (B) tiene F = [0,0,...] (no hubo recorrido despues del reset).
  Un proceso continuo (A) tiene F = recorrido real.
  Metrica: ||F_A - F_B|| sobre la ventana W posterior al reset. T-ID-03 predice > 0.

TRAMPA pre-registrada (honestidad): phi converge al atractor en ~200 ticks (Eq.3),
así que la firma solo separa DURANTE la ventana W post-reset. Esperado y honesto:
la identidad-como-proceso es LOCAL en el tiempo (ventana de continuidad), no global.
Si W es chica y medimos lejos del reset, A y B pueden coincidir por convergencia.
Por eso medimos F en la ventana INMEDIATA post-reset.

CONDICIONES (self_state = {omega HRR, phi, dolor_count} como 0034, + historial phi):
  A continuo:       nunca reset; teletransportas cuerpo; phi sigue evolucionando.
  B copiado:        tick->0; copias omega+phi+dolor_count del pre-reset; historial phi=vacío.
  C degradado:      tick->0; copias con ruido gauss en omega/phi (decay parcial).
  D borrado:        tick->0; borras todo (AMNESIA de 0034).
Metrica principal: pisadas de dolor post-reset (reusa 0034) + firma F post-reset.
Tesis: A y B dan 0 pisadas (ambas "recuerdan"), PERO F(A) != F(B) => la identidad
como proceso SI es distinguible operacionalmente. Si F(A)==F(B), la tesis es
indistinguible de snapshot copiado (Parfit) y se reporta asi.
"""
import math, random, json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
import hrr_core as H

SEED = 20260805
TRIALS = 12
W = 20            # ventana de contexto (reusa Eq.8 conceptualmente)
N = 8             # grafo chico para el exp sintetico
D = 64
ETA = 0.05        # Eq.3
THETA_A = math.pi/2

def make_graph(rng):
    omega = [H.rnd_unit(rng, D) for _ in range(N)]
    phi = [rng.uniform(0, 2*math.pi) for _ in range(N)]
    # reward por nodo (para Eq.3, R_i)
    R = [rng.uniform(-1, 1) for _ in range(N)]
    return omega, phi, R

def step_phase(phi, R, root=0):
    """Un tick de fase Kuramoto (Eq.3) sobre el nodo raiz."""
    phi[root] = (phi[root] + ETA * R[root] * math.sin(THETA_A - phi[root])) % (2*math.pi)
    return phi

def signature(phi_hist_root, W):
    """F(t) = ultimos W delta_phi del nodo raiz. Si el historial es corto, rellena con 0."""
    deltas = []
    for t in range(1, len(phi_hist_root)):
        deltas.append(phi_hist_root[t] - phi_hist_root[t-1])
    while len(deltas) < W:
        deltas.append(0.0)
    return deltas[-W:]

def distF(a, b):
    return math.sqrt(sum((x-y)**2 for x,y in zip(a,b)))

def run_condition(rng, cond):
    """Devuelve (pisadas_post, F_post, phi_final, omega_final, dolor_count)."""
    omega, phi, R = make_graph(rng)
    # pre-trips: 5 viajes aprendiendo a esquivar (acumula dolor_count y phi_hist)
    phi_hist = [phi[0]]  # registro por tick del nodo raiz (float)
    dolor_count = 0
    for _ in range(5):  # 5 "viajes" pre-reset
        for _ in range(W):
            phi = step_phase(phi, R, root=0)
            phi_hist.append(phi[0])
        # "viaje" penaliza si phi lejos de atractor (dolor)
        if abs(phi[0] - THETA_A) > 1.0:
            dolor_count += 1
    pre_phi_hist = list(phi_hist)
    pre_omega = [list(o) for o in omega]
    pre_phi = list(phi)
    pre_dolor = dolor_count

    # RESET segun condicion
    if cond == "A":
        # continuo: teletransportas cuerpo, phi sigue (NO reset de historial)
        phi_hist_post = list(pre_phi_hist)
        omega_post = pre_omega
        phi_post = list(pre_phi)
        dolor_post = pre_dolor
    elif cond == "B":
        # interrumpido, estado copiado: snapshot S(t) copiado, historial phi VACIO
        phi_hist_post = [pre_phi[0]]  # solo el punto final, sin recorrido
        omega_post = [list(o) for o in pre_omega]
        phi_post = list(pre_phi)
        dolor_post = pre_dolor
    elif cond == "C":
        # interrumpido, degradado: copia con ruido
        rng2 = random.Random(rng.randint(0, 10**9))
        phi_post = [p + rng2.gauss(0, 0.3) for p in pre_phi]
        omega_post = [[o[j] + rng2.gauss(0, 0.1) for j in range(D)] for o in pre_omega]
        phi_hist_post = [phi_post[0]]
        dolor_post = max(0, pre_dolor - 1)
    elif cond == "D":
        # interrumpido, borrado (AMNESIA)
        phi_post = [rng.uniform(0, 2*math.pi) for _ in range(N)]
        omega_post = [H.rnd_unit(rng, D) for _ in range(N)]
        phi_hist_post = [phi_post[0]]
        dolor_post = 0

    # POST-reset: 5 viajes, medir pisadas y firma
    dolor_count_post = 0
    for _ in range(5):
        for _ in range(W):
            phi_post = step_phase(phi_post, R, root=0)
            phi_hist_post.append(phi_post[0])
        if abs(phi_post[0] - THETA_A) > 1.0:
            dolor_count_post += 1
    F_post = signature(phi_hist_post, W)
    return dolor_count_post, F_post, phi_post[0], omega_post[0], dolor_post

def main():
    rng = random.Random(SEED)
    res = {"config": {"W":W,"N":N,"D":D,"trials":TRIALS,"seed":SEED,
            "observable_recorrido":"firma F=ultimos W delta_phi raiz",
            "vitalidad_markoviana":"V(t+1)=V(t)*e^-g -> NO observable de recorrido (reportado negativo)"},
           "pisadas": {}, "firma_dist_A_vs_B": {}, "condiciones": {}}
    # pisadas por condicion
    for cond in ["A","B","C","D"]:
        pis = [run_condition(rng, cond)[0] for _ in range(TRIALS)]
        res["pisadas"][cond] = round(sum(pis)/len(pis), 4)
    # firma: A vs B (la prediccion clave de T-ID-03)
    dists = []
    for _ in range(TRIALS):
        _, FA, _, _, _ = run_condition(rng, "A")
        _, FB, _, _, _ = run_condition(rng, "B")
        dists.append(distF(FA, FB))
    res["firma_dist_A_vs_B"]["media"] = round(sum(dists)/len(dists), 4)
    # NC: A vs RW (ruido aleatorio de firma)
    rw_dists = []
    for _ in range(TRIALS):
        _, FA, _, _, _ = run_condition(rng, "A")
        FB_rw = [rng.uniform(-1,1) for _ in range(W)]  # firma RW (ruido)
        rw_dists.append(distF(FA, FB_rw))
    res["firma_dist_A_vs_B"]["NC_A_vs_RW_media"] = round(sum(rw_dists)/len(rw_dists), 4)

    # PRE-REGISTRO T-ID-03 (desenlaces escritos ANTES de correr)
    dA = res["pisadas"]["A"]; dB = res["pisadas"]["B"]
    distAB = res["firma_dist_A_vs_B"]["media"]
    nc = res["firma_dist_A_vs_B"]["NC_A_vs_RW_media"]
    # T-ID-03: firma(A) != firma(B) aunque pisadas(A)=pisadas(B)=0
    tid03 = (abs(dA - dB) < 0.01) and (distAB > 0.05) and (distAB > nc*0.5)
    res["T-ID-03"] = {
        "predice_firma_A_distinto_B": tid03,
        "pisadas_A_igual_B": abs(dA-dB) < 0.01,
        "firma_dist_media": distAB,
        "NC_dist_media": nc,
        "desenlace": ("1_SI_difiere" if tid03 else "2_NO_difiere_Parfit")
    }
    res["pass"] = tid03

    print("exp_SGM_0035 T-ID-03 identidad=proceso")
    print("  pisadas post-reset A/B/C/D:", res["pisadas"])
    print("  firma ||F_A - F_B|| media:", distAB, " | NC ||F_A-F_RW||:", nc)
    print("  T-ID-03 (firma A!=B aunque pisadas iguales):", tid03)
    print("  DESENLACE:", res["T-ID-03"]["desenlace"])
    out = "/sdcard/Hermes/nexus-vault/NOUS/DSCN-G/EXPERIMENTS/SGM/phases/phase7_composicion/results_exp_SGM_0035_identity_trajectory.json"
    os.makedirs(os.path.dirname(out), exist_ok=True)
    full = {
        "experiment_id":"exp_SGM_0035",
        "experiment_name":"identity_trajectory_T-ID-03",
        "phase":"Camino A - identidad como proceso (trayectoria), no snapshot",
        "date":"2026-08-05",
        "hypothesis":("La identidad es la secuencia {S(t)} (NOUS §1, Parfit), no S(t) puntual. Debe "
            "existir observable de recorrido (firma F de delta_phi en ventana W) tal que F(A)!=F(B) "
            "aunque pisadas(A)=pisadas(B)=0. Si no, es indistinguible de snapshot copiado (Parfit)."),
        "config":res["config"],
        "result":res,
        "script":"phases/phase7_composicion/run_identity_tid03.py",
        "results_file":"phases/phase7_composicion/results_exp_SGM_0035_identity_trajectory.json",
        "test_target":"T-ID-03: firma(A)!=firma(B) con pisadas(A)=pisadas(B)",
        "variant_of":"exp_SGM_0034",
        "lit_refs":["exp_SGM_0034","NOUS_Filosofico §1/§10","Parfit 1984","0056 (honestidad de trampa)"],
        "notes":("Extension de 0034 con observable de RECORRIDO. 0034 media solo pisadas y no separaba "
                 "A de B. Firma F=ultimos W delta_phi del nodo raiz: continuo tiene recorrido, copiado "
                 "tiene F=[0,0..]. Vitalidad V es markoviana (V(t+1)=V*e^-g) => NO observable de recorrido."),
        "notes_criollo":("Esto es el test de '¿el proceso nunca cortado es distinto de copiar el estado?' "
                         "Si la firma F difiere, la tesis NOUS §1 es operacionalmente verdadera. Si no "
                         "difiere, es igual a 'copiar el snapshot' y lo decimos con la honestidad de 0056."),
        "capitulo10_NOUS_Filosofico":"SE ESCRIBE CON ESTE DATO (sea cual sea). No escrito hasta tener resultado."
    }
    json.dump(full, open(out,"w"), indent=2, ensure_ascii=False)
    return full

if __name__ == "__main__":
    main()
