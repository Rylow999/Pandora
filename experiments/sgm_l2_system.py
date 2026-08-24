#!/usr/bin/env python3
"""
sgm_l2_system.py — Sistema L2 completo: Piedra Rosetta + Proyección Lineal.

Piedra Rosetta: diccionario directo token <-> omega (fallback L1).
  - Cada palabra conocida tiene su vector semántico.
  - Si omega está cerca de un token conocido → usar directamente.

Proyección L2: W·ω + b → softmax → token.
  - Entrenada offline con corpus (omega, token).
  - Campo de interferencia → promedio ponderado → proyección → sample.

Reemplaza los ifs hardcodeados por: campo de interferencia → decode_l2() → texto.
"""
import sys, os, math, random, hashlib
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sgm_lang import TOKEN2ID, ID2TOKEN


# ============ PIEDRA ROSETTA (L1) ============

class PiedraRosetta:
    """
    Diccionario directo token <-> omega.
    Cada palabra tiene un vector semántico (hash-based determinístico).
    Fallback L1: si omega está cerca de un token conocido, usarlo directamente.
    """
    
    def __init__(self, D=128):
        self.D = D
        self.token2omega = {}  # token_id -> omega
        self.omega2token = {}  # omega_key -> token_id
        self._construir()
    
    def _construir(self):
        """Construye el mapeo para todos los tokens del diccionario."""
        for token, tid in TOKEN2ID.items():
            omega = self._token_a_omega(token)
            self.token2omega[tid] = omega
            # Key para búsqueda rápida (cuantización binaria)
            key = self._omega_key(omega)
            self.omega2token[key] = tid
    
    def _token_a_omega(self, token):
        """Convierte un token en un vector semántico determinístico."""
        # Hash del token → vector D-dimensional
        h = hashlib.md5(token.encode()).hexdigest()
        vec = []
        for i in range(0, len(h), 2):
            val = (int(h[i:i+2], 16) - 128) / 128.0
            vec.append(val)
        # Ajustar a D dimensiones
        while len(vec) < self.D:
            vec.extend(vec[:self.D - len(vec)])
        vec = vec[:self.D]
        # Normalizar
        norm = math.sqrt(sum(x*x for x in vec)) or 1.0
        return [x/norm for x in vec]
    
    def _omega_key(self, omega, bins=8):
        """Cuantiza omega para búsqueda rápida."""
        return tuple(int((x + 1) * bins / 2) for x in omega[:16])
    
    def buscar(self, omega, umbral=0.85):
        """
        Busca el token más cercano a omega.
        Devuelve (token_id, coseno) si coseno > umbral, si no None.
        """
        mejor_tid = None
        mejor_cos = -1.0
        
        for tid, tok_omega in self.token2omega.items():
            cos = sum(a*b for a, b in zip(omega, tok_omega))
            if cos > mejor_cos:
                mejor_cos = cos
                mejor_tid = tid
        
        if mejor_cos >= umbral:
            return mejor_tid, mejor_cos
        return None, mejor_cos
    
    def obtener_omega(self, token_id):
        """Devuelve el omega de un token."""
        return self.token2omega.get(token_id, [0.0]*self.D)
    
    def obtener_token(self, token_id):
        """Devuelve el texto de un token."""
        return ID2TOKEN.get(token_id, "<???>")


# ============ CORPUS GENERATOR ============

