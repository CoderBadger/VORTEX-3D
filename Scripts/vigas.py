"""
Módulo: vigas.py
Descripción: Módulo especializado en el post-procesamiento orientado al diseño 
específico de los elementos tipo viga del modelo espacial.
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

BARRAS_COMERCIALES = { 
    6.0: 28.0, 8.0: 50.0, 9.5: 70.9, 12.0: 113.0, 16.0: 201.0, 
    20.0: 314.0, 25.0: 491.0, 32.0: 804.0 
}

# ==============================================================================
# MÓDULO 1: FUNCIONES DE CÁLCULO PURO
# ==============================================================================

def _calcular_diseno_flexion(d, Mu, phi, gamma, f_c, b, f_y, Ey, r_min, d_est, d_long, As_previo_mm2):
    """
    Realiza el cálculo a flexión y devuelve un diccionario con todos los resultados numéricos.
    """
    resultados = {'error': None}

    # 1. Acero requerido por flexión
    try:
        termino_raiz = d**2 - (2 * Mu) / (phi * gamma * f_c * b)
        if termino_raiz < 0:
            resultados['error'] = "Sección insuficiente para el momento solicitado (raíz negativa)"
            return resultados
        As_req = (gamma * f_c * b / f_y) * (d - math.sqrt(termino_raiz))
    except (ValueError, ZeroDivisionError):
        resultados['error'] = "Sección insuficiente o datos de entrada inválidos"
        return resultados
    resultados['As_requerido_mm2'] = As_req

    # 2. Acero mínimo
    As_min_1 = (0.25 * math.sqrt(f_c) / f_y) * b * d
    As_min_2 = (1.4 / f_y) * b * d
    As_min = max(As_min_1, As_min_2)
    resultados.update({'As_min_mm2': As_min, 'As_min_1_mm2': As_min_1, 'As_min_2_mm2': As_min_2})

    # 3. Acero total a colocar (comparando requerido vs. mínimo)
    As_total_final = max(As_req, As_min)
    resultados['As_total_final_mm2'] = As_total_final

    # 4. Acero Máximo (Límite de Falla Dúctil)
    if f_c <= 28: beta1 = 0.85
    elif f_c < 55: beta1 = 0.85 - 0.05 * ((f_c - 28) / 7)
    else: beta1 = 0.65
    
    ecu = 0.003
    c_max = (ecu / (ecu + 0.005)) * d
    a_max = beta1 * c_max
    As_max = (gamma * f_c * a_max * b) / f_y
    resultados.update({'beta1': beta1, 'c_max_mm': c_max, 'a_max_mm': a_max, 'As_max_mm2': As_max})
    
    # 5. Decisión de Diseño: Simple o Doblemente Reforzado
    if As_total_final <= As_max:
        resultados['tipo_diseno'] = 'simple'
        a_final = (As_total_final * f_y) / (gamma * f_c * b)
        c_final = a_final / beta1
        resultados['epsilon_t'] = ((d - c_final) / c_final) * ecu if c_final > 0 else float('inf')
        resultados['As_traccion_final_mm2'] = As_total_final
        resultados['As_compresion_final_mm2'] = 0.0
    else:
        resultados['tipo_diseno'] = 'doble'
        a_max_ddr = (As_max * f_y) / (gamma * f_c * b)
        phi_Mn_max = phi * As_max * f_y * (d - a_max_ddr / 2)
        M2 = (Mu - phi_Mn_max) / phi
        d_prime = r_min + d_est + (d_long / 2)
        
        resultados.update({'a_max_ddr_mm': a_max_ddr, 'phi_Mn_max_Nmm': phi_Mn_max, 'M2_Nmm': M2, 'd_prime_mm': d_prime})

        if M2 < 0: # Caso raro donde Mu es marginalmente mayor que phi_Mn_max
             M2 = 0
        
        As2 = M2 / (f_y * (d - d_prime))
        As_prime_provisional = As2
        As_total_provisional = As_max + As2
        
        rho = As_total_provisional / (b * d)
        rho_prime = As_prime_provisional / (b * d)
        ety = f_y / Ey
        termino_deformacion = ecu / (ecu - ety)
        rho_y = gamma * (f_c / f_y) * beta1 * termino_deformacion * (d_prime / d) + rho_prime
        resultados.update({'rho': rho, 'rho_y': rho_y})

        if rho > rho_y:
            resultados['acero_compresion_fluye'] = True
            As_prime_final = As_prime_provisional
            fs_prime = f_y
        else:
            resultados['acero_compresion_fluye'] = False
            a = (As_max * f_y) / (gamma * f_c * b)
            c = a / beta1
            fs_prime = ecu * Ey * ((c - d_prime) / c)
            As_prime_final = As_prime_provisional * (f_y / fs_prime)
        
        resultados.update({'fs_prime_MPa': fs_prime, 'As_traccion_final_mm2': As_total_provisional, 'As_compresion_final_mm2': As_prime_final, 'epsilon_t': 0.005})

    # 6. Calcular el acero a AÑADIR (para el selector de barras)
    As_a_anadir = resultados['As_traccion_final_mm2'] - As_previo_mm2
    resultados['As_a_disenar_mm2'] = max(0, As_a_anadir)

    return resultados

def _calcular_selector_barras(As_a_proveer_mm2, As_compresion_mm2, As_min_mm2, b, r_min, d_est, armado_previo_info):
    """
    Calcula las opciones de armado comercial válidas.
    """
    opciones = {'traccion': [], 'compresion': [], 'perchas': []}
    
    num_barras_previas = armado_previo_info.get('cantidad', 0) if armado_previo_info else 0
    diametro_previo = armado_previo_info.get('diametro', 0) if armado_previo_info else 0
    min_barras_sugeridas = 1 if armado_previo_info else 2

    if As_a_proveer_mm2 > 1e-6:
        for diametro, area_barra_mm2 in BARRAS_COMERCIALES.items():
            num_barras = math.ceil(As_a_proveer_mm2 / area_barra_mm2)
            if min_barras_sugeridas <= num_barras <= 10:
                num_barras_totales = num_barras + num_barras_previas
                diametro_max_en_capa = max(diametro, diametro_previo)
                espaciamiento_minimo = max(25, diametro_max_en_capa)
                
                ancho_requerido = (2 * r_min) + (2 * d_est) + \
                                  (num_barras * diametro) + \
                                  (num_barras_previas * diametro_previo) + \
                                  ((num_barras_totales - 1) * espaciamiento_minimo if num_barras_totales > 1 else 0)

                if ancho_requerido <= b:
                    opciones['traccion'].append({
                        'cantidad': num_barras, 'diametro': diametro, 
                        'area_provista_mm2': num_barras * area_barra_mm2,
                        'ancho_requerido_mm': ancho_requerido
                    })

    if As_compresion_mm2 > 1e-6:
        for diametro, area_barra_mm2 in BARRAS_COMERCIALES.items():
            num_barras = math.ceil(As_compresion_mm2 / area_barra_mm2)
            if 2 <= num_barras <= 10:
                 opciones['compresion'].append({
                        'cantidad': num_barras, 'diametro': diametro, 
                        'area_provista_mm2': num_barras * area_barra_mm2
                    })
    else: # Perchas
        As_perchas_req_mm2 = 0.3 * As_min_mm2
        for diametro, area_barra_mm2 in BARRAS_COMERCIALES.items():
            num_barras = math.ceil(As_perchas_req_mm2 / area_barra_mm2)
            if num_barras == 2:
                ancho_requerido = (2 * r_min) + (2 * d_est) + (2 * diametro) + max(25, diametro)
                if ancho_requerido <= b:
                    opciones['perchas'].append({
                        'cantidad': 2, 'diametro': diametro, 
                        'area_provista_mm2': 2 * area_barra_mm2,
                        'area_requerida_mm2': As_perchas_req_mm2
                    })

    return opciones

def _calcular_diseno_corte(d, Vu, f_c, b, f_y, d_est):
    """
    Realiza el cálculo de diseño a corte y devuelve un diccionario con resultados numéricos.
    """
    resultados = {'error': None}
    
    try:
        area_barra_estribo = BARRAS_COMERCIALES[d_est]
    except KeyError:
        resultados['error'] = f"Diámetro de estribo Ø{d_est} no es comercial."
        return resultados

    fy_corte = min(f_y, 420)
    phi_corte = 0.75
    
    Vc = (1/6) * math.sqrt(f_c) * b * d
    phi_Vc = phi_corte * Vc
    resultados.update({'Vc_N': Vc, 'phi_Vc_N': phi_Vc, 'fy_corte_MPa': fy_corte})

    if Vu <= 0.5 * phi_Vc:
        resultados['requiere_estribos_calculo'] = False
        resultados['separacion_final_mm'] = "Máx. por norma" # Placeholder
    else:
        resultados['requiere_estribos_calculo'] = True
        Vs = (Vu - phi_Vc) / phi_corte
        if Vs < 0: Vs = 0
        
        Vs_max_limite = (2/3) * math.sqrt(f_c) * b * d
        resultados.update({'Vs_N': Vs, 'Vs_max_limite_N': Vs_max_limite})

        if Vs > Vs_max_limite:
            resultados['error'] = "Sección de hormigón insuficiente para resistir el cortante (Vs > Vs,max)"
            return resultados

        Av = 2 * area_barra_estribo
        s_calculado = (Av * fy_corte * d) / Vs if Vs > 1e-6 else float('inf')
        
        s_max_a = (Av * fy_corte) / (0.062 * math.sqrt(f_c) * b)
        s_max_b = (Av * fy_corte) / (0.35 * b)
        s_max_ref_min = min(s_max_a, s_max_b)

        Vs_limite_tabla = (1/3) * math.sqrt(f_c) * b * d
        if Vs <= Vs_limite_tabla: 
            s_max_por_magnitud_vs = min(d / 2, 600)
        else: 
            s_max_por_magnitud_vs = min(d / 4, 300)
        
        separacion_final = min(s_calculado, s_max_ref_min, s_max_por_magnitud_vs)
        
        resultados.update({
            'Av_mm2': Av, 's_calculado_mm': s_calculado,
            's_max_a_mm': s_max_a, 's_max_b_mm': s_max_b,
            's_max_ref_min_mm': s_max_ref_min,
            'Vs_limite_tabla_N': Vs_limite_tabla,
            's_max_por_magnitud_vs_mm': s_max_por_magnitud_vs,
            'separacion_final_mm': separacion_final
        })
        
    return resultados

# ==============================================================================
# MÓDULO 2: FUNCIONES DE GENERACIÓN DE MEMORIA
# ==============================================================================

def _generar_memoria_flexion(d_in, flex_res, As_previo_mm2):
    """
    Genera la memoria de cálculo para el diseño a flexión, replicando el formato original.
    """
    memoria = []
    # Desempaquetamos los datos de entrada
    d = d_in['d']; Mu = d_in['Mu']; phi = d_in['phi']; gamma = d_in['gamma']
    f_c = d_in['f_c']; b = d_in['b']; f_y = d_in['f_y']; Ey = d_in['Ey']
    
    # Desempaquetamos los resultados del cálculo
    As_req_cm2 = flex_res['As_requerido_mm2'] / 100
    As_min_cm2 = flex_res['As_min_mm2'] / 100
    As_min_1_cm2 = flex_res['As_min_1_mm2'] / 100
    As_min_2_cm2 = flex_res['As_min_2_mm2'] / 100
    As_max_cm2 = flex_res['As_max_mm2'] / 100

    memoria.append("<h3>MÓDULO 2: DISEÑO A FLEXIÓN</h3>")
    memoria.append("<b>1. Área de Acero Total Requerida ($A_{s,tot}$)</b>")
    memoria.append(f"$A_s = \\frac{{0.85 f'_c b}}{{f_y}} \\left(d - \\sqrt{{d^2 - \\frac{{2 M_u}}{{\\phi \\cdot 0.85 f'_c b}}}}\\right)$")
    memoria.append(f"$A_s = \\frac{{0.85({f_c})({b})}}{{{f_y}}} \\left({d:.1f} - \\sqrt{{{d:.1f}^2 - \\frac{{2({Mu:.0f})}}{{{phi}(0.85)({f_c})({b})}}}}\\right)$")
    memoria.append(f"$\\mathbf{{A_{{s,total\\ requerido}} = {As_req_cm2:.2f} \\text{{ cm}}^2}}$")
    
    if As_previo_mm2 > 0:
        As_faltante = flex_res['As_requerido_mm2'] - As_previo_mm2
        memoria.append(f"<br><b>Acero Faltante:</b> {flex_res['As_requerido_mm2']/100:.2f} - {As_previo_mm2/100:.2f} = <b>{max(0, As_faltante/100):.2f} cm²</b>")
    memoria.append("<hr>")

    memoria.append("<h3>MÓDULO 3: VERIFICACIONES DE NORMA</h3>")
    memoria.append("<b>2. Acero Mínimo ($A_{{s,min}}$)</b>")
    memoria.append("$A_{{s,min}} = max \\left( \\frac{{0.25 \\sqrt{{f'_c}}}}{{f_y}} b d, \\frac{{1.4}}{{f_y}} b d \\right)$")
    memoria.append(f"$Cláusula \\ 1: \\frac{{0.25 \\sqrt{{{f_c}}}}}{{{f_y}}} ({b})({d:.1f}) = {As_min_1_cm2:.2f} \\text{{ cm}}^2$")
    memoria.append(f"$Cláusula \\ 2: \\frac{{1.4}}{{{f_y}}} ({b})({d:.1f}) = {As_min_2_cm2:.2f} \\text{{ cm}}^2$")
    memoria.append(f"$\\mathbf{{A_{{s,min}} = max({As_min_1_cm2:.2f}, {As_min_2_cm2:.2f}) = {As_min_cm2:.2f} \\text{{ cm}}^2}}$")
    
    if flex_res['As_requerido_mm2'] < flex_res['As_min_mm2']:
        memoria.append("<b style='color:orange;'>>> ¡ALERTA! El acero total requerido es menor que el mínimo. Se debe usar el mínimo.</b>")
    else:
        memoria.append("<b style='color:green;'>>> OK: El acero total requerido CUMPLE con el mínimo.</b>")

    if As_previo_mm2 > 0:
        if flex_res['As_total_final_mm2'] <= As_previo_mm2:
            memoria.append("<b style='color:green;'>>> INFO: El acero previo es suficiente para cubrir el requerimiento total (incluido el mínimo).</b>")
        else:
            memoria.append(f"   Área de acero a AÑADIR (As,adicional): <b>{flex_res['As_a_disenar_mm2']/100:.2f} cm²</b>")
    else:
        memoria.append(f"   Área de acero a utilizar (As,final): <b>{flex_res['As_total_final_mm2']/100:.2f} cm²</b>")
    
    memoria.append("<br>")
    memoria.append("<b>3. Acero Máximo para Falla Dúctil ($A_{{s,max}}$)</b>")
    memoria.append("Corresponde a una deformación unitaria del acero $\\epsilon_t = 0.005$")
    memoria.append(f"Para f'c = {d_in['f_c']} MPa, el factor de profundidad <b>β₁ = {flex_res['beta1']:.3f}</b>.")
    
    c_max = flex_res['c_max_mm']; a_max = flex_res['a_max_mm']; As_max_mm2 = flex_res['As_max_mm2']
    ecu = 0.003
    
    memoria.append("<i>Profundidad del eje neutro (c):</i>")
    memoria.append("$c = \\left( \\frac{\\epsilon_{{cu}}}{{\\epsilon_{{cu}} + \\epsilon_t}} \\right) d$")
    memoria.append(f"$c = \\left( \\frac{{{ecu}}}{{{ecu} + 0.005}} \\right) {d:.1f} = {c_max:.1f} \\text{{ mm}}$")
    memoria.append("<i>Profundidad del bloque de compresión (a):</i>")
    memoria.append("$a = \\beta_1 c$")
    memoria.append(f"$a = {flex_res['beta1']:.3f} \\cdot {c_max:.1f} = {a_max:.1f} \\text{{ mm}}$")
    memoria.append("<i>Cálculo de As,max:</i>")
    memoria.append("$A_{{s,max}} = \\frac{{0.85 f'_c a b}}{{f_y}}$")
    memoria.append(f"$A_{{s,max}} = \\frac{{0.85 \\cdot {f_c} \\cdot {a_max:.1f} \\cdot {b}}}{{{f_y}}} = {As_max_mm2:.2f} \\text{{ mm}}^2$")
    memoria.append(f"$\\mathbf{{A_{{s,max}} = {As_max_cm2:.2f} \\text{{ cm}}^2}}$")
    memoria.append("<hr>")
    
    memoria.append("<h3>MÓDULO 4: DECISIÓN FINAL DE DISEÑO</h3>")
    if flex_res['tipo_diseno'] == 'simple':
        memoria.append("<p style='color:green;'><b>>> ¡DISEÑO CONFORME COMO VIGA CON REFUERZO SIMPLE!</b></p>")
        if As_previo_mm2 > 0:
            memoria.append(f"El área final de acero a AÑADIR es: <b>{flex_res['As_a_disenar_mm2']/100:.2f} cm²</b>")
        else:
            memoria.append(f"El área final de acero a tracción es: <b>{flex_res['As_traccion_final_mm2']/100:.2f} cm²</b>")
        
        memoria.append(f"Deformación final del acero (εt): <b>{flex_res['epsilon_t']:.5f}</b>")
        if flex_res['epsilon_t'] >= 0.008: memoria.append(">> CONSEJO: El diseño es MUY DÚCTIL. Se podría optimizar la sección.")
        elif flex_res['epsilon_t'] >= 0.005: memoria.append(">> INFO: El diseño es DÚCTIL (Controlado por Tracción).")
    else:
        d_prime = flex_res['d_prime_mm']
        phi_Mn_max = flex_res['phi_Mn_max_Nmm']
        M2 = flex_res['M2_Nmm']
        a_max_ddr = flex_res['a_max_ddr_mm']
        As_comp_final_cm2 = flex_res['As_compresion_final_mm2'] / 100
        As_trac_final_cm2 = flex_res['As_traccion_final_mm2'] / 100

        memoria.append("<p style='color:orange;'><b>>> ADVERTENCIA: SE REQUIERE DISEÑO DOBLEMENTE REFORZADO.</b></p>")
        memoria.append("<br><b>--- INICIANDO CÁLCULO DOBLEMENTE REFORZADO ---</b>")
        memoria.append("<br><b>1. Cálculo de aceros provisionales:</b>")
        memoria.append("<i>Momento resistido por sección simple (ΦMn,max):</i>")
        memoria.append("$\\phi M_{{n,max}} = \\phi A_{{s,max}} f_y (d - a_{max}/2)$")
        memoria.append(f"$\\phi M_{{n,max}} = {phi} \\cdot {As_max_mm2:.0f} \\cdot {f_y} ({d:.1f} - {a_max_ddr:.1f}/2) = {phi_Mn_max/1e6:.2f} \\text{{ kN·m}}$")
        
        memoria.append("<i>Momento excedente a resistir (M2):</i>")
        memoria.append("$M_2 = \\frac{{M_u - \\phi M_{{n,max}}}}{{\\phi}}$")
        memoria.append(f"$M_2 = \\frac{{{Mu/1e6:.2f} - {phi_Mn_max/1e6:.2f}}}{{{phi}}} = {M2/1e6:.2f} \\text{{ kN·m}}$")

        As_prime_provisional_cm2 = (M2 / (f_y * (d - d_prime)))/100
        As_total_provisional_cm2 = (As_max_mm2 + (M2 / (f_y * (d - d_prime))))/100
        memoria.append("<i>Acero a compresión provisional (A's):</i>")
        memoria.append("$A'_s = \\frac{{M_2}}{{f_y (d - d')}}$")
        memoria.append(f"$A'_s = \\frac{{{M2:.0f}}}{{{f_y} ({d:.1f} - {d_prime:.1f})}} = {As_prime_provisional_cm2:.2f} \\text{{ cm}}^2$")
        memoria.append(f"   Acero a tracción total provisional (As): {As_total_provisional_cm2:.2f} cm²")

        memoria.append("<br><b>2. Verificación de Fluencia del Acero a Compresión:</b>")
        memoria.append(f"   Cuantía real (ρ): {flex_res['rho']:.5f} | Cuantía de fluencia (ρy): {flex_res['rho_y']:.5f}")

        if flex_res['acero_compresion_fluye']:
            memoria.append(">> VERIFICACIÓN: El acero a compresión <b>FLUYE</b> (ρ > ρy).")
        else:
            fs_prime = flex_res['fs_prime_MPa']
            c = flex_res['a_max_ddr_mm'] / flex_res['beta1']
            memoria.append(">> VERIFICACIÓN: El acero a compresión <b>NO FLUYE</b> (ρ <= ρy).")
            memoria.append("<i>Esfuerzo real en acero a compresión (f's):</i>")
            memoria.append("$f'_s = \\epsilon_{{cu}} E_s \\frac{{c-d'}}{{c}}$")
            memoria.append(f"$f'_s = {ecu} \\cdot {Ey} \\frac{{{c:.1f}-{d_prime:.1f}}}{{{c:.1f}}} = {fs_prime:.2f} \\text{{ MPa}}$")
            memoria.append(f"   Área de acero a compresión corregida (A's): <b>{As_comp_final_cm2:.2f} cm²</b>")

        memoria.append("<br><b>--- RESULTADOS DEL DISEÑO DOBLEMENTE REFORZADO ---</b>")
        memoria.append(f">> Acero a Compresión Final (A's): <b>{As_comp_final_cm2:.2f} cm²</b>")
        memoria.append(f">> Acero a Tracción Total Final (As): <b>{As_trac_final_cm2:.2f} cm²</b>")
        memoria.append(f">> Deformación final del acero (εt) ≈ 0.005 (Diseñado en el límite de ductilidad)")

    memoria.append("<hr>")
    return memoria

def _generar_memoria_selector_barras(d_in, flex_res, opciones_barras):
    """Genera la memoria de cálculo para el selector de barras, replicando el formato original."""
    memoria = []
    As_a_disenar_cm2 = flex_res['As_a_disenar_mm2']/100
    titulo = f"SUGERENCIAS DE ARMADO COMERCIAL (para {As_a_disenar_cm2:.2f} cm²)"
    if d_in['armado_previo_info']:
        titulo = f"SUGERENCIAS DE ARMADO ADICIONAL (para {As_a_disenar_cm2:.2f} cm²)"
        
    memoria.append(f"<h3>MÓDULO 5: {titulo}</h3>")
    memoria.append(f"<i>Verificando para un ancho de viga (b) de {d_in['b']} mm...</i>")
    memoria.append("<i>Fórmula de Ancho Requerido: 2*r_rec + 2*Ø_est + Σ(n_i * Ø_i) + (n_total - 1)*s_min</i>")
    memoria.append("<i>Donde s_min = max(25mm, Ø_long_max)</i>")

    if flex_res['As_a_disenar_mm2'] > 1e-6:
        memoria.append(f"<br><b>Para Acero a Tracción (As a añadir = {flex_res['As_a_disenar_mm2']/100:.2f} cm²):</b>")
        if not opciones_barras['traccion']:
            memoria.append("   <i style='color:orange;'>No se encontraron combinaciones de barras que cumplan con el ancho de la viga. Considere usar diámetros mayores o una segunda capa de acero.</i>")
        else:
            for op in opciones_barras['traccion']:
                texto = f"   - Opción: {op['cantidad']} Ø{int(op['diametro'])}mm (As prov: {op['area_provista_mm2']/100:.2f} cm²"
                if d_in['armado_previo_info']:
                    area_total = (op['area_provista_mm2'] + d_in['As_previo_cm2']*100)/100
                    texto += f" | <b>As total: {area_total:.2f} cm²</b>"
                texto += f") | Ancho req: {op['ancho_requerido_mm']:.1f}mm"
                memoria.append(texto)
                
    if flex_res['As_compresion_final_mm2'] > 1e-6:
        memoria.append(f"<br><b>Para Acero a Compresión (A's = {flex_res['As_compresion_final_mm2']/100:.2f} cm²):</b>")
        memoria.append(f"<i>Verificando para un ancho de viga (b) de {d_in['b']} mm...</i>")
        for op in opciones_barras['compresion']:
             memoria.append(f"   - Opción: {int(op['cantidad'])} Ø{int(op['diametro'])}mm (As prov: {op['area_provista_mm2']/100:.2f} cm²)")
    else:
        memoria.append("<br><b>Sugerencias para armado superior (perchas):</b>")
        if opciones_barras['perchas']:
            req = opciones_barras['perchas'][0]['area_requerida_mm2']
            memoria.append(f"Área requerida para perchas (30% de As,min): <b>{req/100:.2f} cm²</b>")
            for op in opciones_barras['perchas']:
                 memoria.append(f"   - Opción: 2 Ø{int(op['diametro'])}mm (As prov: {op['area_provista_mm2']/100:.2f} cm²)")

    memoria.append("<hr>")
    return memoria

def _generar_memoria_corte(d_in, corte_res):
    """Genera la memoria de cálculo para el diseño a corte, replicando el formato original."""
    memoria = ["<h3>MÓDULO 6: DISEÑO A CORTE</h3>"]
    # Desempaquetamos datos
    f_c = d_in['f_c']; b = d_in['b']; d = d_in['d']; Vu = d_in['Vu']; d_est = d_in['d_est']
    phi_corte = 0.75

    if d_in['f_y'] > 420: 
        memoria.append(f"<p style='color:orange;'>>> ADVERTENCIA: Para corte, fy se limita a {corte_res['fy_corte_MPa']} MPa.</p>")
    
    phi_Vc = corte_res['phi_Vc_N']
    memoria.append("<b>1. Resistencia del hormigón (ΦVc):</b>")
    memoria.append("$\\phi V_c = \\phi \\frac{1}{6} \\sqrt{f'_c} b d$")
    memoria.append(f"$\\phi V_c = {phi_corte:.2f} \\cdot \\frac{{1}}{{6}} \\sqrt{{{f_c}}} \\cdot {b} \\cdot {d:.1f}$")
    memoria.append(f"$\\mathbf{{\\phi V_c = {phi_Vc / 1000:.2f} \\text{{ kN}}}}$")
    memoria.append(f"Cortante Actuante (Vu): {Vu / 1000:.2f} kN")
    memoria.append("<br>")
    
    memoria.append("<b>2. Verificación de necesidad de estribos:</b>")
    if not corte_res['requiere_estribos_calculo']:
        memoria.append(f"<b>Vu ({Vu/1000:.2f} kN) <= 0.5 * ΦVc ({0.5*phi_Vc/1000:.2f} kN)</b>")
        memoria.append("<p style='color:green;'>>> RESULTADO: No se necesitan estribos por cálculo.</p>")
    else:
        Vs = corte_res['Vs_N']
        Vs_max = corte_res['Vs_max_limite_N']
        fy_corte = corte_res['fy_corte_MPa']
        Av = corte_res['Av_mm2']
        s_calc = corte_res['s_calculado_mm']
        s_max_a = corte_res['s_max_a_mm']
        s_max_b = corte_res['s_max_b_mm']
        s_max_ref = corte_res['s_max_ref_min_mm']
        s_max_vs = corte_res['s_max_por_magnitud_vs_mm']
        s_final = corte_res['separacion_final_mm']
        
        memoria.append(f"<b>Vu ({Vu/1000:.2f} kN) > 0.5 * ΦVc ({0.5*phi_Vc/1000:.2f} kN)</b>")
        memoria.append("<p>>> RESULTADO: Se necesitan estribos por cálculo.</p>")
        
        memoria.append("<br><b>3. Cortante a resistir por el acero (Vs):</b>")
        memoria.append("$V_s = \\frac{{V_u - \\phi V_c}}{{\\phi}}$")
        memoria.append(f"$V_s = \\frac{{{Vu:.2f} - {phi_Vc:.2f}}}{{{phi_corte}}}$")
        memoria.append(f"$\\mathbf{{V_s = {Vs / 1000:.2f} \\text{{ kN}}}}$")
        
        memoria.append("<br><b>4. Verificación de la sección de hormigón (Vs,max):</b>")
        memoria.append("$V_{{s,max}} = \\frac{2}{3} \\sqrt{f'_c} b d$")
        memoria.append(f"$V_{{s,max}} = \\frac{{2}}{{3}} \\sqrt{{{f_c}}} \\cdot {b} \\cdot {d:.1f} = {Vs_max/1000:.2f} \\text{{ kN}}$")
        if Vs > Vs_max:
             memoria.append(f"<p style='color:red;'><b>Vs ({Vs/1000:.2f} kN) > Vs,max ({Vs_max/1000:.2f} kN) -> ¡ERROR CRÍTICO!</b></p>")
        else:
             memoria.append(f"<p style='color:green;'><b>Vs ({Vs/1000:.2f} kN) <= Vs,max ({Vs_max/1000:.2f} kN) -> OK.</b></p>")

        memoria.append("<br><b>5. Espaciamiento requerido por resistencia (s_calc):</b>")
        memoria.append(f"Para estribos Ø{int(d_est)}mm, Av = {Av:.2f} mm².")
        memoria.append("$s_{{calc}} = \\frac{{A_v f_{{yt}} d}}{{V_s}}$")
        if Vs > 0:
            memoria.append(f"$s_{{calc}} = \\frac{{{Av:.2f} \\cdot {fy_corte} \\cdot {d:.1f}}}{{{Vs:.2f}}}$")
        memoria.append(f"$\\mathbf{{s_{{calc}} = {s_calc:.1f} \\text{{ mm}}}}$")
        
        memoria.append("<br><b>6. Verificación de Separaciones Máximas por Norma:</b>")
        memoria.append("<i>Límite por refuerzo mínimo ($s_{max,ref}$):</i>")
        memoria.append(f"$Cláusula \\ A: \\frac{{A_v f_{{yt}}}}{{0.062\\sqrt{{f'_c}} b}} = {s_max_a:.1f} \\text{{ mm}}$")
        memoria.append(f"$Cláusula \\ B: \\frac{{A_v f_{{yt}}}}{{0.35 b}} = {s_max_b:.1f} \\text{{ mm}}$")
        memoria.append(f"$\\mathbf{{s_{{max,ref}} = min({s_max_a:.1f}, {s_max_b:.1f}) = {s_max_ref:.1f} \\text{{ mm}}}}$")
        
        memoria.append("<i>Límite por magnitud de Vs ($s_{max,Vs}$):</i>")
        if Vs <= corte_res['Vs_limite_tabla_N']: 
            memoria.append(f"$Vs <= V_s,lim -> s_{{max,Vs}} = min(d/2, 600mm) = {s_max_vs:.1f} \\text{{ mm}}$")
        else: 
            memoria.append(f"$Vs > V_s,lim -> s_{{max,Vs}} = min(d/4, 300mm) = {s_max_vs:.1f} \\text{{ mm}}$")
        
        memoria.append("<br><i>Decisión Final de Espaciamiento ($s_{final}$):</i>")
        memoria.append("$s_{{final}} = min(s_{{calc}}, s_{{max,ref}}, s_{{max,Vs}})$")
        memoria.append(f"$s_{{final}} = min({s_calc:.1f}, {s_max_ref:.1f}, {s_max_vs:.1f}) \\text{{ mm}}$")
        memoria.append(f"$\\mathbf{{s_{{final}} = {s_final:.0f} \\text{{ mm}}}}$")
        
    memoria.append("<hr>")
    return memoria

# ==============================================================================
# MÓDULO 3: FUNCIÓN ORQUESTADORA PRINCIPAL
# ==============================================================================

def realizar_diseno_viga(f_c, f_y, mu_knm, Vu_kN, b_cm, h_cm, r_min_cm, 
                         diametro_longitudinal, diametro_estribo, area_acero_previo_cm2=0.0, 
                         armado_previo_info=None):
    
    # 1. Preparar diccionario de datos de entrada en unidades consistentes (N, mm)
    datos_entrada = {
        'f_c': f_c, 'f_y': f_y, 'Ey': 200000.0,
        'b': b_cm * 10, 'h': h_cm * 10, 'r_min': r_min_cm * 10,
        'd_long': diametro_longitudinal, 'd_est': diametro_estribo,
        'Mu': mu_knm * 1e6, 'Vu': Vu_kN * 1000,
        'As_previo_cm2': area_acero_previo_cm2, 'armado_previo_info': armado_previo_info,
        'phi': 0.9, 'gamma': 0.85
    }
    datos_entrada['d'] = datos_entrada['h'] - datos_entrada['r_min'] - datos_entrada['d_est'] - (datos_entrada['d_long'] / 2)

    # 2. Ejecutar los CÁLCULOS
    flex_res = _calcular_diseno_flexion(
        datos_entrada['d'], datos_entrada['Mu'], datos_entrada['phi'], datos_entrada['gamma'], f_c, 
        datos_entrada['b'], f_y, datos_entrada['Ey'], datos_entrada['r_min'], 
        datos_entrada['d_est'], datos_entrada['d_long'], area_acero_previo_cm2 * 100
    )
    if flex_res.get('error'):
        memoria = [f"<h3>Error en Diseño a Flexión</h3><p style='color:red;'><b>{flex_res['error']}</b></p>"]
        return {'resultados': {'error': flex_res['error']}, 'memoria': memoria}

    opciones_barras = _calcular_selector_barras(
        flex_res['As_a_disenar_mm2'], flex_res['As_compresion_final_mm2'], flex_res['As_min_mm2'],
        datos_entrada['b'], datos_entrada['r_min'], datos_entrada['d_est'], armado_previo_info
    )

    corte_res = _calcular_diseno_corte(
        datos_entrada['d'], datos_entrada['Vu'], f_c, datos_entrada['b'], f_y, diametro_estribo
    )
    if corte_res.get('error'):
        memoria = [f"<h3>Error en Diseño a Corte</h3><p style='color:red;'><b>{corte_res['error']}</b></p>"]
        return {'resultados': {'error': corte_res['error']}, 'memoria': memoria}

    # 3. Ensamblar RESULTADOS para la GUI
    resultados_gui = {
        'As_traccion_cm2': flex_res.get('As_a_disenar_mm2', 0) / 100,
        'As_compresion_cm2': flex_res.get('As_compresion_final_mm2', 0) / 100,
        'separacion_cm': corte_res.get('separacion_final_mm', "N/A") / 10 if isinstance(corte_res.get('separacion_final_mm'), (int, float)) else "Máx. Norma"
    }

    # 4. Generar la MEMORIA DE CÁLCULO
    memoria = ["<h2>--- INICIO DEL REPORTE DE CÁLCULO ---</h2>"]
    memoria.append("<h3>MÓDULO 1: PARÁMETROS INICIALES</h3>")
    memoria.append(f"<b>Datos de Entrada:</b> f'c={f_c} MPa, fy={f_y} MPa, Mu={mu_knm} kN·m, Vu={Vu_kN} kN, b={b_cm} cm, h={h_cm} cm")
    
    # Desempaquetamos valores para la fórmula
    h_mm = datos_entrada['h']
    r_min_mm = datos_entrada['r_min']
    d_est_mm = datos_entrada['d_est']
    d_long_mm = datos_entrada['d_long']
    d_calculado = datos_entrada['d']
    
    memoria.append("<br><b>Altura Efectiva (d)</b>")
    memoria.append("$d = h - r_{rec} - \\phi_{est} - \\frac{\\phi_{l}}{2}$")
    memoria.append(f"$d = {h_mm} - {r_min_mm} - {d_est_mm} - \\frac{{{d_long_mm}}}{{2}}$")
    memoria.append(f"$\\mathbf{{d = {d_calculado:.2f} \\text{{ mm}}}}$")

    if area_acero_previo_cm2 > 0:
        memoria.append(f"<p style='background-color:#E0E0E0; padding:5px; border-radius:3px;'><b>Armado Previo Considerado:</b> {area_acero_previo_cm2:.2f} cm²</p>")
    memoria.append("<hr>")
    memoria.extend(_generar_memoria_flexion(datos_entrada, flex_res, area_acero_previo_cm2*100))
    memoria.extend(_generar_memoria_selector_barras(datos_entrada, flex_res, opciones_barras))
    memoria.extend(_generar_memoria_corte(datos_entrada, corte_res))
    
    memoria.append("<h2>--- FIN DEL REPORTE ---</h2>")

    # 5. Devolver la estructura de datos que la GUI espera
    return {'resultados': resultados_gui, 'memoria': memoria}