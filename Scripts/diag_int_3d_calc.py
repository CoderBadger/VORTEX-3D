"""
Módulo: diag_int_3d_calc.py
Descripción: Genera la superficie de interacción 3D para columnas 
rectangulares sometidas a flexo-compresión biaxial, utilizando el método de 
intersección de planos de falla.
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

import numpy as np
from col_flex_com import generar_diagrama_interaccion

def _crear_malla_matplotlib(puntos_2d_fuerte, puntos_2d_debil, num_contornos=40, num_puntos_contorno=40):
    """
    Función que genera los datos para la superficie 3D completa (compresión y tracción).
    """
    puntos_2d_fuerte.sort(key=lambda p: p[1])
    puntos_2d_debil.sort(key=lambda p: p[1])
    pn_fuerte = np.array([p[1] for p in puntos_2d_fuerte])
    mnx_fuerte = np.array([p[0] for p in puntos_2d_fuerte])
    pn_debil = np.array([p[1] for p in puntos_2d_debil])
    mny_debil = np.array([p[0] for p in puntos_2d_debil])
    
    if len(pn_fuerte) == 0:
        return (np.array([]), np.array([]), np.array([])), 0, 0

    pn_min, pn_max = (pn_fuerte[0], pn_fuerte[-1])
    mnx_max = np.max(mnx_fuerte) if len(mnx_fuerte) > 0 else 0
    mny_max = np.max(mny_debil) if len(mny_debil) > 0 else 0
    
    niveles_pn = np.linspace(pn_min, pn_max, num_contornos)
    angulos = np.linspace(0, 2 * np.pi, num_puntos_contorno)
    alpha = 1.5
    x, y, z = [], [], []

    for Pn_actual in niveles_pn:
        Mox = np.interp(Pn_actual, pn_fuerte, mnx_fuerte)
        Moy = np.interp(Pn_actual, pn_debil, mny_debil)
        
        if Mox < 1e-6 or Moy < 1e-6:
             for ang in angulos: 
                 x.append(0)
                 y.append(0)
                 z.append(Pn_actual / 1000)
             continue
        
        for ang in angulos:
            numerador = Mox * Moy
            denominador = ((Moy * abs(np.cos(ang)))**alpha + (Mox * abs(np.sin(ang)))**alpha)**(1/alpha)
            radio = numerador / denominador if denominador > 1e-9 else 0
            x.append(radio * np.cos(ang) / 1e6)
            y.append(radio * np.sin(ang) / 1e6)
            z.append(Pn_actual / 1000)

    X = np.array(x).reshape((num_contornos, num_puntos_contorno))
    Y = np.array(y).reshape((num_contornos, num_puntos_contorno))
    Z = np.array(z).reshape((num_contornos, num_puntos_contorno))

    return (X, Y, Z), pn_max/1000, max(mnx_max/1e6, mny_max/1e6)

def generar_superficie_interaccion_3d(fc, fy, b, h, acero_dist):
    if not acero_dist: return None, [], [], 0, 0
    puntos_nom_fuerte, puntos_dis_fuerte = generar_diagrama_interaccion(fc, fy, b, h, acero_dist, 'fuerte')
    puntos_nom_debil, puntos_dis_debil = generar_diagrama_interaccion(fc, fy, b, h, acero_dist, 'debil')
    
    malla_diseno_mpl, pn_max, mn_max = _crear_malla_matplotlib(puntos_dis_fuerte, puntos_dis_debil)
    
    return malla_diseno_mpl, puntos_dis_fuerte, puntos_dis_debil, pn_max, mn_max

def verificar_punto_numericamente(punto_demanda, puntos_dis_fuerte, puntos_dis_debil):
    """
    Verifica si un punto de demanda cae dentro de la superficie de interacción.
    Devuelve el estado ("Seguro" o "Falla") y el ratio Demanda/Capacidad.
    """
    pu, mux, muy = punto_demanda['p'], abs(punto_demanda['mx']), abs(punto_demanda['my'])

    # 1. Preparar los datos de capacidad de los diagramas 2D
    puntos_dis_fuerte.sort(key=lambda p: p[1])
    puntos_dis_debil.sort(key=lambda p: p[1])
    pn_fuerte = np.array([p[1] / 1000 for p in puntos_dis_fuerte])
    mnx_fuerte = np.array([p[0] / 1e6 for p in puntos_dis_fuerte])
    pn_debil = np.array([p[1] / 1000 for p in puntos_dis_debil])
    mny_debil = np.array([p[0] / 1e6 for p in puntos_dis_debil])
    
    # 2. Calcular la capacidad de la sección al nivel de carga Pu
    Mox_cap = np.interp(pu, pn_fuerte, mnx_fuerte)
    Moy_cap = np.interp(pu, pn_debil, mny_debil)

    if Mox_cap < 1e-6 or Moy_cap < 1e-6:
        return ("Falla", float('inf')) if (mux > 1e-6 or muy > 1e-6) else ("Seguro", 0.0)

    # 3. Calcular la capacidad resistente en la dirección del momento de demanda
    angulo_demanda = np.arctan2(muy, mux)
    alpha = 1.5
    numerador = Mox_cap * Moy_cap
    denominador = ((Moy_cap * abs(np.cos(angulo_demanda)))**alpha + (Mox_cap * abs(np.sin(angulo_demanda)))**alpha)**(1/alpha)
    Mn_capacidad = numerador / denominador if denominador > 1e-9 else 0
    
    # 4. Comparar demanda vs capacidad
    Mn_demanda = np.sqrt(mux**2 + muy**2)
    
    if Mn_demanda <= Mn_capacidad:
        estado = "Seguro"
    else:
        estado = "Falla"
        
    ratio = Mn_demanda / Mn_capacidad if Mn_capacidad > 1e-9 else float('inf')
    
    return estado, ratio
