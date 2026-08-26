#!/usr/bin/env python3
"""train_l2_real.py — Pipeline L2 real: co-ocurrencia → PMI → SVD → decoder.

Simplificado: sin t-SNE (muy lento en Python puro). Usa SVD directamente.
"""
import sys, os, math, random
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sgm_lang import TOKEN2ID, ID2TOKEN

def cargar(ruta):
    return np.load(ruta, allow_pickle=True).item()

def coocurrencia(datos, n_nodos):
    C = np.zeros((n_nodos, n_nodos))
    for zona in datos["campos"]:
        if not zona: continue
        nodos = [n for n, _, _ in zona]
        for i in nodos:
            for j in nodos:
                if i < n_nodos and j < n_nodos:
                    C[i, j] += 1
    return C

def pmi(C, eps=1e-10):
    total = C.sum()
    if total == 0: return np.zeros_like(C)
    P_ij = C / total
    P_i = C.sum(axis=1) / total
    P_j = C.sum(axis=0) / total
    PMI = np.zeros_like(C)
    for i in range(C.shape[0]):
        for j in range(C.shape[1]):
            if P_ij[i,j] > eps and P_i[i] > eps and P_j[j] > eps:
                PMI[i,j] = math.log(P_ij[i,j] / (P_i[i] * P_j[j]))
    return PMI

def svd(PMI, k=32):
    U, S, _ = np.linalg.svd(PMI, full_matrices=False)
    return U[:, :k] * S[:k]

class L2Decoder:
    def __init__(self, D=128, V=100, lr=0.05):
        self.W = np.random.randn(V, D) * 0.01
        self.b = np.zeros(V)
        self.lr = lr
    
    def forward(self, x):
        l = self.W.dot(x) + self.b
        l -= np.max(l)
        e = np.exp(l)
        return e / e.sum()
    
    def train(self, x, tid, lr=None):
        lr = lr or self.lr
        p = self.forward(x)
        d = p.copy()
        d[tid] -= 1.0
        self.W -= lr * np.outer(d, x)
        self.b -= lr * d
        return -math.log(p[tid] + 1e-12)
    
    def decode(self, x, topk=1):
        p = self.forward(x)
        idx = np.argsort(p)[-topk:][::-1]
        return [(int(i), float(p[i])) for i in idx]
    
    def save(self, path):
        np.savez(path, W=self.W, b=self.b)
    
    def load(self, path):
        if os.path.exists(path):
            d = np.load(path, allow_pickle=True)
            self.W, self.b = d['W'], d['b']
            return True
        return False

def train(datos, epochs=50, lr=0.05):
    V = len(TOKEN2ID)
    dec = L2Decoder(128, V, lr)
    
    # Usa METAS (tokens semanticos: comer/explorar/huir) en vez de acciones 0-16.
    # El L2 aprende estado (campo de interferencia) -> meta a ejecutar.
    pares = []
    for i, (zona, meta) in enumerate(zip(datos["campos"], datos.get("metas", datos.get("acciones", [])))):
        if not zona: continue
        omegas_paso = datos["omegas"][i] if i < len(datos.get("omegas", [])) else {}
        meta_tid = meta if isinstance(meta, int) else min(V-1, (meta or 0) % V)
        for nid, omega, _ in zona:
            if nid in omegas_paso:
                pares.append((np.array(omegas_paso[nid], dtype=float), meta_tid))
    
    if not pares:
        return None
    
    for ep in range(epochs):
        random.shuffle(pares)
        losses = [dec.train(x, t) for x, t in pares]
        if ep % 10 == 0:
            print(f"  Epoch {ep}: loss={np.mean(losses):.4f}")
    
    return dec

if __name__ == "__main__":
    print("=== L2 REAL (estado -> meta) ===")
    import sgm_core
    
    # Fuente principal: el estado real del bot (historial_campos + historial_metas_l2)
    # acumulado por el bridge en Minecraft. Si existe, entrenar con eso.
    ruta_estado = "experiments/sgm_estado.npy"
    if os.path.exists(ruta_estado):
        est = cargar(ruta_estado)
        campos = est.get("historial_campos", [])
        metas = est.get("historial_metas_l2", [])
        omegas = est.get("omega", [])
        print(f"  Del estado real del bridge: {len(campos)} campos, {len(metas)} metas")
        # construir omegas como dict {nid: omega} por zona
        omegas_pasos = [{i: omegas[i] for i in range(len(omegas))} for _ in range(len(campos))]
        datos = {"campos": campos, "metas": metas, "omegas": omegas_pasos}
    else:
        # fallback: recolectar datos simulados
        ruta_datos = "experiments/l2_raw_data.npy"
        if not os.path.exists(ruta_datos):
            from experiments.collect_l2_data import colectar
            datos, ag = colectar(n_pasos=200, semilla=42)
            datos["metas"] = datos.get("acciones", [])  # fallback simulado
            np.save(ruta_datos, datos)
        else:
            datos = cargar(ruta_datos)
        print(f"  (fallback simulado) {len(datos['campos'])} pasos")
    
    n = max((n for z in datos["campos"] if z for n, _, _ in z), default=0) + 1
    print(f"  Pasos: {len(datos['metas'])} | Nodos: {n}")
    
    C = coocurrencia(datos, n)
    P = pmi(C)
    vv = svd(P, k=min(32, n))
    print(f"  SVD: {vv.shape}")
    
    dec = train(datos)
    if dec:
        dec.save("experiments/l2_real.npz")
        # test: codificar metas conocidas
        for tk in ["comer", "explorar", "huir"]:
            x = np.random.randn(128) * 0.1
            top = dec.decode(x)[0]
            print(f"  {tk} -> {ID2TOKEN.get(top[0], '?')} ({top[1]:.3f})")
    print("OK")