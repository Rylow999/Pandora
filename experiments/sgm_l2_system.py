# -*- coding: utf-8 -*-
"""sgm_l2_system.py — Decodificador L2: Piedra Rosetta + Proyección Lineal.

Piedra Rosetta (L1): diccionario directo token ↔ omega determinístico.
Proyección L2: W·ω + b → softmax → token (SIN HRR).
"""
import sys, os, math, random, hashlib
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sgm_lang import TOKEN2ID, ID2TOKEN


class PiedraRosetta:
    """Diccionario directo token ↔ omega (fallback L1)."""
    
    def __init__(self, D=128):
        self.D = D
        self.token2omega = {}
        self._construir()
    
    def _construir(self):
        for token, tid in TOKEN2ID.items():
            self.token2omega[tid] = self._token_a_omega(token)
    
    def _token_a_omega(self, token):
        h = hashlib.md5(token.encode()).hexdigest()
        vec = []
        for i in range(0, len(h), 2):
            val = (int(h[i:i+2], 16) - 128) / 128.0
            vec.append(val)
        while len(vec) < self.D:
            vec.extend(vec[:self.D - len(vec)])
        vec = vec[:self.D]
        norm = math.sqrt(sum(x*x for x in vec)) or 1.0
        return [x/norm for x in vec]
    
    def buscar(self, omega, umbral=0.85):
        mejor_tid, mejor_cos = None, -1.0
        for tid, tok_omega in self.token2omega.items():
            cos = sum(a*b for a, b in zip(omega, tok_omega))
            if cos > mejor_cos:
                mejor_cos, mejor_tid = cos, tid
        if mejor_cos >= umbral:
            return mejor_tid, mejor_cos
        return None, mejor_cos


class L2Decoder:
    """Decodificador L2: W·ω + b → softmax → token."""
    
    def __init__(self, D=128, lr=0.05):
        self.D = D
        self.vocab_size = max(TOKEN2ID.values()) + 1 if TOKEN2ID else 100
        self.lr = lr
        self.W = np.random.randn(self.vocab_size, self.D) * 0.01
        self.b = np.zeros(self.vocab_size)
    
    def forward(self, omega):
        if isinstance(omega, list):
            omega = np.array(omega, dtype=float)
        logits = self.W.dot(omega) + self.b
        logits -= np.max(logits)
        exp = np.exp(logits)
        return exp / np.sum(exp)
    
    def decodificar(self, omega, topk=1, temperatura=1.0):
        probs = self.forward(omega)
        if temperatura != 1.0:
            logits = np.log(probs + 1e-12) / temperatura
            logits -= np.max(logits)
            exp = np.exp(logits)
            probs = exp / np.sum(exp)
        top_idx = np.argsort(probs)[-topk:][::-1]
        return [(int(idx), float(probs[idx])) for idx in top_idx]
    
    def entrenar(self, omega, token_id, lr=None):
        lr = lr or self.lr
        probs = self.forward(omega)
        dlogits = probs.copy()
        dlogits[token_id] -= 1.0
        if isinstance(omega, list):
            omega = np.array(omega, dtype=float)
        self.W -= lr * np.outer(dlogits, omega)
        self.b -= lr * dlogits
        return -math.log(probs[token_id] + 1e-12)
    
    def guardar(self, ruta):
        np.savez(ruta, W=self.W, b=self.b)
    
    def cargar(self, ruta):
        if os.path.exists(ruta):
            data = np.load(ruta, allow_pickle=True)
            if 'W' in data and 'b' in data:
                self.W, self.b = data['W'], data['b']
                return True
        return False


class DecodeL2:
    """Pipeline completo: campo de interferencia → decode → texto."""
    
    def __init__(self, D=128):
        self.D = D
        self.rosetta = PiedraRosetta(D)
        self.l2 = L2Decoder(D)
    
    def decode(self, zona, max_palabras=5, temperatura=0.8):
        """
        Decodifica una zona de interferencia a texto.
        zona: lista de (nodo_id, omega, interferencia)
        """
        if not zona:
            return "..."
        
        palabras = []
        for _, omega, interferencia in zona[:max_palabras]:
            token = None
            
            # Fallback L1: Piedra Rosetta
            tid, cos = self.rosetta.buscar(omega, umbral=0.80)
            if tid is not None:
                token = ID2TOKEN.get(tid, "<???>")
            
            # Proyección L2
            if token is None:
                t_i = np.array(omega) * interferencia
                top = self.l2.decodificar(t_i, topk=1, temperatura=temperatura)
                if top:
                    token = ID2TOKEN.get(top[0][0], "<???>")
            
            if token:
                palabras.append(token)
        
        return " ".join(palabras) if palabras else "..."


def entrenar_l2_offline(epochs=30, n_variaciones=20, verbose=True):
    """Entrena L2 con corpus generado desde la Piedra Rosetta."""
    rosetta = PiedraRosetta(128)
    l2 = L2Decoder(128, lr=0.5)
    
    # Corpus: tokens de estado interno con variaciones
    tokens_estado = ['comida', 'hambre', 'madera', 'zombie', 'soy', 'piedra',
                     'peligro', 'necesito', 'quiero', 'comer', 'explorar',
                     'creo', 'puede', 'talar', 'romper', 'mover', 'atacar',
                     'defender', 'colocar', 'recolectar']
    
    corpus = []
    for token in tokens_estado:
        if token in TOKEN2ID:
            tid = TOKEN2ID[token]
            omega = rosetta.obtener_omega(tid)
            for _ in range(n_variaciones):
                ruido = np.random.randn(128) * 0.05
                o = np.array(omega, dtype=float) + ruido
                o /= np.linalg.norm(o)
                corpus.append((o, tid))
    
    if verbose:
        print(f"Entrenando L2: {len(corpus)} ejemplos, {epochs} epochs...")
    
    for epoch in range(epochs):
        random.shuffle(corpus)
        losses = []
        for omega, tid in corpus:
            loss = l2.entrenar(omega, tid)
            losses.append(loss)
        if verbose and epoch % 5 == 0:
            print(f"  Epoch {epoch}: loss={np.mean(losses):.4f}")
    
    return l2


if __name__ == "__main__":
    l2 = entrenar_l2_offline(epochs=30, n_variaciones=20)
    l2.guardar("experiments/l2_projection.npz")
    print("Guardado: experiments/l2_projection.npz")