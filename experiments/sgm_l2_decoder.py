#!/usr/bin/env python3
"""sgm_l2_decoder.py — DECODIFICADOR L2 (PURE-L2): proyeccion lineal aprendida.

El documento Arquitectura_Pure_L2_Pandora.md (§4.5) define L2 como la separacion radical
entre CONOCIMIENTO (el grafo SGM, que evoluciona libremente) y DECODIFICACION (esta capa
entrenada offline/online que traduce vemántico a tokens):

    p_i = softmax(W · t_i + b)    donde t_i = omega_i * I_i (token semántico escalado)

W ∈ ℝ^(V×D_sem), b ∈ ℝ^V, omega ∈ ℝ^D_sem, I_i = interferencia del nodo.

El decodificador se entrena INDEPENDIENTE del grafo: el grafo aprende el significado,
el decodificador aprende la VOZ (qué tonalidad, qué palabras usar). Esto permite que el
grafo evolucione libremente (aprender de internet, de Minecraft, de Luciano) mientras el
mantiene una voz curada/coherente.

Implementacion: numpy puro (sin torch), entrenable online con backprop simple.
Formato: pesos se guardan/cargan en .npz.
"""
import sys, os, math, random
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sgm_lang import TOKEN2ID, ID2TOKEN

import numpy as np


class L2Decoder:
    """Decodificador L2: proyeccion lineal W·omega + b -> softmax -> token.

    Entrenable online con pares (omega, token_id) — cuando Pandora produce un mensaje
    y recibe feedback, ajusta W para que ese omega produzca ese token."""

    def __init__(self, D_sem=128, vocab_size=None, lr=0.01, ruta_pesos=None):
        self.D = D_sem
        self.vocab_size = vocab_size or len(TOKEN2ID)
        self.lr = lr
        self.ruta_pesos = ruta_pesos or os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "l2_decoder.npz")
        # W: [V, D], b: [V]
        self.W = np.random.randn(self.vocab_size, self.D) * 0.01
        self.b = np.zeros(self.vocab_size)
        self._cargar()

    def forward(self, omega):
        """Dado un vector semántico omega [D], devuelve distribución sobre tokens.
        p = softmax(W·omega + b) — la probabilidad de cada token dado el estado."""
        logits = self.W.dot(omega) + self.b  # [V]
        # softmax numéricamente estable
        logits -= np.max(logits)
        exp = np.exp(logits)
        probs = exp / np.sum(exp)
        return probs

    def decodificar(self, omega, topk=1, temperatura=1.0):
        """Decodifica omega a token(es). Devuelve lista de (token_id, prob).
        temperatura < 1 = más determinista, > 1 = más exploratorio."""
        probs = self.forward(omega)
        if temperatura != 1.0:
            # escalar logits por temperatura
            logits = np.log(probs + 1e-12) / temperatura
            logits -= np.max(logits)
            exp = np.exp(logits)
            probs = exp / np.sum(exp)
        # top-k
        top_idx = np.argsort(probs)[-topk:][::-1]
        return [(int(idx), float(probs[idx])) for idx in top_idx]

    def entrenar(self, omega, token_id, lr=None):
        """Un paso de entrenamiento: ajusta W para que omega produzca token_id.
        Loss = -log p(token_id | omega). Backprop simple (softmax + cross-entropy)."""
        lr = lr or self.lr
        probs = self.forward(omega)
        # gradiente de cross-entropy: dL/dlogits = probs - one_hot
        dlogits = probs.copy()
        dlogits[token_id] -= 1.0
        # gradientes de W y b
        # dL/dW[j,i] = dlogits[j] * omega[i]
        # dL/db[j] = dlogits[j]
        self.W -= lr * np.outer(dlogits, omega)  # [V, D]
        self.b -= lr * dlogits  # [V]
        # devolver loss para monitoreo
        return -math.log(probs[token_id] + 1e-12)

    def entrenar_secuencia(self, omegas, token_ids, lr=None):
        """Entrena sobre una secuencia de (omega, token_id). Devuelve loss promedio."""
        losses = []
        for omega, tid in zip(omegas, token_ids):
            loss = self.entrenar(omega, tid, lr)
            losses.append(loss)
        return np.mean(losses) if losses else 0.0

    def guardar(self):
        """Guarda pesos en .npz."""
        np.savez(self.ruta_pesos, W=self.W, b=self.b,
                 D=self.D, vocab_size=self.vocab_size)
        return self.ruta_pesos

    def _cargar(self):
        """Carga pesos si existen."""
        if os.path.exists(self.ruta_pesos):
            try:
                data = np.load(self.ruta_pesos, allow_pickle=True)
                if 'W' in data and 'b' in data:
                    self.W = data['W']
                    self.b = data['b']
            except Exception:
                pass  # si hay error, usar inicialización aleatoria


def generar_mensaje_l2(decoder, palabras_activas, max_len=6):
    """Genera un mensaje completo usando el decodificador L2.
    palabras_activas: lista de (omega, interferencia) — los nodos activos del grafo.
    Devuelve una lista de strings (tokens).

    Segun el documento: cada nodo relevante emite un 'token semántico' t_i = omega_i * I_i.
    L2 proyecta cada t_i a una distribución sobre el vocabulario.
    Los N tokens se ordenan por interferencia decreciente y se concatenan."""
    if not palabras_activas:
        return []
    # ordenar por interferencia decreciente (los más relevantes primero)
    palabras_activas.sort(key=lambda x: -x[1])
    tokens_generados = []
    for omega, interferencia in palabras_activas[:max_len]:
        t_i = omega * interferencia  # token semántico escalado por interferencia
        top = decoder.decodificar(t_i, topk=1, temperatura=0.8)
        if top:
            token_id = top[0][0]
            token = ID2TOKEN.get(token_id, "<???>")
            tokens_generados.append(token)
    return tokens_generados


if __name__ == "__main__":
    # Demo: crear el decodificador y entrenar con ejemplos
    dec = L2Decoder(D_sem=128, lr=0.05)
    rng = random.Random(42)

    # Ejemplos de entrenamiento: (omega, token_id)
    # Simulamos que ciertos patrones de omega deberían producir ciertos tokens
    print("Entrenando L2 con ejemplos...")
    for epoch in range(50):
        losses = []
        for token_name, base_vector in [
            ("hambre", [1.0, 0.5] + [0.0]*126),
            ("comida", [0.8, 0.8] + [0.0]*126),
            ("necesito", [0.6, 0.9] + [0.0]*126),
            ("tengo", [0.9, 0.3] + [0.0]*126),
            ("comer", [0.7, 0.7] + [0.0]*126),
        ]:
            omega = np.array(base_vector[:128], dtype=float)
            # agregar ruido
            omega += np.random.randn(128) * 0.05
            tid = TOKEN2ID.get(token_name)
            if tid is not None:
                loss = dec.entrenar(omega, tid)
                losses.append(loss)
        if epoch % 10 == 0:
            print("  epoch %d: loss medio = %.4f" % (epoch, np.mean(losses) if losses else 0))

    # Test: decodificar un omega
    print("\nTest de decodificacion:")
    test_omega = np.array([1.0, 0.5] + [0.0]*126)
    test_omega += np.random.randn(128) * 0.03
    top5 = dec.decodificar(test_omega, topk=5, temperatura=0.8)
    print("  omega [1.0, 0.5, ...] -> ", [(ID2TOKEN.get(t, '?'), "%.3f" % p) for t, p in top5])

    # Guardar
    ruta = dec.guardar()
    print("\nGuardado en:", ruta)
    print("Decodificador L2 LISTO.")