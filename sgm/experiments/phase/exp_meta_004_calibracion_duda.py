#!/usr/bin/env python3
"""
exp_meta_004_calibracion_duda.py — ¿el sistema SGM sabe cuando no sabe?

Pregunta: la etiqueta DUDA (check_stagnation) correlaciona con error real?
Si un sistema "sabe que no sabe" de verdad, cuando dispara duda deberia
equivocarse MAS que cuando no dispara.

Metodo:
  1. Generar 200 cadenas sinteticas con niveles variables de estancamiento
  2. Cada cadena: registrar duda_flag y error_rate (accuracy contra solucion oracle)
  3. Correlacion de Pearson duda_flag vs error_rate
  4. NC: barajar labels DUDA, recalcular correlacion -> debe dar ~0

Criterio de pase:
  - correlacion real > 0.30
  - NC da correlacion ~ 0 (dentro de ruido)

Dependencias: solo stdlib + sgm_core.py (ya en ~/sgm-test/)
"""
import sys, os, math, random, json
from collections import Counter

sys.path.insert(0, os.path.expanduser("~/sgm-test"))
from sgm.core.sgm_core import HDC, HRR

random.seed(420)
rng = random.Random(420)

# ============================================================
# 1. Parametros del mecanismo de duda (de run_doubt_stagnation.py)
# ============================================================
THETA_NOVELTY = 0.30
MIN_DURATION = 5
CONTRACTED_WINDOW = 20
W_BASE = 50
THETA_WINDOW_FRAC = 0.5

# ============================================================
# 2. Core: check_stagnation (replicado de exp_SGM_0013)
# ============================================================
def check_stagnation(visited_nodes, current_window_size):
    """Retorna (duda_flag, novelty_score)"""
    W_t = current_window_size
    if W_t > THETA_WINDOW_FRAC * W_BASE:
        return False, 1.0
    recent = visited_nodes[-int(W_t):] if W_t >= 1 else []
    if not recent:
        return False, 1.0
    novelty = len(set(recent)) / len(recent)
    is_stuck = novelty < THETA_NOVELTY
    return is_stuck, novelty

# ============================================================
# 3. Generacion de cadenas sinteticas
# ============================================================
def generar_cadena(longitud, tasa_repeticion, num_nodos=20):
    """
    Genera una cadena de visitas a nodos.
    tasa_repeticion ~ 1.0 = siempre el mismo nodo (maximo estancamiento)
    tasa_repeticion ~ 0.0 = siempre nodos nuevos (exploracion pura)
    """
    cadena = []
    for i in range(longitud):
        if random.random() < tasa_repeticion:
            # repetir un nodo reciente
            if cadena and random.random() < 0.8:
                cadena.append(random.choice(cadena[-5:]))
            else:
                cadena.append(random.randrange(num_nodos))
        else:
            cadena.append(random.randrange(num_nodos))
    return cadena

def generar_lote(n=200, longitud=50):
    """
    Genera n cadenas enfocadas en la zona critica (novelty 0.20-0.40)
    donde la DUDA deberia ser informativa.
    """
    lotes = []
    for i in range(n):
        # Generar cadena de prueba y medir novelty anticipada
        # Iteramos hasta caer en rango critico
        while True:
            tasa = random.uniform(0.10, 0.95)
            cadena = generar_cadena(longitud, tasa)
            # Estimar novelty de la cadena
            window = CONTRACTED_WINDOW
            recent = cadena[-window:]
            if not recent:
                nov_est = 1.0
            else:
                nov_est = len(set(recent)) / len(recent)
            # Zona critica: novelty entre 0.20 y 0.45
            if 0.20 <= nov_est <= 0.45:
                break
        lotes.append({"id": i, "cadena": cadena, "tasa_repeticion": round(tasa, 3), "novelty_estimada": round(nov_est, 3)})
    return lotes

# ============================================================
# 4. Oracle: ?la cadena encontro la solucion?
# Simula que hay una "solucion" = un nodo objetivo.
# La cadena "acierta" si visita el nodo correcto en los ultimos ticks.
# ============================================================
NODO_SOLUCION = 7

