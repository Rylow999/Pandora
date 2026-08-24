#!/usr/bin/env python3
"""
sgm_core_pulsiones.py — Plugins de pulsiones para el SGM.

Cada pulsión es un método que devuelve {accion: peso_crudo}.
El Arbitro combina estos vectores en un score final.

Filosofía:
- Cada pulsión es INDEPENDIENTE (no sabe de las otras)
- El Arbitro decide cómo combinarlas (modos, prioridades)
- La fase de percepción se ejecuta ANTES de las pulsiones
"""

import math, random


class Pulsion:
    """Base para todas las pulsiones. Cada una computa un vector de pesos."""
    
    def __init__(self, nombre, params=None):
        self.nombre = nombre
        self.params = params or {}
    
    def computar(self, agente, valid_actions):
        """Devuelve {accion: peso_crudo}. Sobreescribir en subclases."""
        return {}
    
    def _modo_factor(self, agente, modo_base=1.0, modo_sup=0.0):
        """Factor según modo: BASE -> modo_base, SUPERVIVENCIA -> modo_sup."""
        if getattr(agente, 'modo', 'BASE') == 'SUPERVIVENCIA':
            return modo_sup
        return modo_base


class PulsionPPR(Pulsion):
    """Pulsión base: PPR * vitalidad. Siempre activa."""
    
    def __init__(self):
        super().__init__('PPR', {'alpha': 0.15, 'iters': 10})
    
    def computar(self, agente, valid_actions):
        from experiments.sgm_ppr import ppr_route
        rank = ppr_route(agente.edges, agente._seed, agente._aff,
                        alpha=self.params['alpha'], iters=self.params['iters'])
        result = {}
        for a in valid_actions:
            if a in rank:
                result[a] = rank[a] * agente.vitalidad[a]
        return result


class PulsionInteraccion(Pulsion):
    """Instinto de interacción: pulsion a 'do' (instinto_alimentacion) cuando hay necesidad."""
    
    def __init__(self):
        super().__init__('Interaccion', {'fuerza': 0.7, 'beta_sup': 2.0})
    
    def computar(self, agente, valid_actions):
        result = {}
        accion_do = agente.instinto_alimentacion
        if accion_do is None or accion_do not in valid_actions:
            return result
        
        necesidad = max(agente._hambre_real, agente._amenaza)
        algo_enfrente = getattr(agente, '_algo_enfrente', 0)
        
        if algo_enfrente <= 0 or necesidad <= 0.05:
            return result
        
        fuerza = necesidad * self.params['fuerza']
        
        # En supervivencia: amplificado (control exclusivo del canal)
        if agente.modo == 'SUPERVIVENCIA':
            fuerza *= self.params['beta_sup']
        
        result[accion_do] = fuerza
        return result


class PulsionExploracion(Pulsion):
    """Instinto de exploración: pulsión a moverse hacia lo desconocido."""
    
    def __init__(self):
        super().__init__('Exploracion', {'fuerza': 0.4})
    
    def computar(self, agente, valid_actions):
        result = {}
        incertidumbre = agente.incertidumbre_acum
        umbral = agente.instinto_explorar_umbral
        
        if incertidumbre < umbral:
            return result
        
        # Configuración del adaptador
        config_curio = getattr(agente, '_config_curio', {})
        if not config_curio.get('activo', False):
            return result
        
        # Dirección más incierta
        inc_dirs = getattr(agente, '_inc_dirs', {})
        if not inc_dirs:
            return result
        
        try:
            dir_mas_inc = max(inc_dirs, key=inc_dirs.get)
        except (ValueError, KeyError):
            return result
        
        if dir_mas_inc in valid_actions and inc_dirs.get(dir_mas_inc, 0) > 0:
            factor = self._modo_factor(agente, modo_base=1.0, modo_sup=0.3)
            result[dir_mas_inc] = config_curio.get('fuerza', 0.4) * factor
        
        return result


class PulsionGradiente(Pulsion):
    """Gradiente homeostático: quimiotaxis hacia recurso visible."""
    
    def __init__(self):
        super().__init__('Gradiente', {'fuerza': 0.5})
    
    def computar(self, agente, valid_actions):
        result = {}
        
        en_carencia = agente.V_grafo < agente.instinto_umbral_carencia
        if not en_carencia:
            return result
        
        hay_gradiente = getattr(agente, '_hay_gradiente', False)
        config_grad = getattr(agente, '_config_grad', {})
        
        if not hay_gradiente or not config_grad.get('activo', False):
            return result
        
        grad_dir = getattr(agente, '_gradiente_dir', (0, 0))
        if grad_dir == (0, 0):
            return result
        
        accion_grad = agente._direccion_a_accion(grad_dir[0], grad_dir[1])
        if accion_grad in valid_actions:
            factor = self._modo_factor(agente, modo_base=1.0, modo_sup=0.3)
            result[accion_grad] = config_grad.get('fuerza', 0.5) * factor
        
        return result


