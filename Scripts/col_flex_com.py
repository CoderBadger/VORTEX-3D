"""
Módulo: col_flex_com.py
Descripción: Rutinas de cálculo detallado para una columna individual. Procesa 
las fuerzas axiales y momentos biaxiales resultantes del análisis matricial 
para verificar estados de carga específicos.
"""

# -----------------------------------------------------------------------------
# VORTEX 3D - Análisis Estructural de Edificaciones 3D y Diseño Normativo 
# de Vigas y Columnas 
# Copyright (C) 2026 Diego Oliver Vargas Moya & Luis Alberto Ortiz Morales
#
# Este programa es software libre: puedes redistribuirlo y/o modificarlo
# bajo los términos de la Licencia Pública General GNU (GNU GPL) publicada
# por la Free Software Foundation, ya sea la versión 3 de la Licencia, o
# (a tu elección) cualquier versión posterior.
#
# Este programa se distribuye con la esperanza de que sea útil,
# pero SIN GARANTÍA ALGUNA; ni siquiera la garantía implícita
# MERCANTIL o de APTITUD PARA UN PROPÓSITO DETERMINADO.
# Consulta los detalles de la Licencia Pública General GNU para más
# información.
#
# Deberías haber recibido una copia de la Licencia Pública General GNU
# junto a este programa. En caso contrario, consulta
# <https://www.gnu.org/licenses/>.
# -----------------------------------------------------------------------------

import math

def generar_acero_automatico(b, h, rec, d_est, d_barra, n_h, n_b):
    """Genera una malla de acero perimetral con coordenadas (x, y) para cada barra."""
    area_barra = math.pi * (d_barra**2) / 4
    acero = []
    
    x_min = rec + d_est + d_barra / 2
    x_max = b - x_min
    y_min = rec + d_est + d_barra / 2
    y_max = h - y_min

    if n_h > 2:
        esp_h = (y_max - y_min) / (n_h - 1)
        for i in range(1, n_h - 1):
            y_i = y_min + i * esp_h
            acero.append({'area': area_barra, 'x': x_min, 'y': y_i})
            acero.append({'area': area_barra, 'x': x_max, 'y': y_i})

    if n_b >= 2:
        esp_b = (x_max - x_min) / (n_b - 1) if n_b > 1 else 0
        for i in range(n_b):
            x_i = x_min + i * esp_b
            acero.append({'area': area_barra, 'x': x_i, 'y': y_min})
            acero.append({'area': area_barra, 'x': x_i, 'y': y_max})
            
    return acero

def generar_acero_manual(b, d_barra, capas):
    """Genera el acero a partir de una lista de capas definida por el usuario."""
    area_barra = math.pi * (d_barra**2) / 4
    acero = []
    for num_barras_capa, d_capa in capas:
        if num_barras_capa == 1:
            acero.append({'area': area_barra, 'x': b / 2, 'y': d_capa})
        else:
            x_min = 50 
            x_max = b - 50
            for i in range(num_barras_capa):
                x_pos = x_min + i * (x_max - x_min) / (num_barras_capa - 1)
                acero.append({'area': area_barra, 'x': x_pos, 'y': d_capa})
    return acero

def calcular_phi(epsilon_t, fy):
    """Calcula el factor de reducción de resistencia (phi) según ACI 318-14 / NB 1225001."""
    Es = 200000.0
    ecu = 0.003
    ety = fy / Es
    et_limite = ety + ecu  # Límite normativo de tracción (ej: 0.0021 + 0.003 = 0.0051)
    
    if epsilon_t <= ety: 
        return 0.65
    elif epsilon_t >= et_limite: 
        return 0.90
    else: 
        # Interpolación exacta en la Zona de Transición
        return 0.65 + 0.25 * (epsilon_t - ety) / (et_limite - ety)

def calcular_punto_diagrama(c, fc, fy, b, h, acero_dist):
    """Función universal que calcula (Pn, Mn) para una profundidad 'c' dada."""
    Es, ecu = 200000.0, 0.003
    if fc <= 28: beta1 = 0.85
    else: beta1 = max(0.65, 0.85 - 0.05 * (fc - 28) / 7.0)
    a = beta1 * c
    if a > h: a = h
    Cc = 0.85 * fc * a * b
    Pn_acero, Mn_acero = 0.0, 0.0
    d_max = max(bar['d'] for bar in acero_dist) if acero_dist else h
    for barra in acero_dist:
        d_barra_i = barra['d']
        area_barra_i = barra['area']
        epsilon_s = ecu * (c - d_barra_i) / c if c > 1e-9 else -ecu
        esfuerzo_s = max(min(Es * epsilon_s, fy), -fy)
        fuerza_s = area_barra_i * esfuerzo_s
        Pn_acero += fuerza_s
        Mn_acero += fuerza_s * (h / 2.0 - d_barra_i)
    Pn = Cc + Pn_acero
    Mn = Cc * (h / 2.0 - a / 2.0) + Mn_acero
    epsilon_t = ecu * (d_max - c) / c if c > 1e-9 else float('inf')
    return (Mn, Pn, epsilon_t)

def generar_diagrama_interaccion(fc, fy, b, h, acero_dist_original, eje):
    if not acero_dist_original: return [], []
    
    acero_dist_calculo = []
    
    b_calc, h_calc = b, h
    if eje == 'fuerte':
        for barra in acero_dist_original:
            acero_dist_calculo.append({'area': barra['area'], 'd': barra['y']})
    else: # Eje débil
        b_calc, h_calc = h, b
        for barra in acero_dist_original:
            acero_dist_calculo.append({'area': barra['area'], 'd': barra['x']})

    c_valores = [h_calc * i / 100 for i in range(400, 0, -1)]
    c_valores.extend([h_calc * i / 1000 for i in range(100, 0, -1)])
    c_valores.extend([h_calc * i / 10000 for i in range(100, 0, -1)])
    puntos_nominales = []
    puntos_diseno = []
    for c in c_valores:
        Mn, Pn, epsilon_t = calcular_punto_diagrama(c, fc, fy, b_calc, h_calc, acero_dist_calculo)
        puntos_nominales.append((abs(Mn), Pn))
        phi = calcular_phi(epsilon_t, fy)
        puntos_diseno.append((abs(phi * Mn), phi * Pn))

    area_total_acero = sum(b['area'] for b in acero_dist_calculo)
    P0_compresion = 0.85 * fc * (b_calc * h_calc - area_total_acero) + fy * area_total_acero
    puntos_nominales.insert(0, (0, P0_compresion))
    P0_traccion = -fy * area_total_acero
    puntos_nominales.append((0, P0_traccion))
    Pn_diseno_max = 0.80 * (0.65 * P0_compresion)
    puntos_diseno_final = []
    for Mn_d, Pn_d in puntos_diseno:
        if Pn_d >= 0:
            puntos_diseno_final.append((Mn_d, min(Pn_d, Pn_diseno_max)))
        else:
            puntos_diseno_final.append((Mn_d, Pn_d))
    
    puntos_diseno_final.insert(0, (0, Pn_diseno_max))
    puntos_diseno_final.append((0, 0.9 * P0_traccion))
    return puntos_nominales, puntos_diseno_final