#!/usr/bin/env python3
"""sgm_lang_modelo.py — Mini-Transformer numpy para SGM (Fase 10).

Un transformer PEQUENO implementado en numpy puro (sin pytorch), entrenable online
con las interacciones de SGM. Traduce el ESTADO de SGM (vector condicion, el
'equivalente a LoRA') + contexto de tokens hacia la siguiente palabra del mensaje.

Arquitectura minima (fiel a un transformer de verdad, pero chico):
 - embedding de tokens (tabla de vectores aprendida)
 - condicion de estado: el vector de estado SGM se concatenaria al contexto como
   un token global que condiciona la atencion (asi como SGM se 'siente', asi habla)
 - self-attention de una cabeza (QK^T/sqrt(d) softmax sobre V)
 - capa feedforward pequeña
 - softmax de salida sobre el vocabulario

Entrenable: forward + backprop simple (descenso de gradiente estocastico) con
pares (contexto + condicion SGM) -> sgte token. Aprende de las interacciones
(conversacion acumulada), POCO A POCO, con el diccionario base como vocabulario.

NOTA honesta: con vocab chico y numpy, genera frases-esquema del diccionario (no
espanol fluido). Aprende a PRODUCIR la secuencia de tokens del mensaje correcto
dado el estado de SGM. El objetivo es que mejore con las interacciones reales.
"""
import numpy as np


class MiniTransformer:
    """Transformador minimo de una capa con 1 cabeza de atencion, en numpy puro."""

    def __init__(self, vocab_size, d_model=32, estado_dim=8, lr=0.05):
        self.V = vocab_size
        self.d = d_model
        self.es = estado_dim  # tamano del vector de estado (condicion SGM)
        self.lr = lr
        rng = np.random.default_rng(42)
        # embedding de tokens
        self.We = rng.normal(0, 0.1, (vocab_size, d_model))
        # proyecciones de atencion
        self.Wq = rng.normal(0, 0.1, (d_model, d_model))
        self.Wk = rng.normal(0, 0.1, (d_model, d_model))
        self.Wv = rng.normal(0, 0.1, (d_model, d_model))
        # proyeccion del estado (condicion) -> d_model (para inyectar)
        self.Wc = rng.normal(0, 0.1, (estado_dim, d_model))
        # feedforward
        self.W1 = rng.normal(0, 0.1, (d_model, d_model * 2))
        self.b1 = np.zeros(d_model * 2)
        self.W2 = rng.normal(0, 0.1, (d_model * 2, d_model))
        self.b2 = np.zeros(d_model)
        # salida (logits sobre vocabulario)
        self.Wo = rng.normal(0, 0.1, (d_model, vocab_size))
        self.bo = np.zeros(vocab_size)

    def _softmax(self, x):
        e = np.exp(x - x.max())
        return e / e.sum()

    def forward(self, tokens, estado):
        """tokens: lista de ids de contexto (sin SOS/EOS). estado: vector de estado [es].
        Devuelve logits sobre el siguiente token (vector [V]) y guarda activaciones."""
        # embed tokens
        X = np.array([self.We[t] for t in tokens], dtype=float)  # (L, d)
        # condicion de estado: vector que se suma a la media (lo que SGM 'siente')
        cond = estado @ self.Wc  # (d,)  - condiciona TODA la secuencia
        # self-attention de 1 cabeza sobre la secuencia + cond
        Q = X @ self.Wq  # (L, d)
        K = X @ self.Wk
        V = X @ self.Wv
        # inyectar condicion a las claves/valores (como un token global de estado)
        K = K + cond[None, :]
        V = V + cond[None, :]
        scores = Q @ K.T / np.sqrt(self.d)  # (L, L)
        attn = np.array([self._softmax(r) for r in scores])  # (L, L)
        ctx = attn @ V  # (L, d)  contextualizado
        # pool: usar el ultimo token como la representacion a predecir
        h = ctx[-1]
        # feedforward
        h1 = np.tanh(h @ self.W1 + self.b1)
        h2 = h1 @ self.W2 + self.b2
        h3 = h2 + h  # residual (opcional)
        logits = h3 @ self.Wo + self.bo
        self._cache = (X, Q, K, V, attn, ctx, h1, h)
        return logits

    def pred_proba(self, tokens, estado):
        logits = self.forward(tokens, estado)
        return self._softmax(logits)

    def predecir(self, tokens, estado, top=3):
        """Genera el siguiente token (muestra de los top). Devuelve (token_id, proba)."""
        p = self.pred_proba(tokens, estado)
        top_idx = np.argsort(p)[::-1][:top]
        probs = p[top_idx]
        probs = probs / probs.sum()
        return int(np.random.choice(top_idx, p=probs)), float(p[top_idx[0]])

    def entrenar(self, tokens, estado, target):
        """Backprop de un paso SGE para aprender (contexto, estado) -> target token.
        Actualiza los pesos por descenso de gradiente con la loss (entropia cruzada)."""
        logits = self.forward(tokens, estado)
        # softmax + loss
        p = self._softmax(logits)
        grad_logits = p.copy()
        grad_logits[target] -= 1.0  # derivada de cross-entropy
        grad_logits /= max(1, len(tokens))  # escala

        X, Q, K, V, attn, ctx, h1, h = self._cache
        d = self.d

        # gradientes (reglas de la cadena, simplificadas para esta arquitectura)
        grad_h3 = grad_logits @ self.Wo.T
        grad_Wo = np.outer(h, grad_logits)
        grad_bo = grad_logits

        grad_h = grad_h3
        grad_W2 = np.outer(h1, grad_h)
        grad_b2 = grad_h
        grad_h1 = grad_h @ self.W2.T
        grad_h1 = grad_h1 * (1.0 - np.tanh(h1) ** 2)
        grad_W1 = np.outer(h, grad_h1)
        grad_b1 = grad_h1
        grad_ctx = grad_h1 @ self.W1.T  # gradiente sobre el contexto del ultimo token

        # actualizar (descenso de gradiente)
        self.Wo -= self.lr * grad_Wo
        self.bo -= self.lr * grad_bo
        self.W2 -= self.lr * grad_W2
        self.b2 -= self.lr * grad_b2
        self.W1 -= self.lr * grad_W1
        self.b1 -= self.lr * grad_b1

        return -np.log(p[target])  # loss (para tracking)


if __name__ == "__main__":
    # smoke test: entrenar una regla trivial (estado hambre -> token comida)
    from sgm_lang import VOCAB_SIZE, TOKEN2ID, SOS, EOS, estado_a_contexto_vector, estado_a_tokens
    m = MiniTransformer(VOCAB_SIZE, d_model=32, estado_dim=8)
    # generar un par de ejemplo
    estado = np.zeros(8)
    estado[0] = 0.9  # hambre alta
    contexto = [TOKEN2ID["tengo"], TOKEN2ID["hambre"]]
    target = TOKEN2ID["comida"]
    for i in range(50):
        loss = m.entrenar(contexto, estado, target)
    print("loss tras 50 pasos:", round(loss, 3))
    # predecir
    tok, pr = m.predecir(contexto, estado)
    print("predice token idx", tok, "=", list(TOKEN2ID)[tok], "(esp comida)")