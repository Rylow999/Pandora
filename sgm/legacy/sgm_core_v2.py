#!/usr/bin/env python3
"""sgm_core_v2.py — SGM con grafo vivo que crece con la experiencia.
El grafo nace vacío. Cada percepción crea/activa nodos.
Cada co-ocurrencia crea/refuerza aristas.
Los nodos compiten por vitalidad.
Los modos de comprensión operan sobre el grafo."""

import math, random, numpy as np

class GrafoVivo:
    """Grafo que nace vacío y crece con la experiencia."""
    
    def __init__(self, D=128):
        self.D = D
        self.nodos = []  # {id, omega, phi, vitalidad, etiqueta, tipo}
        self.aristas = {}  # {id: [ids vecinos]}
        self.consolidadas = set()
        self.MEMORIA = []  # memoria episódica
        
    def crear_nodo(self, etiqueta, tipo='percepcion'):
        """Crea un nuevo nodo o devuelve el existente."""
        # Buscar si ya existe un nodo con etiqueta similar
        for nodo in self.nodos:
            if nodo['etiqueta'] == etiqueta:
                return nodo['id']
        
        # Crear nuevo nodo
        omega = [random.gauss(0, 0.1) for _ in range(self.D)]
        norma = math.sqrt(sum(x*x for x in omega)) or 1
        omega = [x/norma for x in omega]
        
        nodo = {
            'id': len(self.nodos),
            'omega': omega,
            'phi': random.uniform(0, 2*math.pi),
            'vitalidad': 0.5,
            'etiqueta': etiqueta,
            'tipo': tipo,  # percepcion, accion, estado
            'ultimo_uso': 0,
            'resonancias': 0,
        }
        self.nodos.append(nodo)
        self.aristas[nodo['id']] = []
        return nodo['id']
    
    def crear_arista(self, a, b):
        """Crea una arista entre dos nodos."""
        if a == b:
            return
        if a not in self.aristas:
            self.aristas[a] = []
        if b not in self.aristas:
            self.aristas[b] = []
        if b not in self.aristas[a]:
            self.aristas[a].append(b)
            self.aristas[b].append(a)
    
    def reforzar_arista(self, a, b, fuerza=0.1):
        """Refuerza una arista por co-ocurrencia."""
        if a >= len(self.nodos) or b >= len(self.nodos):
            return
        na, nb = self.nodos[a], self.nodos[b]
        for i in range(self.D):
            na['omega'][i] += fuerza * nb['omega'][i]
        norma = math.sqrt(sum(x*x for x in na['omega'])) or 1
        for i in range(self.D):
            na['omega'][i] /= norma
        na['vitalidad'] = min(1, na['vitalidad'] + fuerza)
        nb['vitalidad'] = min(1, nb['vitalidad'] + fuerza)
        na['ultimo_uso'] = 0
        nb['ultimo_uso'] = 0
        self.consolidadas.add((a, b))
        self.consolidadas.add((b, a))
    
    def reforzar_nodo(self, nodo_id, fuerza=0.1):
        """Refuerza la vitalidad de un nodo."""
        if nodo_id >= len(self.nodos):
            return
        nodo = self.nodos[nodo_id]
        nodo['vitalidad'] = min(1, nodo['vitalidad'] + fuerza)
        nodo['ultimo_uso'] = 0
        nodo['resonancias'] += 1
    
    def kuramoto_step(self, eta=0.05):
        """Sincronización de Kuramoto: nodos se sincronizan con la raíz."""
        if not self.nodos:
            return
        phi_raiz = self.nodos[0]['phi']
        for nodo in self.nodos:
            R = nodo['vitalidad']
            delta = math.sin(phi_raiz - nodo['phi'])
            nodo['phi'] = (nodo['phi'] + eta * R * delta) % (2 * math.pi)
    
    def interferencia(self, nodo_id):
        """Interferencia de ondas (Eq. 7)."""
        if nodo_id >= len(self.nodos):
            return 0
        nodo = self.nodos[nodo_id]
        phi_raiz = self.nodos[0]['phi'] if self.nodos else 0
        norm = math.sqrt(sum(x*x for x in nodo['omega']))
        return norm * math.cos(nodo['phi'] - phi_raiz)
    
    def ppr(self, seed, alpha=0.15, iters=50):
        """PageRank personalizado."""
        n = len(self.nodos)
        if n == 0:
            return []
        rank = [0.0] * n
        rank[seed] = 1.0
        for _ in range(iters):
            nrank = [0.0] * n
            for i in range(n):
                if rank[i] == 0:
                    continue
                vecinos = self.aristas.get(i, [])
                if not vecinos:
                    nrank[i] += rank[i]
                    continue
                share = rank[i] * (1 - alpha) / len(vecinos)
                for j in vecinos:
                    if j < n:
                        nrank[j] += share
                nrank[i] += rank[i] * alpha
            rank = nrank
        return rank
    
    def inducir(self, a, b):
        """Inducción: generalizar una regla de casos observados."""
        if a >= len(self.nodos) or b >= len(self.nodos):
            return False
        self.reforzar_arista(a, b, 0.15)
        return True
    
    def deducir(self, a, b):
        """Deducción: aplicar regla + caso -> resultado."""
        if a >= len(self.nodos) or b >= len(self.nodos):
            return False
        # Verificar si hay conexión directa
        if b in self.aristas.get(a, []):
            return True
        # Verificar transitividad
        for vecino in self.aristas.get(a, []):
            if b in self.aristas.get(vecino, []):
                return True
        return False
    
    def abducir(self, resultado, topk=5):
        """Abducción: inferir causas más plausibles."""
        if resultado >= len(self.nodos):
            return []
        # PPR inverso: desde el resultado, encontrar causas
        inv_aristas = {}
        for i in self.aristas:
            for j in self.aristas[i]:
                if j not in inv_aristas:
                    inv_aristas[j] = []
                inv_aristas[j].append(i)
        
        n = len(self.nodos)
        rank = [0.0] * n
        rank[resultado] = 1.0
        for _ in range(50):
            nrank = [0.0] * n
            for i in range(n):
                if rank[i] == 0:
                    continue
                vecinos = inv_aristas.get(i, [])
                if not vecinos:
                    nrank[i] += rank[i]
                    continue
                share = rank[i] * 0.85 / len(vecinos)
                for j in vecinos:
                    if j < n:
                        nrank[j] += share
                nrank[i] += rank[i] * 0.15
            rank = nrank
        
        candidatos = [(i, s) for i, s in enumerate(rank) if i != resultado]
        candidatos.sort(key=lambda x: -x[1])
        return candidatos[:topk]
    
    def podar(self):
        """Poda nodos con vitalidad muy baja."""
        ahora = 0
        for nodo in self.nodos:
            nodo['ultimo_uso'] += 1
            nodo['vitalidad'] *= 0.999  # decaimiento natural
        
        # Podar nodos inactivos
        a_podar = []
        for i, nodo in enumerate(self.nodos):
            if nodo['vitalidad'] < 0.05 and nodo['ultimo_uso'] > 100:
                a_podar.append(i)
        
        for i in reversed(a_podar):
            del self.nodos[i]
            del self.aristas[i]
            # Actualizar aristas
            for j in self.aristas:
                self.aristas[j] = [x if x < i else x-1 for x in self.aristas[j] if x != i]