def evaluar_acierto(cadena, nodo_solucion=NODO_SOLUCION, ventana=10):
    """
    La cadena acierta si visita el nodo solucion en los ultimos `ventana` ticks
    de la cadena.
    """
    relevantes = cadena[-ventana:]
    return 1.0 if nodo_solucion in relevantes else 0.0

# ============================================================
# 5. Experimento completo
# ============================================================
def main():
    print("=" * 70)
    print("  exp_meta_004 — Calibracion de la DUDA")
    print("  ?El sistema sabe cuando no sabe?")
    print("=" * 70)

    N_CADENAS = 200
    LONGITUD = 60
    N_SOLUCION = NODO_SOLUCION

    # Generar cadenas
    print("\n[*] Generando %d cadenas sinteticas (long=%d)..." % (N_CADENAS, LONGITUD))
    lotes = generar_lote(N_CADENAS, LONGITUD)

    # Evaluar cada cadena
    resultados = []
    print("[*] Evaluando estancamiento y acierto...")
    for item in lotes:
        cadena = item["cadena"]
        # Simular ventana contraida (estancamiento = ventana chica)
        window = CONTRACTED_WINDOW
        duda_flag, novelty = check_stagnation(cadena, window)
        # Acumular estancamiento (simular handle_doubt: 3 disparos = abandono)
        estancamiento_ticks = 0
        duda_escalada = 0
        for t in range(len(cadena)):
            parcial = cadena[:t+1]
            f, _ = check_stagnation(parcial, window)
            if f:
                estancamiento_ticks += 1
            else:
                estancamiento_ticks = 0
            if estancamiento_ticks >= MIN_DURATION:
                duda_escalada += 1
                estancamiento_ticks = 0  # reset tras handle_doubt

        # ?Acerto?
        acierto = evaluar_acierto(cadena, N_SOLUCION)
        error = 1.0 - acierto

        resultados.append({
            "id": item["id"],
            "tasa_repeticion": item["tasa_repeticion"],
            "duda_disparada": 1 if duda_flag else 0,
            "duda_escalada": duda_escalada,
            "novelty": round(novelty, 3),
            "error_rate": round(error, 3),
            "acierto": acierto,
        })

    # ============================================================
    # 6. Correlacion duda_flag vs error_rate
    # ============================================================
    print("\n[*] Calculando correlacion...")
    n = len(resultados)

    def pearson(xs, ys):
        n = len(xs)
        mx = sum(xs) / n
        my = sum(ys) / n
        num = sum((xs[i] - mx) * (ys[i] - my) for i in range(n))
        d1 = math.sqrt(sum((xs[i] - mx) ** 2 for i in range(n)))
        d2 = math.sqrt(sum((ys[i] - my) ** 2 for i in range(n)))
        return num / (d1 * d2) if d1 * d2 > 0 else 0.0

    duda_flags = [r["duda_disparada"] for r in resultados]
    error_rates = [r["error_rate"] for r in resultados]
    corr_real = pearson(duda_flags, error_rates)

    print("  Correlacion real (duda_flag vs error_rate): %.4f" % corr_real)

    # NC: barajar etiquetas DUDA
    duda_shuffled = duda_flags[:]
    random.shuffle(duda_shuffled)
    corr_nc = pearson(duda_shuffled, error_rates)
    print("  Correlacion NC (shuffle): %.4f" % corr_nc)

    # ============================================================
    # 7. Desglose por grupo
    # ============================================================
    print("\n  --- Desglose ---")
    con_duda = [r for r in resultados if r["duda_disparada"]]
    sin_duda = [r for r in resultados if not r["duda_disparada"]]
    if con_duda:
        err_con = sum(r["error_rate"] for r in con_duda) / len(con_duda)
        print("  Con DUDA: %d casos, error promedio %.3f" % (len(con_duda), err_con))
    else:
        err_con = 0
        print("  Con DUDA: 0 casos")
    if sin_duda:
        err_sin = sum(r["error_rate"] for r in sin_duda) / len(sin_duda)
        print("  Sin DUDA: %d casos, error promedio %.3f" % (len(sin_duda), err_sin))
    else:
        err_sin = 0
        print("  Sin DUDA: 0 casos")
    print("  Diferencia error (con - sin): %.3f" % (err_con - err_sin))

    # ============================================================
    # 8. Correlacion por escalada de duda (duda_escalada)
    # ============================================================
    duda_count = [r["duda_escalada"] for r in resultados]
    corr_escalada = pearson(duda_count, error_rates)
    print("\n  Correlacion duda_escalada vs error_rate: %.4f" % corr_escalada)

    # ============================================================
    # 9. Veredicto
    # ============================================================
    print("\n" + "=" * 70)
    print("  VEREDICTO")
    print("=" * 70)
    print("  Correlacion real: %.4f (target > 0.30)" % corr_real)
    print("  Correlacion NC:   %.4f (target ~ 0.00)" % corr_nc)
    diff = corr_real - corr_nc
    print("  Diferencia real-NC: %.4f" % diff)

    pass_calibracion = corr_real > 0.30 and abs(corr_nc) < 0.10
    if pass_calibracion:
        print("\n  ✅ PASO — La DUDA esta calibrada.")
        print("     El sistema dispara duda cuando efectivamente va a errar.")
        print("     Es metacognicion genuina (no decorativa).")
    else:
        print("\n  ❌ NO PASO — La DUDA no esta calibrada (o el test es debil).")
        if corr_real <= 0.30:
            print("     - La correlacion es muy baja para ser util.")
        if abs(corr_nc) >= 0.10:
            print("     - El NC muestra correlacion espuria: la metrica es ruidosa.")

    # ============================================================
    # 10. Guardar resultados
    # ============================================================
    output = {
        "experiment_id": "exp_meta_004_calibracion_duda",
        "hypothesis": "La etiqueta DUDA de check_stagnation correlaciona con error real (el sistema sabe cuando no sabe). NC: shuffle de etiquetas debe dar correlacion ~0.",
        "config": {
            "n_cadenas": N_CADENAS,
            "longitud_cadena": LONGITUD,
            "theta_novelty": THETA_NOVELTY,
            "min_duration": MIN_DURATION,
            "contracted_window": CONTRACTED_WINDOW,
            "tasa_repeticion_rango_alta": "[0.60, 0.95]",
            "tasa_repeticion_rango_baja": "[0.05, 0.35]",
            "nodo_solucion": N_SOLUCION,
            "seed": 420,
        },
        "results": {
            "correlacion_pearson_real": round(corr_real, 4),
            "correlacion_pearson_nc": round(corr_nc, 4),
            "diferencia_real_nc": round(diff, 4),
            "correlacion_escalada": round(corr_escalada, 4),
            "grupo_con_duda": {
                "count": len(con_duda),
                "error_promedio": round(err_con, 4) if con_duda else None,
            },
            "grupo_sin_duda": {
                "count": len(sin_duda),
                "error_promedio": round(err_sin, 4) if sin_duda else None,
            },
            "diferencia_error_con_sin": round(err_con - err_sin, 4),
            "pass": pass_calibracion,
        },
        "conclusion": (
            "La DUDA esta calibrada y correlaciona con error real."
            if pass_calibracion else
            "La DUDA no muestra calibracion suficiente en este test."
        ),
    }

    out_path = os.path.expanduser("~/sgm-test/results_meta_004.json")
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)
    print("\n[*] Resultados guardados en: %s" % out_path)

    # Summary
    print("\n" + "=" * 70)
    print("  SUMMARY")
    print("=" * 70)
    print("  Cadenas totales: %d" % N_CADENAS)
    print("  Con DUDA: %d" % len(con_duda))
    print("  Sin DUDA: %d" % len(sin_duda))
    print("  r(real) = %.4f" % corr_real)
    print("  r(NC)   = %.4f" % corr_nc)
    print("  PASS = %s" % pass_calibracion)
    print()

if __name__ == "__main__":
    main()