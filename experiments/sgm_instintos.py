# -*- coding: utf-8 -*-
"""sgm_instintos.py — Instintos y drives del agente."""
import math


class Instintos:
    """Instintos biológicos del agente."""
    
    def __init__(self):
        # Umbrales
        self.umbral_hambre = 0.3
        self.umbral_amenaza = 0.5
        self.umbral_carencia = 0.3
        self.devaluar_umbral = 0.35
        
        # Fuerzas
        self.fuerza_alimentacion = 0.5
        self.fuerza_exploracion = 0.4
        self.fuerza_defensa = 0.7
        self.fuerza_desplazamiento = 0.6
        
        # Drives
        self.drive_noop = 0.0
        self.drive_noop_umbral = 1.5
        self.drive_noop_fuerza = 1.0
        self.drive_noop_tasa = 0.1
        self.drive_noop_descarga = 0.5
        
        # Estado
        self.necesidad_insatisfecha = False
        self.incertidumbre_acum = 0.0
        self.instinto_explorar_umbral = 3
    
    def hambre(self, food):
        """Hambre real basado en food (0-20)."""
        return max(0.0, 1.0 - food / 20.0)
    
    def amenaza(self, health, health_max=20):
        """Amenaza basada en salud."""
        if health < health_max * 0.75:
            return (health_max - health) / health_max
        return 0.0
    
    def carencia(self, V_grafo):
        """Carencia = V_grafo bajo umbral."""
        return V_grafo < self.umbral_carencia
    
    def fuerza_instinto(self, V_grafo):
        """Fuerza del instinto de alimentación."""
        if self.carencia(V_grafo):
            return self.fuerza_alimentacion * (self.umbral_carencia - V_grafo)
        return 0.0
    
    def quiere_explorar(self):
        """Curiosidad basada en incertidumbre."""
        return self.incertidumbre_acum >= self.instinto_explorar_umbral
    
    def actualizar_drive_noop(self, accion):
        """Actualiza el drive de acción (SEEKING)."""
        if accion == 0:
            self.drive_noop = min(self.drive_noop_umbral * 3, self.drive_noop + self.drive_noop_tasa)
        else:
            self.drive_noop = max(0.0, self.drive_noop - self.drive_noop_descarga)
    
    def drive_dispara(self):
        """El drive noop está activo."""
        return self.drive_noop >= self.drive_noop_umbral