class SGMAgent:
    """Agente SGM con grafo vivo."""
    
    def __init__(self, D=128):
        self.D = D
        self.grafo = GrafoVivo(D)
        self.estado = {'hambre': 0, 'amenaza': 0, 'curiosidad': 0.5}
        self.posicion = (0, 0)
        self.ultima_accion = None
        self.historial = []
        
        # Crear nodos raíz
        self.n_raiz = self.grafo.crear_nodo('raiz', 'raiz')
        self.n_hambre = self.grafo.crear_nodo('hambre', 'estado')
        self.n_peligro = self.grafo.crear_nodo('peligro', 'estado')
        self.n_comida = self.grafo.crear_nodo('comida', 'percepcion')
        self.n_explorar = self.grafo.crear_nodo('explorar', 'accion')
        self.n_comer = self.grafo.crear_nodo('comer', 'accion')
        self.n_defender = self.grafo.crear_nodo('defender', 'accion')
        self.n_recolectar = self.grafo.crear_nodo('recolectar', 'accion')
        
        # Aristas iniciales
        self.grafo.crear_arista(self.n_hambre, self.n_comida)
        self.grafo.crear_arista(self.n_comida, self.n_comer)
        self.grafo.crear_arista(self.n_comer, self.n_hambre)
        self.grafo.crear_arista(self.n_peligro, self.n_defender)
        self.grafo.crear_arista(self.n_defender, self.n_peligro)
        self.grafo.crear_arista(self.n_explorar, self.n_recolectar)
        self.grafo.crear_arista(self.n_recolectar, self.n_comida)
    
    def percibir(self, percepciones):
        """Procesar percepciones del mundo."""
        nodos_activados = []
        for percepcion in percepciones:
            nodo_id = self.grafo.crear_nodo(percepcion, 'percepcion')
            self.grafo.reforzar_nodo(nodo_id, 0.2)
            nodos_activados.append(nodo_id)
            
            # Co-ocurrencia: crear aristas entre percepciones simultáneas
            for otro_id in nodos_activados[:-1]:
                self.grafo.crear_arista(nodo_id, otro_id)
                self.grafo.reforzar_arista(nodo_id, otro_id, 0.1)
        
        return nodos_activados
    
    def actualizar_estado(self, hambre, amenaza, curiosidad):
        """Actualizar estado interno."""
        self.estado['hambre'] = hambre
        self.estado['amenaza'] = amenaza
        self.estado['curiosidad'] = curiosidad
        
        # Reforzar nodos de estado
        self.grafo.reforzar_nodo(self.n_hambre, hambre * 0.3)
        self.grafo.reforzar_nodo(self.n_peligro, amenaza * 0.3)
        self.grafo.reforzar_nodo(self.n_explorar, curiosidad * 0.2)
    
    def elegir_accion(self):
        """Elegir acción basada en el estado del grafo."""
        activos = []
        if self.estado['hambre'] > 0.3:
            activos.append(self.n_hambre)
        if self.estado['amenaza'] > 0.3:
            activos.append(self.n_peligro)
        if self.estado['curiosidad'] > 0.7:
            activos.append(self.n_explorar)
        
        if not activos:
            return None
        
        # PPR combinado
        rank = [0.0] * len(self.grafo.nodos)
        for seed in activos:
            r = self.grafo.ppr(seed)
            for i in range(len(r)):
                rank[i] += r[i]
        
        # Añadir interferencia de Kuramoto
        for i in range(len(self.grafo.nodos)):
            I = self.grafo.interferencia(i)
            rank[i] *= (1 + I)
        
        # Elegir acción (nivel 1) con mayor rank
        acciones = [n for n in self.grafo.nodos if n['tipo'] == 'accion']
        if not acciones:
            return None
        
        mejor = max(acciones, key=lambda n: rank[n['id']])
        if rank[mejor['id']] > 0.1:
            return mejor['etiqueta']
        return None
    
    def ejecutar_accion(self, accion, resultado=None):
        """Ejecutar una acción y registrar el resultado."""
        self.ultima_accion = accion
        
        # Buscar nodo de la acción
        nodo_accion = None
        for n in self.grafo.nodos:
            if n['etiqueta'] == accion:
                nodo_accion = n['id']
                break
        
        if nodo_accion is None:
            nodo_accion = self.grafo.crear_nodo(accion, 'accion')
        
        # Reforzar nodo de acción
        self.grafo.reforzar_nodo(nodo_accion, 0.2)
        
        # Si hay resultado, crear arista causal
        if resultado:
            nodo_resultado = self.grafo.crear_nodo(resultado, 'percepcion')
            self.grafo.crear_arista(nodo_accion, nodo_resultado)
            self.grafo.reforzar_arista(nodo_accion, nodo_resultado, 0.3)
            
            # Memoria episódica
            self.grafo.MEMORIA.append({
                'accion': accion,
                'resultado': resultado,
                'estado': self.estado.copy(),
            })
    
    def expresarse(self):
        """Generar expresión basada en el estado del grafo."""
        # Usar PPR desde el estado dominante
        seed = self.n_explorar
        if self.estado['hambre'] > 0.3:
            seed = self.n_hambre
        elif self.estado['amenaza'] > 0.3:
            seed = self.n_peligro
        
        rank = self.grafo.ppr(seed)
        
        # Añadir interferencia
        for i in range(len(self.grafo.nodos)):
            I = self.grafo.interferencia(i)
            rank[i] *= (1 + I)
        
        # Top-k nodos más relevantes
        indices = sorted(range(len(rank)), key=lambda i: -rank[i])[:3]
        palabras = [self.grafo.nodos[i]['etiqueta'] for i in indices if self.grafo.nodos[i]['etiqueta'] != 'raiz']
        
        return ' '.join(palabras) if palabras else '...'
    
    def paso(self, percepciones, hambre, amenaza, curiosidad):
        """Un paso completo del agente."""
        # 1. Percepción
        self.percibir(percepciones)
        
        # 2. Actualizar estado
        self.actualizar_estado(hambre, amenaza, curiosidad)
        
        # 3. Kuramoto
        self.grafo.kuramoto_step()
        
        # 4. Elegir acción
        accion = self.elegir_accion()
        
        # 5. Ejecutar acción
        if accion:
            self.ejecutar_accion(accion)
        
        # 6. Poda ocasional
        if random.random() < 0.01:
            self.grafo.podar()
        
        return accion