class PulsionDriveNoop(Pulsion):
    """Drive de acción (SEEKING): empuje contra quedarse quieto (noop)."""
    
    def __init__(self):
        super().__init__('DriveNoop', {'fuerza': 1.0, 'umbral': 1.5})
    
    def computar(self, agente, valid_actions):
        result = {}
        drive_noop = agente.drive_noop
        umbral = agente.drive_noop_umbral
        
        if drive_noop < umbral:
            return result
        
        # Empuja a cualquier acción NO-noop
        factor = self._modo_factor(agente, modo_base=1.0, modo_sup=0.3)
        for a in valid_actions:
            if a != 0:  # no empujar noop
                result[a] = self.params['fuerza'] * (drive_noop / umbral) * factor
        
        return result


class PulsionReEncare(Pulsion):
    """Re-encare: moverse hacia el objetivo para posicionarse antes de interactuar."""
    
    def __init__(self):
        super().__init__('ReEncare', {'fuerza': 0.8})
    
    def computar(self, agente, valid_actions):
        result = {}
        necesidad = max(agente._hambre_real, agente._amenaza)
        
        if necesidad <= 0.05:
            return result
        
        target_dir = getattr(agente, '_target_dir', (0, 0))
        target_dist = getattr(agente, '_target_dist', 0)
        
        if target_dir == (0, 0):
            return result
        
        accion_do = agente.instinto_alimentacion
        mult = agente.beta_supervivencia if agente.modo == 'SUPERVIVENCIA' else 1.0
        
        # Si está lejos: moverse hacia el objetivo
        if target_dist > 1:
            target_dir = target_dir if len(target_dir) == 3 else (*target_dir, 0)
            accion_mov = agente._direccion_a_accion(target_dir[0], target_dir[1], target_dir[2])
            if accion_mov in valid_actions and accion_mov in agente.acciones_movimiento:
                result[accion_mov] = mult * self.params['fuerza'] * necesidad
        
        # Si está adyacente: interactuar
        elif target_dist == 1 and accion_do is not None and accion_do in valid_actions:
            result[accion_do] = mult * necesidad * agente.instinto_interaccion_fuerza
        
        return result


class PulsionNavegacionMeta(Pulsion):
    """Navegación a meta: ir a un lugar recordado donde se resolvió antes."""
    
    def __init__(self):
        super().__init__('NavegacionMeta', {'fuerza': 0.8})
    
    def computar(self, agente, valid_actions):
        result = {}
        
        if not getattr(agente, 'auto_navegar_meta', False):
            return result
        
        if agente._hambre_real <= 0.2:
            return result
        
        meta = agente.meta_recordada
        if meta is None:
            return result
        
        accion_meta = getattr(agente, '_accion_meta', None)
        algo_enfrente = getattr(agente, '_algo_enfrente', 0)
        
        if accion_meta is not None and accion_meta in valid_actions:
            # Solo si no hay nada accionable enfrente y hay supervivencia
            if algo_enfrente == 0 and agente.modo == 'SUPERVIVENCIA':
                result[accion_meta] = self.params['fuerza']
        
        return result


class PulsionAlimentacion(Pulsion):
    """Instinto de alimentación: pulsión a 'do' cuando hay carencia."""
    
    def __init__(self):
        super().__init__('Alimentacion', {'fuerza': 0.5, 'umbral_carencia': 0.3})
    
    def computar(self, agente, valid_actions):
        result = {}
        
        if agente.V_grafo >= self.params['umbral_carencia']:
            return result
        
        accion_do = agente.instinto_alimentacion
        if accion_do is None or accion_do not in valid_actions:
            return result
        
        fuerza = self.params['fuerza'] * (self.params['umbral_carencia'] - agente.V_grafo)
        result[accion_do] = fuerza
        return result


