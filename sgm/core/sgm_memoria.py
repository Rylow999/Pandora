# -*- coding: utf-8 -*-
"""sgm_memoria.py — Memoria episódica, place cells avanzadas, NOUS.

Buffer de eventos salientes, navegación a meta, modelo de objetos,
ventana dinámica W(t), densidad contextual ρ(t).
"""
import math


class Memoria:
    """Memoria episódica y modelo del mundo."""
    
    def __init__(self, D=128, max_episodios=50):
        self.D = D
        self.max_episodios = max_episodios
        self.episodios = []
        self.historia = []
        self.historia_max = 200
        self.saliencia_umbral = 1
        self.context_window = []
        self.kappa_W = 2.0
        self.W_base = 50
        self.current_density = 0.0
        self.effective_learning_rate = 0.10
        self.auto_navegar_meta = True
        self.auto_registrar_place = True
        self.auto_mutar_omega = True
        self.place_bucket = 4
        self._objetos_vistos = []
        self._tipos_meta_buscados = ['comida']
        self.meta_recordada = None
        self.valencia_recurso = {}
        self.valencia_tasa = 0.15
        self.modelo_del_otro = {}
        self.otro_observaciones = 0
        self.stagnation_ticks = 0
        self.doubt_count = 0
        self.doubt_cooldown = 0
        self.status = "ACTIVA"
    
    def registrar_episodio(self, accion, recurso_nuevo, estado_q, contexto):
        """Registra un episodio significativo."""
        cambio = sum(abs(contexto.get(k, 0) - estado_q.get(k, 0)) for k in set(contexto) | set(estado_q))
        if cambio >= self.saliencia_umbral:
            self.episodios.append({
                "accion": accion,
                "recurso_nuevo": recurso_nuevo,
                "saliencia": cambio,
                "estado_q": estado_q,
                "contexto": contexto
            })
            if len(self.episodios) > self.max_episodios:
                self.episodios.pop(0)
    
    def actualizar_contexto(self, paso):
        """Actualiza la ventana de contexto (W(t))."""
        self.context_window.append(paso)
        W_t = self.W_base / (1 + self.kappa_W * self.current_density)
        while len(self.context_window) > W_t:
            self.context_window.pop(0)
    
    def densidad_contextual(self, N_active):
        """Calcula ρ(t) = |E_active| / (W(t) · N_active)."""
        W_t = max(1, self.W_base / (1 + self.kappa_W * self.current_density))
        if N_active > 0:
            self.current_density = len(self.context_window) / (W_t * N_active)
        return self.current_density
    
    def predecir_recompensa(self, accion, estado_q, metas_priorizadas=None):
        """Predice recompensa de una acción en un estado."""
        # Buscar episodios similares
        mejor_sig = 0.0
        for ep in self.episodios:
            if ep["accion"] == accion:
                sim = sum(ep["estado_q"].get(k, 0) * estado_q.get(k, 0) for k in set(ep["estado_q"]) & set(estado_q))
                mejor_sig = max(mejor_sig, sim)
        
        confianza = 1.0 if mejor_sig > 0.5 else 0.0
        bonus = mejor_sig if metas_priorizadas else 0.0
        
        return 0.0, confianza, bonus
    
    def razonar_meta(self, meta):
        """Razona sobre una meta usando memoria episódica."""
        for ep in self.episodios:
            if meta in str(ep.get("recurso_nuevo", "")):
                return ep["accion"], 1.0
        return None, 0.0
    
    def check_stagnation(self, agente=None):
        """Verifica si el agente está estancado."""
        historial = getattr(agente, 'historial_acciones', []) if agente else getattr(self, 'historial_acciones', [])
        if not historial or len(historial) < 20:
            return False
        recientes = historial[-20:]
        if len(set(recientes)) < 3:
            return True
        return False

    def handle_doubt(self, agente=None):
        """Maneja la duda (estancamiento)."""
        if agente:
            agente.doubt_cooldown = 10
            agente.doubt_count = getattr(agente, 'doubt_count', 0) + 1
        else:
            self.doubt_cooldown = 10
            self.doubt_count += 1