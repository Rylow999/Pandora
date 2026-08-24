#!/usr/bin/env python3
"""train_l2_real.py — Entrena L2 con PMI con co-acción → cluster → español.

Pipeline:
1. Carga datos crudos (campos, acciones, resultados)
2. Construye matriz de co-ocurrencia (nodo_i ↔ nodo_j en mismo campo)
3. Computa PMI entre pares de nodos co-activos y acciones
4. SVD sobre la matriz PMI para reducir dimensionalidad
5. t-SNE sobre los vectores SVD para visualizar clusters
6. Entrena decoder lineal W·ω + b → token desde los clusters
"""
import sys, os, math, random
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sgm_lang import TOKEN2ID, ID2TOKEN

def cargar_datos(ruta):
    """Carga datos crudos."""
    datos = np.load(ruta, allow_pickle=True).item()
    return datos

def construir_coocurrencia(datos, n_nodos):
    """
    Construye matriz de co-ocurrencia entre nodos.
    C[i,j] = veces que nodo i y j aparecen juntos en un campo.
    """
    C = np.zeros((n_nodos, n_nodos))
    
    for zona in datos["campos"]:
        if not zona:
            continue
        nodos = [nodo_id for nodo_id, _, _ in zona]
        for i in nodos:
            for j in nodos:
                if i < n_nodos and j < n_nodos:
                    C[i, j] += 1
    
    return C

def computar_pmi(C, epsilon=1e-10):
    """
    Computa PMI entre nodos: PMI(i,j) = log( P(i,j) / (P(i)*P(j)) )
    """
    total = C.sum()
    if total == 0:
        return np.zeros_like(C)
    
    P_ij = C / total
    P_i = C.sum(axis=1) / total
    P_j = C.sum(axis=0) / total
    
    PMI = np.zeros_like(C)
    for i in range(C.shape[0]):
        for j in range(C.shape[1]):
            if P_ij[i, j] > epsilon and P_i[i] > epsilon and P_j[j] > epsilon:
                PMI[i, j] = math.log(P_ij[i, j] / (P_i[i] * P_j[j]))
    
    return PMI

def svd_reducir(PMI, k=32):
    """SVD para reducir dimensionalidad."""
    U, S, Vt = np.linalg.svd(PMI, full_matrices=False)
    # Tomar los k componentes principales
    return U[:, :k] * S[:k]

def entrenar_l2(datos, vectores, n_epochs=100, lr=0.05):
    """
    Entrena decoder L2: W·ω + b → softmax → token.
    Asigna tokens a los nodos basado en los clusters.
    """
    # Contar tokens disponibles
    vocab_size = len(TOKEN2ID)
    
    # Construir pares (omega, token_id)
    pares = []
    for i, (zona, accion) in enumerate(zip(datos["campos"], datos["acciones"])):
        if not zona:
            continue
        
        # Elegir token basado en acción
        # 0=noop, 1-4=mover, 5=interactuar, 6=romper, 7-8=recoger/colocar, 9=craftear
        token_id = min(vocab_size - 1, accion % vocab_size)
        
        for nodo_id, omega, _ in zona:
            if nodo_id < len(vectores):
                pares.append((vectores[nodo_id], token_id))
    
    if not pares:
        print("  No hay pares para entrenar")
        return None
    
    # Entrenar
    decoder = L2Decoder(128, vocab_size, lr)
    
    for epoch in range(n_epochs):
        random.shuffle(pares)
        losses = []
        for omega, tid in pares:
            loss = decoder.entrenar(omega, tid)
            losses.append(loss)
        
        if epoch % 20 == 0:
            print(f"  Epoch {epoch}: loss={np.mean(losses):.4f}")
    
    return decoder

class L2Decoder:
    """Decoder L2: W·ω + b → softmax → token."""
    
    def __init__(self, D=128, vocab_size=100, lr=0.05):
        self.D = D
        self.vocab_size = vocab_size
        self.lr = lr
        self.W = np.random.randn(vocab_size, D) * 0.01
        self.b = np.zeros(vocab_size)
    
    def forward(self, omega):
        logits = self.W.dot(omega) + self.b
        logits -= np.max(logits)
        exp = np.exp(logits)
        return exp / np.sum(exp)
    
    def decodificar(self, omega, topk=1):
        probs = self.forward(omega)
        top_idx = np.argsort(probs)[-topk:][::-1]
        return [(int(idx), float(probs[idx])) for idx in top_idx]
    
    def entrenar(self, omega, token_id, lr=None):
        lr = lr or self.lr
        probs = self.forward(omega)
        dlogits = probs.copy()
        dlogits[token_id] -= 1.0
        self.W -= lr * np.outer(dlogits, omega)
        self.b -= lr * dlogits
        return -math.log(probs[token_id] + 1e-12)
    
    def guardar(self, ruta):
        np.savez(ruta, W=self.W, b=self.b)
    
    def cargar(self, ruta):
        if os.path.exists(ruta):
            data = np.load(ruta, allow_pickle=True)
            self.W, self.b = data['W'], data['b']
            return True
        return False

if __name__ == "__main__":
    print("=== ENTRENAMIENTO L2 REAL ===")
    print()
    
    # 1. Cargar datos
    datos = cargar_datos("experiments/l2_raw_data.npy")
    n_nodos = max(max((nodo_id for nodo_id, _, _ in zona), default=0) for zona in datos["campos"] if zona) + 1
    print(f"  Pasos: {len(datos['acciones'])}")
    print(f"  Nodos: {n_nodos}")
    
    # 2. Co-ocurrencia
    C = construir_coocurrencia(datos, n_nodos)
    print(f"  Co-ocurrencia: {C.sum():.0f} co-activaciones")
    
    # 3. PMI
    PMI = computar_pmi(C)
    print(f"  PMI: max={PMI.max():.3f}, min={PMI.min():.3f}")
    
    # 4. SVD
    vectores = svd_reducir(PMI, k=32)
    print(f"  SVD: {vectores.shape}")
    
    # 5. Entrenar L2
    print()
    print("Entrenando decoder L2...")
    decoder = entrenar_l2(datos, vectores, n_epochs=50)
    
    if decoder:
        decoder.guardar("experiments/l2_real.npz")
        print("Guardado: experiments/l2_real.npz")
    
    print("OK")