if __name__ == "__main__":
    print("=== SGM con Grafo Vivo ===")
    ag = SGMAgent(128)
    
    # Simular experiencias
    experiencias = [
        (['arbol', 'madera'], 0.8, 0.0, 0.3),
        (['vaca', 'carne'], 0.6, 0.0, 0.4),
        (['zombie', 'peligro'], 0.3, 0.8, 0.2),
        (['piedra', 'carbon'], 0.5, 0.1, 0.6),
        (['mesa', 'craftear'], 0.4, 0.0, 0.7),
    ]
    
    for percepciones, hambre, amenaza, curiosidad in experiencias:
        ag.percibir(percepciones)
        ag.actualizar_estado(hambre, amenaza, curiosidad)
        ag.grafo.kuramoto_step()
        accion = ag.elegir_accion()
        print(f"  Percepciones: {percepciones} -> Acción: {accion}")
        if accion:
            ag.ejecutar_accion(accion, f"resultado_{accion}")
    
    print(f"\nNodos del grafo: {len(ag.grafo.nodos)}")
    print(f"Aristas: {sum(len(v) for v in ag.grafo.aristas.values())//2}")
    print(f"Memoria episódica: {len(ag.grafo.MEMORIA)}")
    
    # Probar modos de comprensión
    print("\n=== Modos de Comprensión ===")
    
    # Inducción
    ag.grafo.inducir(ag.n_hambre, ag.n_comida)
    print(f"  Inducción(hambre-> comida): arista reforzada")
    
    # Deducción
    resultado = ag.grafo.deducir(ag.n_comer, ag.n_hambre)
    print(f"  Deducción(comer-> hambre): {resultado}")
    
    # Abducción
    causas = ag.grafo.abducir(ag.n_hambre, topk=3)
    causa_etiquetas = [(ag.grafo.nodos[i]['etiqueta'], s) for i, s in causas if i < len(ag.grafo.nodos)]
    print(f"  Abducción(hambre): causas = {causa_etiquetas}")
    
    # Expresión
    print(f"\nExpresión: '{ag.expresarse()}'")
    
    print("\n=== Grafo Vivo FUNCIONANDO ===")