class CorpusL2:
    """
    Genera corpus de entrenamiento (omega, token) para L2.
    Usa la Piedra Rosetta + variaciones con ruido.
    """
    
    def __init__(self, D=128, ruido=0.05):
        self.D = D
        self.ruido = ruido
        self.rosetta = PiedraRosetta(D)
    
    def generar(self, n_variaciones=20):
        """
        Genera corpus completo.
        Para cada token: omega_original + n_variaciones con ruido.
        Devuelve lista de (omega_array, token_id).
        """
        corpus = []
        
        for token, tid in TOKEN2ID.items():
            omega_base = self.rosetta.obtener_omega(tid)
            
            # Original
            corpus.append((np.array(omega_base, dtype=float), tid))
            
            # Variaciones con ruido
            for _ in range(n_variaciones):
                ruido = np.random.randn(self.D) * self.ruido
                omega = np.array(omega_base, dtype=float) + ruido
                norm = np.linalg.norm(omega)
                if norm > 0:
                    omega /= norm
                corpus.append((omega, tid))
        
        return corpus
    
    def generar_desde_grafo(self, agente):
        """
        Genera corpus desde los nodos activos del grafo del agente.
        Para cada nodo con interferencia > umbral: (omega*I, token_mas_cercano).
        """
        corpus = []
        
        for i, omega in enumerate(agente.omega):
            if i >= len(agente.vitalidad):
                break
            if agente.vitalidad[i] < 0.3:
                continue
            
            # Buscar token más cercano en Rosetta
            tid, cos = self.rosetta.buscar(omega, umbral=0.7)
            if tid is not None:
                # Token semántico escalado por interferencia
                interferencia = agente.vitalidad[i]
                t_i = np.array(omega, dtype=float) * interferencia
                corpus.append((t_i, tid))
        
        return corpus


# ============ L2 DECODER (PROYECCIÓN LINEAL) ============

class L2Decoder:
    """
    Decodificador L2: proyección lineal W·ω + b → softmax → token.
    Entrenable con SGD + cross-entropy.
    """
    
    def __init__(self, D=128, vocab_size=None, lr=0.05):
        self.D = D
        self.vocab_size = vocab_size or len(TOKEN2ID)
        self.lr = lr
        self.W = None
        self.b = None
        self._inicializar()
    
    def _inicializar(self):
        """Inicializa W y b."""
        # Asegurar que vocab_size cubre todos los tokens
        max_tid = max(TOKEN2ID.values()) if TOKEN2ID else 0
        self.vocab_size = max(self.vocab_size, max_tid + 1)
        self.W = np.random.randn(self.vocab_size, self.D) * 0.01
        self.b = np.zeros(self.vocab_size)
    
    def forward(self, omega):
        """Devuelve distribución de probabilidad sobre tokens."""
        if isinstance(omega, list):
            omega = np.array(omega, dtype=float)
        logits = self.W.dot(omega) + self.b
        logits -= np.max(logits)  # estabilidad numérica
        exp = np.exp(logits)
        return exp / np.sum(exp)
    
    def decodificar(self, omega, topk=1, temperatura=1.0):
        """Devuelve lista de (token_id, prob)."""
        probs = self.forward(omega)
        if temperatura != 1.0:
            logits = np.log(probs + 1e-12) / temperatura
            logits -= np.max(logits)
            exp = np.exp(logits)
            probs = exp / np.sum(exp)
        
        top_idx = np.argsort(probs)[-topk:][::-1]
        return [(int(idx), float(probs[idx])) for idx in top_idx]
    
    def entrenar(self, omega, token_id, lr=None):
        """Un paso de SGD. Loss = -log p(token_id | omega)."""
        lr = lr or self.lr
        probs = self.forward(omega)
        
        # Gradiente cross-entropy
        dlogits = probs.copy()
        dlogits[token_id] -= 1.0
        
        # Actualizar
        if isinstance(omega, list):
            omega = np.array(omega, dtype=float)
        self.W -= lr * np.outer(dlogits, omega)
        self.b -= lr * dlogits
        
        return -math.log(probs[token_id] + 1e-12)
    
    def entrenar_corpus(self, corpus, epochs=50, verbose=True):
        """Entrena sobre un corpus completo."""
        if not corpus:
            return []
        
        losses = []
        for epoch in range(epochs):
            random.shuffle(corpus)
            epoch_losses = []
            for omega, tid in corpus:
                loss = self.entrenar(omega, tid)
                epoch_losses.append(loss)
            
            avg_loss = np.mean(epoch_losses)
            losses.append(avg_loss)
            if verbose and epoch % 10 == 0:
                print(f"  Epoch {epoch}: loss = {avg_loss:.4f}")
        
        return losses
    
    def guardar(self, ruta):
        """Guarda W y b en .npz."""
        np.savez(ruta, W=self.W, b=self.b, D=self.D, vocab_size=self.vocab_size)
    
    def cargar(self, ruta):
        """Carga W y b desde .npz."""
        if os.path.exists(ruta):
            data = np.load(ruta, allow_pickle=True)
            if 'W' in data and 'b' in data:
                self.W = data['W']
                self.b = data['b']
                return True
        return False


