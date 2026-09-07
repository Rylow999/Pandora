# -*- coding: utf-8 -*-
"""sgm_homeostasis.py — Homeostasis: acople grafo-cuerpo.

V_grafo = media(vitalidad) × factor_cuerpo(food, health)
Interocepción: dolor, hambre, seguridad.
"""


class Homeostasis:
    """Homeostasis del agente."""
    
    def __init__(self, D=128):
        self.D = D
        self.V_grafo = 1.0
        self._hambre_real = 0.0
        self._amenaza = 0.0
        self._algo_enfrente = 0
        self._posicion_actual = None
        self._hay_gradiente = False
        self._gradiente_dir = (0, 0)
        self._config_grad = {"activo": False, "fuerza": 0.0}
        self._config_curio = {"activo": False, "fuerza": 0.0}
        self._inc_dirs = {}
        self.instinto_alimentacion = None
        self.umbral_hambre_food = 3.0
        self.instinto_umbral_carencia = 0.3
        self.instinto_fuerza_base = 0.5
        self.devaluar_umbral = 0.35
        self.instinto_interaccion_fuerza = 0.7
        self.beta_supervivencia = 2.0
        self.beta_otras_compo = 0.3
        self.reencare_fuerza = 0.8
        self.instinto_explorar_umbral = 3
        self.instinto_explorar_fuerza = 0.4
        self.acciones_movimiento = {1, 2, 3, 4}
        self.drive_noop = 0.0
        self.drive_noop_umbral = 1.5
        self.drive_noop_fuerza = 1.0
        self.drive_noop_tasa = 0.1
        self.drive_noop_descarga = 0.5
        self.instinto_desplazar_fuerza = 0.6
        self.necesidad_insatisfecha = False
        self.umbral_amenaza_dolor = 0.5
        self._fuerza_instinto_eat_override = None
        self._objetos_vistos = []
        self._tipos_meta_buscados = ['comida']
        self.meta_recordada = None
        self.auto_registrar_place = True
        self.auto_navegar_meta = True
        self.auto_mutar_omega = True
        self.place_bucket = 4
        self.mutacion_tasa = 0.05
    
    def actualizar(self, agente, food, health):
        """Actualiza V_grafo acoplando salud del cuerpo."""
        health = float(health) if health is not None else 20.0
        food = float(food)
        
        factor_cuerpo = max(0.05, health / 20.0)
        if agente.omega:
            self.V_grafo = (sum(agente.vitalidad) / len(agente.vitalidad)) * factor_cuerpo
        else:
            self.V_grafo = factor_cuerpo
        
        self._hambre_real = max(0.0, 1.0 - food / 20.0)
        agente.V_grafo = self.V_grafo
    
    def configurar_arbitro(self, agente):
        """Configura el agente con las señales internas."""
        agente._hambre_real = self._hambre_real
        agente._amenaza = self._amenaza
        agente._algo_enfrente = self._algo_enfrente
        agente._posicion_actual = self._posicion_actual
        agente._hay_gradiente = self._hay_gradiente
        agente._gradiente_dir = self._gradiente_dir
        agente._config_grad = self._config_grad
        agente._config_curio = self._config_curio
        agente._inc_dirs = self._inc_dirs