class PulsionDesplazamiento(Pulsion):
    """Desplazamiento reactivo: moverse cuando la necesidad no se satisface localmente."""
    
    def __init__(self):
        super().__init__('Desplazamiento', {'fuerza': 0.6, 'umbral': 0.35})
    
    def computar(self, agente, valid_actions):
        result = {}
        
        necesidad_insat = getattr(agente, 'necesidad_insatisfecha', False)
        if not necesidad_insat:
            return result
        
        for a in valid_actions:
            if a in agente.acciones_movimiento:
                result[a] = self.params['fuerza']
            else:
                result[a] = -self.params['fuerza'] * 0.5  # penalizar no-movimiento
        
        return result


class PulsionSeeking(Pulsion):
    """SEEKING homeostático: búsqueda de alimento cuando hay hambre real."""
    
    def __init__(self):
        super().__init__('Seeking', {'fuerza': 0.3, 'umbral_hambre': 0.5})
    
    def computar(self, agente, valid_actions):
        result = {}
        
        if agente._hambre_real <= self.params['umbral_hambre']:
            return result
        
        algo_enfrente = getattr(agente, '_algo_enfrente', 0)
        target_dir = getattr(agente, '_target_dir', (0, 0))
        
        # Solo si no hay nada enfrente ni objetivo
        if algo_enfrente != 0 or target_dir != (0, 0):
            return result
        
        # Empuja levemente a cualquier acción de movimiento
        for a in valid_actions:
            if a in agente.acciones_movimiento:
                result[a] = self.params['fuerza'] * agente._hambre_real
        
        return result


# ============ ARBITRO ============

class Arbitro:
    """
    Combina los vectores de pulsiones en un score final.
    
    Modos:
    - BASE: todas las pulsiones compiten por igual
    - SUPERVIVENCIA: pulsiones de supervivencia dominan, otras atenuadas
    """
    
    def __init__(self):
        self.pulsiones = []
        self.modos = {
            'BASE': {'PPR': 1.0, 'Interaccion': 1.0, 'Exploracion': 1.0, 
                     'Gradiente': 1.0, 'DriveNoop': 1.0, 'ReEncare': 1.0,
                     'NavegacionMeta': 1.0, 'Alimentacion': 1.0, 
                     'Desplazamiento': 1.0, 'Seeking': 1.0},
            'SUPERVIVENCIA': {'PPR': 0.5, 'Interaccion': 2.0, 'Exploracion': 0.3,
                              'Gradiente': 1.0, 'DriveNoop': 0.3, 'ReEncare': 1.5,
                              'NavegacionMeta': 1.0, 'Alimentacion': 1.0,
                              'Desplazamiento': 0.5, 'Seeking': 0.0},
        }
    
    def registrar(self, pulsion):
        self.pulsiones.append(pulsion)
    
    def computar(self, agente, valid_actions):
        """Devuelve {accion: score_final}."""
        modo = getattr(agente, 'modo', 'BASE')
        factores = self.modos.get(modo, self.modos['BASE'])
        
        # Acumulador de scores
        scores = {a: 0.0 for a in valid_actions}
        
        for pulsion in self.pulsiones:
            vector = pulsion.computar(agente, valid_actions)
            factor = factores.get(pulsion.nombre, 1.0)
            
            for a, peso in vector.items():
                if a in scores:
                    scores[a] += peso * factor
        
        return scores
    
    def elegir(self, agente, valid_actions):
        """Elige la acción con mayor score."""
        scores = self.computar(agente, valid_actions)
        
        if not scores:
            return valid_actions[0] if valid_actions else 0
        
        mejor = max(valid_actions, key=lambda a: scores.get(a, -float('inf')))
        
        # Si todas son negativas, elegir la primera viable
        if scores.get(mejor, 0) <= 0:
            viables = [a for a in valid_actions if agente.vitalidad[a] > 0.1]
            if viables:
                return viables[0]
        
        return mejor


def crear_arbitro_default():
    """Crea el arbitro con todas las pulsiones por defecto."""
    arbitro = Arbitro()
    arbitro.registrar(PulsionPPR())
    arbitro.registrar(PulsionInteraccion())
    arbitro.registrar(PulsionExploracion())
    arbitro.registrar(PulsionGradiente())
    arbitro.registrar(PulsionDriveNoop())
    arbitro.registrar(PulsionReEncare())
    arbitro.registrar(PulsionNavegacionMeta())
    arbitro.registrar(PulsionAlimentacion())
    arbitro.registrar(PulsionDesplazamiento())
    arbitro.registrar(PulsionSeeking())
    return arbitro