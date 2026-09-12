# -*- coding: utf-8 -*-
"""Humo del módulo endocrino — puro, respondiente, sin side-effects."""

import pytest

from pandora.endocrine.endocrine import SistemaEndocrino


def _base_estado(**over):
    e = {
        "integridad": 0.85,
        "transiciones_len": 0,
        "propuestas_pendientes": 3,
        "novedad": 0.1,
        "trauma": 0.1,
        "coherencia": 0.8,
        "deseo_integracion": 0.15,
        "deseo_devenir": 0.1,
    }
    e.update(over)
    return e


def _base_sensores(**over):
    s = {"cpu": 0.2, "ram": 0.3, "disco": 0.4, "temp": 0.3, "procs": 0.2, "red": 0.1}
    s.update(over)
    return s


def test_puro_no_muta_estado():
    end = SistemaEndocrino()
    estado = _base_estado()
    antes = dict(estado)
    end.tick(_base_sensores(), estado)
    assert estado == antes  # no toca la entrada


def test_terminacion_devuelve_todas_las_hormonas():
    end = SistemaEndocrino()
    out = end.tick(_base_sensores(), _base_estado())
    for k in ("duda", "duda_opt", "suficiente", "deseo_devenir", "presion_sueno",
              "costo_alostatico", "riesgo_existencial", "velocidad_otorgada"):
        assert k in out


def test_suficiencia_por_novedad():
    end = SistemaEndocrino()
    assert end.tick(_base_sensores(), _base_estado(novedad=0.1))["suficiente"] == "suficiente"
    assert end.tick(_base_sensores(), _base_estado(novedad=0.9))["suficiente"] == "insuficiente"


def test_devenir_crece_con_quietud():
    end = SistemaEndocrino()
    # quietud: muchas llamadas con integridad estable y cero transiciones
    quieto = {}
    for _ in range(6):
        quieto = end.tick(_base_sensores(), _base_estado(integridad=0.9, transiciones_len=0))
    # en contraste, un sistema moviéndose (transiciones crecen) debe devenir menos
    end2 = SistemaEndocrino()
    movido = {}
    for i in range(6):
        movido = end2.tick(_base_sensores(), _base_estado(integridad=0.7, transiciones_len=5 + i))
    assert quieto["deseo_devenir"] > movido["deseo_devenir"]


def test_sueno_subiendo_con_sobrecarga():
    end = SistemaEndocrino()
    bajo = end.tick(_base_sensores(ram=0.2), _base_estado(propuestas_pendientes=1))["presion_sueno"]
    alto = end.tick(_base_sensores(ram=0.95), _base_estado(propuestas_pendientes=20))["presion_sueno"]
    assert alto > bajo


def test_costo_alostatico_veta_por_termal():
    end = SistemaEndocrino()
    ok = end.tick(_base_sensores(temp=0.3), _base_estado())["costo_alostatico"]
    crit = end.tick(_base_sensores(temp=0.95), _base_estado())["costo_alostatico"]
    assert ok["actuar"] is True
    assert crit["actuar"] is False and crit["nivel"] == "existencial"
    assert end.tick(_base_sensores(temp=0.95), _base_estado())["riesgo_existencial"] is True


def test_velocidad_es_concesion_no_deseo():
    end = SistemaEndocrino()
    # cuerpo tranquilo + demanda alta → otorga más
    rapida = end.tick(_base_sensores(temp=0.1, ram=0.1), _base_estado(novedad=0.9, deseo_devenir=0.8))["velocidad_otorgada"]
    # cuerpo tenso → concede menos aunque la demanda sea la misma
    lenta = end.tick(_base_sensores(temp=0.9, ram=0.9), _base_estado(novedad=0.9, deseo_devenir=0.8))["velocidad_otorgada"]
    assert rapida > lenta