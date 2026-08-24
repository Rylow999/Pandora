# -*- coding: utf-8 -*-
"""sgm_kuramoto.py — Kuramoto: sincronización de fases.

φ(t+1) = [φ(t) + η·R·sin(φ_root - φ)] mod 2π
I = ||ω|| · cos(φ - φ_root)
"""
import math


def kuramoto_step(phi, phi_root, vitalidad, eta=0.05):
    """Actualiza fases de todos los nodos."""
    for i in range(len(phi)):
        R = vitalidad[i] if i < len(vitalidad) else 0.0
        delta = math.sin(phi_root - phi[i])
        phi[i] = (phi[i] + eta * R * delta) % (2 * math.pi)


def interferencia(omega, phi, phi_root):
    """Calcula interferencia de un nodo (Eq.7)."""
    norm = math.sqrt(sum(x * x for x in omega))
    return norm * math.cos(phi - phi_root)


def campo_interferencia(omega, phi, phi_root, vitalidad, umbral=0.45):
    """
    Devuelve lista de (nodo_id, omega, interferencia) para nodos relevantes.
    """
    zona = []
    for i in range(len(omega)):
        if i >= len(vitalidad) or i >= len(phi):
            break
        if vitalidad[i] < 0.1:
            continue
        I = interferencia(omega[i], phi[i], phi_root)
        if I > umbral:
            zona.append((i, omega[i], I))
    
    zona.sort(key=lambda x: -x[2])
    return zona


def promedio_ponderado(zona):
    """Promedia omega ponderados por interferencia."""
    if not zona:
        return None
    
    suma = None
    suma_peso = 0.0
    
    for _, omega, I in zona:
        peso = max(0, I)
        if suma is None:
            suma = [x * peso for x in omega]
        else:
            for j in range(len(omega)):
                suma[j] += omega[j] * peso
        suma_peso += peso
    
    if suma_peso > 0 and suma:
        return [x / suma_peso for x in suma]
    return None


def step_k_cadenas(edges, omega, phi, vitalidad, seed, K=10, pasos=3, alpha=5.0):
    """
    Ejecuta K cadenas paralelas sobre el grafo.
    Devuelve zona activa (nodos con interferencia > umbral).
    """
    zona_activa = {}
    
    for k in range(K):
        # Nodo inicial
        actual = seed
        
        for _ in range(pasos):
            vecinos = edges.get(actual, [])
            if not vecinos:
                break
            
            # Afinidad semántica (Eq.2)
            afinidades = []
            for v in vecinos:
                if v < len(omega) and actual < len(omega):
                    dist = math.sqrt(sum((a - b) ** 2 for a, b in zip(omega[actual], omega[v])))
                    afinidades.append(math.exp(-alpha * dist))
                else:
                    afinidades.append(0.0)
            
            suma = sum(afinidades) or 1.0
            probs = [a / suma for a in afinidades]
            siguiente = vecinos[probs.index(max(probs))]
            
            # Actualizar fase (Eq.3)
            if siguiente < len(phi):
                delta_phi = math.sin(phi[0] - phi[siguiente]) if phi else 0.0
                R = 1.0 / (1.0 + math.sqrt(sum((a - b) ** 2 for a, b in zip(omega[siguiente], omega[0])))) if omega else 1.0
                phi[siguiente] = (phi[siguiente] + 0.05 * R * delta_phi) % (2 * math.pi)
            
            # Actualizar vitalidad (Eq.5)
            if siguiente < len(vitalidad):
                vitalidad[siguiente] = vitalidad[siguiente] * math.exp(-0.01) + 1.0 * (1 - math.exp(-0.01))
            
            # Evaluar interferencia
            if siguiente < len(omega) and siguiente < len(phi):
                I = interferencia(omega[siguiente], phi[siguiente], phi[0] if phi else 0.0)
                if I > 0.45:
                    zona_activa[siguiente] = I
            
            actual = siguiente
    
    return zona_activa