# ============ CAMPO DE INTERFERENCIA ============

class CampoInterferencia:
    """
    Calcula el campo de interferencia (Eq.7) para todos los nodos.
    I_i = ||ω_i|| · cos(φ_i - φ_root)
    Nodos con I_i > θ son 'cognitivamente relevantes'.
    """
    
    def __init__(self, agente, umbral=0.45):
        self.agente = agente
        self.umbral = umbral
    
    def computar(self):
        """
        Devuelve lista de (nodo_id, omega, interferencia) para nodos relevantes.
        Ordenada por interferencia decreciente.
        """
        zona = []
        phi_root = self.agente.phi[0] if self.agente.phi else 0.0
        
        for i in range(len(self.agente.omega)):
            if i >= len(self.agente.vitalidad):
                break
            if i >= len(self.agente.phi):
                break
            if self.agente.vitalidad[i] < 0.1:
                continue
            
            omega = self.agente.omega[i]
            norm = math.sqrt(sum(x*x for x in omega))
            cos_phi = math.cos(self.agente.phi[i] - phi_root)
            interferencia = norm * cos_phi
            
            if interferencia > self.umbral:
                zona.append((i, omega, interferencia))
        
        # Ordenar por interferencia decreciente
        zona.sort(key=lambda x: -x[2])
        return zona
    
    def promedio_ponderado(self, topk=5):
        """
        Promedia los omega de los topk nodos más relevantes,
        ponderados por interferencia.
        """
        zona = self.computar()
        if not zona:
            return None
        
        # Tomar topk
        relevantes = zona[:topk]
        
        # Promedio ponderado
        suma_omega = np.zeros(self.agente.D)
        suma_peso = 0.0
        
        for _, omega, interferencia in relevantes:
            peso = max(0, interferencia)
            suma_omega += np.array(omega) * peso
            suma_peso += peso
        
        if suma_peso > 0:
            suma_omega /= suma_peso
        
        return suma_omega


# ============ DECODE L2 (PIPELINE COMPLETO) ============

class DecodeL2:
    """
    Pipeline completo: campo de interferencia → decode_l2() → texto.
    
    1. Campo de interferencia → nodos relevantes
    2. Promedio ponderado de omega
    3. Fallback L1 (Piedra Rosetta): si omega cercano a token conocido → usarlo
    4. Proyección L2: W·ω + b → softmax → sample
    5. Concatenar tokens
    """
    
    def __init__(self, D=128, usar_rosetta=True, usar_l2=True):
        self.D = D
        self.rosetta = PiedraRosetta(D) if usar_rosetta else None
        self.l2 = L2Decoder(D) if usar_l2 else None
        self.campo = None
    
    def inicializar_agente(self, agente):
        """Inicializa el campo de interferencia para un agente."""
        self.campo = CampoInterferencia(agente)
    
    def decode(self, agente, max_palabras=5, temperatura=0.8, verbose=False):
        """
        Decodifica el estado del agente a texto.
        Devuelve string con la expresión generada.
        """
        if self.campo is None or self.campo.agente is not agente:
            self.inicializar_agente(agente)
        
        # 1. Campo de interferencia
        zona = self.campo.computar()
        if not zona:
            return "..."
        
        palabras = []
        
        for nodo_id, omega, interferencia in zona[:max_palabras]:
            token = None
            
            # 2. Fallback L1: Piedra Rosetta
            if self.rosetta is not None:
                tid, cos = self.rosetta.buscar(omega, umbral=0.80)
                if tid is not None:
                    token = ID2TOKEN.get(tid, "<???>")
                    if verbose:
                        print(f"  L1: nodo{nodo_id} -> '{token}' (cos={cos:.3f})")
            
            # 3. Proyección L2
            if token is None and self.l2 is not None:
                t_i = np.array(omega) * interferencia
                top = self.l2.decodificar(t_i, topk=1, temperatura=temperatura)
                if top:
                    tid = top[0][0]
                    prob = top[0][1]
                    token = ID2TOKEN.get(tid, "<???>")
                    if verbose:
                        print(f"  L2: nodo{nodo_id} -> '{token}' (p={prob:.3f})")
            
            if token:
                palabras.append(token)
        
        return " ".join(palabras) if palabras else "..."
    
    def entrenar_offline(self, epochs=50, n_variaciones=20, verbose=True):
        """Entrena L2 offline con corpus generado desde la Piedra Rosetta."""
        if self.l2 is None:
            return
        
        corpus_gen = CorpusL2(self.D)
        corpus = corpus_gen.generar(n_variaciones)
        
        if verbose:
            print(f"Entrenando L2: {len(corpus)} ejemplos, {epochs} epochs...")
        
        losses = self.l2.entrenar_corpus(corpus, epochs=epochs, verbose=verbose)
        
        if verbose and losses:
            print(f"  Loss final: {losses[-1]:.4f}")
    
    def guardar(self, ruta_base):
        """Guarda L2 y Rosetta."""
        if self.l2:
            self.l2.guardar(ruta_base + "_l2.npz")
    
    def cargar(self, ruta_base):
        """Carga L2."""
        if self.l2:
            return self.l2.cargar(ruta_base + "_l2.npz")
        return False


