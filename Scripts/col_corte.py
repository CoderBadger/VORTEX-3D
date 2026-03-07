"""
Módulo: col_corte.py
Descripción: Módulo especializado en el post-procesamiento orientado al diseño 
normativo a corte de los elementos tipo columna del modelo espacial.
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

# ==============================================================================
#      MOTOR DE CÁLCULO DE ESTRIBOS EN COLUMNAS V2.0
#                                 (Norma NB1225001 / ACI 318-14)
# ==============================================================================

import math

# Diccionario global de barras (mm -> mm²)
BARRAS_COMERCIALES = { 
    6.0: 28.0, 8.0: 50.0, 9.5: 70.9, 10.0: 78.5, 12.0: 113.0, 16.0: 201.0, 
    20.0: 314.0, 25.0: 491.0, 32.0: 804.0 
}

# ==============================================================================
# MÓDULO 1: FUNCIONES DE CÁLCULO PURO
# ==============================================================================

def _calcular_diseno_corte_columna(f_c, f_y, Vu, Nu, b, h, d, d_est, d_long):
    """
    Realiza el cálculo de diseño a corte para columnas, devolviendo un diccionario
    con todos los resultados numéricos en (N, mm).
    
    Verifica simultáneamente los requisitos de NB 1225001 para:
    - Resistencia a Cortante (Vc, Vs)
    - Refuerzo Mínimo por Corte (NB 10.6.2.2)
    - Espaciamiento Máximo por Corte
    - Espaciamiento Máximo por Confinamiento (NB 25.7.2.1)
    """
    resultados = {'error': None}
    
    try:
        area_una_barra = BARRAS_COMERCIALES[d_est]
        Av = 2 * area_una_barra
        resultados['Av_mm2'] = Av
    except KeyError:
        resultados['error'] = f"Diámetro de estribo Ø{d_est} no es comercial."
        return resultados

    phi_corte = 0.75
    lambda_val = 1.0
    Ag = b * h
    
    # 1. Resistencia del Hormigón (Vc) - NB 22.5.6.1
    termino_axial = (1 + (Nu / (14 * Ag)))
    if termino_axial > 2.0:
        termino_axial = 2.0
    elif termino_axial < 0:
        termino_axial = 0.0 

    Vc = (lambda_val * math.sqrt(f_c) / 6) * termino_axial * b * d
    phi_Vc = phi_corte * Vc
    limite_estribos_min = 0.5 * phi_Vc
    
    resultados.update({
        'Ag_mm2': Ag, 'termino_axial': termino_axial, 'Vc_N': Vc, 
        'phi_Vc_N': phi_Vc, 'limite_estribos_min_N': limite_estribos_min
    })

    # 2. Verificar si se requieren estribos por cálculo - NB 10.6.2.1
    requiere_estribos_calculo = Vu >= limite_estribos_min
    resultados['requiere_estribos_calculo'] = requiere_estribos_calculo

    # 3. Calcular espaciamientos requeridos
    s_por_resistencia = float('inf')
    Vs = 0
    
    if Vu > phi_Vc:
        # A. Separación por Resistencia (s_res) - NB 22.5.10.1
        Vs = (Vu / phi_corte) - Vc
        
        Vs_max_limite = (2/3) * math.sqrt(f_c) * b * d
        if Vs > Vs_max_limite:
            resultados['error'] = "Sección de hormigón insuficiente (Vs > Vs,max)"
            return resultados
        
        # NB 22.5.10.5.3
        s_por_resistencia = (Av * f_y * d) / Vs if Vs > 1e-6 else float('inf')
    
    resultados.update({'Vs_N': Vs, 's_por_resistencia_mm': s_por_resistencia})

    # B. Separación por Armadura Mínima de Corte (s_min,shear) - NB 10.6.2.2
    # (Usando 1/16 = 0.0625, redondeado a 0.062)
    s_max_min_shear_a = (Av * f_y) / (0.062 * math.sqrt(f_c) * b) 
    
    # --- CAMBIO IMPORTANTE: NB usa 0.34 ---
    s_max_min_shear_b = (Av * f_y) / (0.34 * b)
    
    s_por_arm_minima_shear = min(s_max_min_shear_a, s_max_min_shear_b)
    
    resultados.update({
        's_max_min_shear_a_mm': s_max_min_shear_a,
        's_max_min_shear_b_mm': s_max_min_shear_b,
        's_por_arm_minima_shear_mm': s_por_arm_minima_shear
    })

    # C. Separación Máxima por Cortante (s_max,shear)
    Vs_limite_tabla = (1/3) * math.sqrt(f_c) * b * d
    if Vs <= Vs_limite_tabla: 
        s_max_por_magnitud_vs = min(d / 2, 600)
    else: 
        s_max_por_magnitud_vs = min(d / 4, 300)

    resultados.update({
        'Vs_limite_tabla_N': Vs_limite_tabla,
        's_max_por_magnitud_vs_mm': s_max_por_magnitud_vs
    })

    # D. Separación Máxima por Confinamiento (s_max,confin) - NB 25.7.2.1 
    # --- CAMBIO IMPORTANTE: NB usa 12 y 36 --- 
    s_max_confin_1 = 12 * d_long
    s_max_confin_2 = 36 * d_est
    s_max_confin_3 = min(b, h)
    s_max_confinamiento = min(s_max_confin_1, s_max_confin_2, s_max_confin_3)
    
    resultados.update({
        's_max_confin_1_mm': s_max_confin_1,
        's_max_confin_2_mm': s_max_confin_2,
        's_max_confin_3_mm': s_max_confin_3,
        's_max_confinamiento_mm': s_max_confinamiento
    })

    # 4. Decisión Final
    if requiere_estribos_calculo:
        s_final = min(s_por_resistencia, s_por_arm_minima_shear, s_max_por_magnitud_vs, s_max_confinamiento)
    else:
        s_final = s_max_confinamiento

    s_final_constructivo = math.floor(s_final / 10) * 10
    
    resultados.update({
        's_final_mm': s_final,
        's_final_constructivo_mm': s_final_constructivo
    })

    return resultados

# ==============================================================================
# MÓDULO 2: FUNCIONES DE GENERACIÓN DE MEMORIA
# ==============================================================================

def _generar_memoria_corte_columna(d_in, corte_res):
    """
    Genera la memoria de cálculo para el diseño a corte de la columna.
    (Versión con Fórmulas LaTeX y citaciones NB 1225001)
    """
    memoria = ["<h3>MÓDULO 2: DISEÑO A CORTE (COLUMNA NB 1225001)</h3>"]
    
    # Desempaquetar datos de entrada
    f_c = d_in['f_c']; b = d_in['b']; d = d_in['d']; h = d_in['h']
    Nu = d_in['Nu']; Vu = d_in['Vu']; d_est = d_in['d_est']; d_long = d_in['d_long']
    
    # Desempaquetar resultados
    phi_corte = 0.75
    Vc_kN = corte_res['Vc_N'] / 1000
    phi_Vc_kN = corte_res['phi_Vc_N'] / 1000
    limite_kN = corte_res['limite_estribos_min_N'] / 1000
    Ag = corte_res['Ag_mm2']
    termino_axial = corte_res['termino_axial']
    
    # --- CITACIÓN ACTUALIZADA ---
    memoria.append("<b>1. Resistencia del Hormigón (Vc) - (NB 22.5.6.1)</b>")
    memoria.append(f"Se utiliza la ecuación detallada para miembros con carga axial (Nu = {Nu/1000:.2f} kN):")
    
    memoria.append(r"$V_c = \frac{\lambda \sqrt{f'_c}}{6} \left(1 + \frac{N_u}{14 A_g}\right) b_w d$")
    memoria.append(f"$Término \\ Axial = \\left(1 + \\frac{{{Nu:.0f}}}{{14 \\times {Ag:.0f}}}\\right) = {termino_axial:.3f}$")
    memoria.append(f"$V_c = \\frac{{\\sqrt{{{f_c}}}}}{{{6}}} ({termino_axial:.3f}) \\times {b:.0f} \\times {d:.1f}$")
    memoria.append(f"$\\mathbf{{V_c = {corte_res['Vc_N']:.0f} \\text{{ N}} = {Vc_kN:.2f} \\text{{ kN}}}}$")
    memoria.append(f"$\\phi V_c = {phi_corte} \\times {Vc_kN:.2f} \\text{{ kN}} = \\mathbf{{{phi_Vc_kN:.2f} \\text{{ kN}}}}$")
    memoria.append("<br>")
    
    # --- CITACIÓN ACTUALIZADA ---
    memoria.append("<b>2. Verificación de Requisito de Estribos (NB 10.6.2.1)</b>")
    memoria.append("Se requieren estribos de corte si:")
    memoria.append(r"$V_u \geq 0.5 \cdot \phi V_c$")
    
    memoria.append(f"$Límite \\ (0.5 \\times \\phi V_c) = {limite_kN:.2f} \\text{{ kN}}$")
    memoria.append(f"Cortante Actuante (Vu): {Vu/1000:.2f} kN")

    if not corte_res['requiere_estribos_calculo']:
        memoria.append("<p style='color:blue;'>>> INFO: Vu < 0.5 * ΦVc. No se requieren estribos por cálculo de corte. Se diseñará por confinamiento.</p>")
    else:
        memoria.append("<p style='color:orange;'>>> ALERTA: Vu ≥ 0.5 * ΦVc. Se requieren estribos por cálculo de corte.</p>")
    
    memoria.append("<hr>")
    memoria.append("<h3>MÓDULO 3: CÁLCULO DE SEPARACIÓN DE ESTRIBOS</h3>")
    memoria.append(f"<i>Usando estribos Ø{int(d_est)}mm (2 ramas), Av = {corte_res['Av_mm2']:.2f} mm²</i>")
    
    if corte_res['requiere_estribos_calculo']:
        # --- CITACIÓN ACTUALIZADA ---
        memoria.append("<br><b>A. Separación por Resistencia (s_res) - (NB 22.5.10.1)</b>")
        if corte_res['Vs_N'] > 0:
            Vs_kN = corte_res['Vs_N'] / 1000
            s_res = corte_res['s_por_resistencia_mm']
            memoria.append(f"Vu ({Vu/1000:.2f} kN) > ΦVc ({phi_Vc_kN:.2f} kN). Se necesita Vs.")
            
            memoria.append(r"$V_s = \frac{V_u - \phi V_c}{\phi}$")
            memoria.append(f"$V_s = \\frac{{{Vu/1000:.2f} - {phi_Vc_kN:.2f}}}{{{phi_corte}}} = {Vs_kN:.2f} \\text{{ kN}}$")
            memoria.append(r"$s = \frac{A_v f_{yt} d}{V_s}$") # Esta es s_res
            memoria.append(f"$s_{{res}} = \\frac{{{corte_res['Av_mm2']:.2f} \\times {d_in['f_y']} \\times {d:.1f}}}{{{corte_res['Vs_N']:.0f}}}$")
            memoria.append(f"$\\mathbf{{s_{{res}} = {s_res:.1f} \\text{{ mm}}}}$")
        else:
            memoria.append("Vu ≤ ΦVc. No se requiere separación por resistencia (Vs=0).")
            memoria.append("$\\mathbf{s_{res} = \\infty}$")

        # --- CITACIÓN ACTUALIZADA ---
        memoria.append("<br><b>B. Separación por Armadura Mínima de Corte (s_min,shear) - (NB 10.6.2.2)</b>")
        s_min_a = corte_res['s_max_min_shear_a_mm']
        s_min_b = corte_res['s_max_min_shear_b_mm']
        s_min_shear = corte_res['s_por_arm_minima_shear_mm']
        
        memoria.append(r"$s_a = \frac{A_v f_{yt}}{(\sqrt{f'_c}/16) b_w}$") # Fórmula reordenada de
        memoria.append(f"$s_a = \\frac{{{corte_res['Av_mm2']:.2f} \\times {d_in['f_y']}}}{{(\\sqrt{{{d_in['f_c']}}}/16) \\times {b}}} = {s_min_a:.1f} \\text{{ mm}}$")
        
        # --- LÓGICA Y CITACIÓN ACTUALIZADA ---
        memoria.append(r"$s_b = \frac{A_v f_{yt}}{0.34 b_w}$")
        memoria.append(f"$s_b = \\frac{{{corte_res['Av_mm2']:.2f} \\times {d_in['f_y']}}}{{0.34 \\times {b}}} = {s_min_b:.1f} \\text{{ mm}}$")
        
        memoria.append(f"$\\mathbf{{s_{{min,shear}} = min({s_min_a:.1f}, {s_min_b:.1f}) = {s_min_shear:.1f} \\text{{ mm}}}}$")

        # --- CITACIÓN ELIMINADA (No estaba en el doc) ---
        memoria.append("<br><b>C. Separación Máxima por Cortante (s_max,shear)</b>")
        Vs_lim_kN = corte_res['Vs_limite_tabla_N'] / 1000
        Vs_kN = corte_res['Vs_N'] / 1000
        s_max_vs = corte_res['s_max_por_magnitud_vs_mm']
        
        # --- CORRECCIÓN BUG LATEX ---
        memoria.append(r"$Límite \ V_s = (1/3)\sqrt{f'_c} b d$")
        
        memoria.append(f"$Límite \\ V_s = (1/3)\\sqrt{{{f_c}}} \\times {b:.0f} \\times {d:.1f} = {Vs_lim_kN:.2f} \\text{{ kN}}$")
        
        if corte_res['Vs_N'] <= corte_res['Vs_limite_tabla_N']:
            memoria.append(f"$V_s \\ ({Vs_kN:.2f} \\text{{ kN}}) \\leq \\text{{Límite}} \\ ({Vs_lim_kN:.2f} \\text{{ kN}}) \\rightarrow s_{{max}} = min(d/2, 600mm)$")
        else: 
            memoria.append(f"$V_s \\ ({Vs_kN:.2f} \\text{{ kN}}) > \\text{{Límite}} \\ ({Vs_lim_kN:.2f} \\text{{ kN}}) \\rightarrow s_{{max}} = min(d/4, 300mm)$")
            
        memoria.append(f"$\\mathbf{{s_{{max,shear}} = {s_max_vs:.1f} \\text{{ mm}}}}$")
    
    # --- CITACIÓN Y LÓGICA ACTUALIZADA ---
    memoria.append("<br><b>D. Separación Máxima por Confinamiento (s_max,confin) - (NB 25.7.2.1)</b>")
    s_conf_1 = corte_res['s_max_confin_1_mm']
    s_conf_2 = corte_res['s_max_confin_2_mm']
    s_conf_3 = corte_res['s_max_confin_3_mm']
    s_confin = corte_res['s_max_confinamiento_mm']
    
    memoria.append(r"$s_1 = 12 \times \phi_{long}$")
    memoria.append(f"$s_1 = 12 \\times {d_long} = {s_conf_1:.1f} \\text{{ mm}}$")
    memoria.append(r"$s_2 = 36 \times \phi_{est}$")
    memoria.append(f"$s_2 = 36 \\times {d_est} = {s_conf_2:.1f} \\text{{ mm}}$")
    memoria.append(r"$s_3 = min(b, h)$")
    memoria.append(f"$s_3 = min({b:.0f}, {h:.0f}) = {s_conf_3:.1f} \\text{{ mm}}$")
    
    memoria.append(f"$\\mathbf{{s_{{max,confin}} = min({s_conf_1:.1f}, {s_conf_2:.1f}, {s_conf_3:.1f}) = {s_confin:.1f} \\text{{ mm}}}}$")
    
    memoria.append("<hr>")
    memoria.append("<h3>MÓDULO 4: DECISIÓN FINAL DE DISEÑO</h3>")
    
    s_final = corte_res['s_final_mm']
    s_final_const = corte_res['s_final_constructivo_mm']
    
    if corte_res['requiere_estribos_calculo']:
        memoria.append("<i>El espaciamiento debe cumplir todos los criterios (Resistencia, Mín. Corte, Máx. Corte, Confinamiento):</i>")
        memoria.append(r"$s_{final} = min(s_{res}, s_{min,shear}, s_{max,shear}, s_{max,confin})$")
        memoria.append(f"$s_{{final}} = min({corte_res['s_por_resistencia_mm']:.1f}, {corte_res['s_por_arm_minima_shear_mm']:.1f}, {corte_res['s_max_por_magnitud_vs_mm']:.1f}, {corte_res['s_max_confinamiento_mm']:.1f})$")
    else:
        memoria.append("<i>El espaciamiento solo debe cumplir el criterio de confinamiento:</i>")
        memoria.append(r"$s_{final} = s_{max,confin}$")
    
    memoria.append(f"$\\mathbf{{s_{{final}} = {s_final:.1f} \\text{{ mm}}}}$")
    memoria.append(f"Separación constructiva (múltiplo de 10mm inferior): <b>{s_final_const:.0f} mm</b>")
    
    memoria.append(f"<h2 style='color:green; border: 2px solid green; padding: 10px;'>Usar estribos: Ø{int(d_est)} @ {int(s_final_const)} mm</h2>")
    
    return memoria
# ==============================================================================
# MÓDULO 3: FUNCIÓN ORQUESTADORA PRINCIPAL
# ==============================================================================

def realizar_diseno_columna_corte(f_c, f_y, Vu_kN, Nu_kN, b_cm, h_cm, r_min_cm, 
                                 diametro_estribo, diametro_longitudinal):
    
    # (El inicio de la función está bien)
    datos_entrada = {
        'f_c': f_c, 'f_y': f_y,
        'b': b_cm * 10, 'h': h_cm * 10, 'r_min': r_min_cm * 10,
        'd_est': diametro_estribo, 'd_long': diametro_longitudinal,
        'Vu': Vu_kN * 1000, 'Nu': Nu_kN * 1000,
    }
    datos_entrada['d'] = datos_entrada['h'] - datos_entrada['r_min'] - datos_entrada['d_est'] - (datos_entrada['d_long'] / 2)

    # (La llamada a la función de cálculo está bien como la corregimos antes)
    corte_res = _calcular_diseno_corte_columna(
        f_c=datos_entrada['f_c'], 
        f_y=datos_entrada['f_y'], 
        Vu=datos_entrada['Vu'], 
        Nu=datos_entrada['Nu'], 
        b=datos_entrada['b'], 
        h=datos_entrada['h'], 
        d=datos_entrada['d'],
        d_est=datos_entrada['d_est'], 
        d_long=datos_entrada['d_long']
    )
    
    if corte_res.get('error'):
        memoria = [f"<h3>Error Crítico en Diseño a Corte</h3><p style='color:red;'><b>{corte_res['error']}</b></p>"]
        return {'resultados': {'error': corte_res['error']}, 'memoria': memoria}

    resultados_gui = {
        'separacion_final_cm': corte_res['s_final_constructivo_mm'] / 10,
        'diametro_estribo_mm': diametro_estribo
    }

    # (Aquí viene la generación de memoria)
    memoria = ["<h2>--- INICIO DEL REPORTE DE CÁLCULO: CORTE EN COLUMNA ---</h2>"]
    memoria.append("<h3>MÓDULO 1: PARÁMETROS INICIALES (Unidades en mm y N)</h3>")
    memoria.append(f"<b>Datos:</b> f'c={f_c} MPa, fy={f_y} MPa, Vu={Vu_kN} kN, Nu={Nu_kN} kN")
    memoria.append(f"<b>Geometría:</b> b={datos_entrada['b']} mm, h={datos_entrada['h']} mm")
    
    memoria.append("<br><b>Altura Efectiva (d)</b>")
    
    # --- CORRECCIÓN AQUÍ --- (Este era el primer error de tu screenshot)
    memoria.append(r"$d = h - r_{rec} - \phi_{est} - \frac{\phi_{l}}{2}$")
    
    memoria.append(f"$d = {datos_entrada['h']} - {datos_entrada['r_min']} - {datos_entrada['d_est']} - \\frac{{{datos_entrada['d_long']}}}{{2}}$")
    memoria.append(f"$\\mathbf{{d = {datos_entrada['d']:.2f} \\text{{ mm}}}}$")
    memoria.append("<hr>")
    
    memoria.extend(_generar_memoria_corte_columna(datos_entrada, corte_res))
    
    memoria.append("<h2>--- FIN DEL REPORTE ---</h2>")

    return {'resultados': resultados_gui, 'memoria': memoria}