# ============ TEST ============

if __name__ == "__main__":
    print("=== TEST SISTEMA L2 ===")
    print()
    
    # 1. Piedra Rosetta
    rosetta = PiedraRosetta(128)
    print(f"Rosetta: {len(rosetta.token2omega)} tokens mapeados")
    
    # Test: buscar token
    test_token = "hambre"
    test_tid = TOKEN2ID[test_token]
    test_omega = rosetta.obtener_omega(test_tid)
    found_tid, cos = rosetta.buscar(test_omega)
    print(f"  '{test_token}' -> buscar: '{ID2TOKEN.get(found_tid)}' (cos={cos:.3f})")
    
    # 2. Corpus
    corpus_gen = CorpusL2(128)
    corpus = corpus_gen.generar(n_variaciones=10)
    print(f"Corpus: {len(corpus)} ejemplos")
    
    # 3. L2 Decoder
    l2 = L2Decoder(128)
    losses = l2.entrenar_corpus(corpus, epochs=20, verbose=False)
    print(f"L2 entrenado: loss inicial={losses[0]:.4f}, final={losses[-1]:.4f}")
    
    # 4. Decodificar
    test_omega = rosetta.obtener_omega(TOKEN2ID['comida'])
    top = l2.decodificar(test_omega, topk=3)
    print(f"  'comida' -> {[(ID2TOKEN[t], f'{p:.3f}') for t, p in top]}")
    
    # 5. Campo de interferencia (necesita agente)
    print()
    print("=== TEST COMPLETO CON AGENTE ===")
    
    from sgm_core import SGMAgent
    ag = SGMAgent(random.Random(42), 128, n_nodes=64, gamma=0.01)
    ag.set_edges({i: random.sample(range(64), min(5, 63)) for i in range(64)})
    ag.instinto_alimentacion = 5
    
    # Simular actividad
    ag._hambre_real = 0.7
    ag._amenaza = 0.1
    ag._algo_enfrente = 1
    ag._posicion_actual = (10, 10)
    ag._hay_gradiente = True
    ag._gradiente_dir = (1, 0)
    ag._config_grad = {'activo': True, 'fuerza': 0.8}
    ag._config_curio = {'activo': True, 'fuerza': 0.4}
    ag._inc_dirs = {1: 1.0, 2: 0.5, 3: 0.5, 4: 0.5}
    sv = [0.2, 0.2, 0.7, 0.1, 0.8, 1.0, 1.0] + [0.0] * 11
    ag.step(sv, list(range(17)))
    
    # Decode L2
    decoder = DecodeL2(128)
    decoder.l2 = l2  # Usar el ya entrenado
    decoder.inicializar_agente(ag)
    
    texto = decoder.decode(ag, max_palabras=5, verbose=True)
    print(f"Expresión generada: '{texto}'")
    
    print()
    print("=== SISTEMA L2 FUNCIONANDO ===")