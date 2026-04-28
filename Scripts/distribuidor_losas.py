"""
Módulo: distribuidor_losas.py
Descripción: Módulo fundamental para la transferencia de cargas. Calcula áreas 
tributarias de losas y distribuye las cargas superficiales hacia los elementos 
1D (vigas) perimetrales en forma de cargas distribuidas lineales y uniformes.
"""

# -----------------------------------------------------------------------------
# VORTEX 3D - Análisis Estructural de Edificaciones 3D y Diseño Normativo 
# de Vigas y Columnas 
# Copyright (C) 2026 Diego Oliver Vargas Moya & Luis Alberto Ortiz Morales
#
# Este programa es software libre: puedes redistribuirlo y/o modificarlo
# bajo los términos de la Licencia Pública General GNU (GNU GPL) publicada
# por la Free Software Foundation, ya sea la versión 3 de la Licencia, o
# cualquier versión posterior.
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

#=======================================================================
# I. IMPORTACIONES Y DEPENDENCIAS
#=======================================================================
import numpy as np
import math
from calc import matriz_transformacion_portico_3d
from collections import defaultdict # Nuevo

#=======================================================================
# II. FUNCIONES GEOMÉTRICAS AUXILIARES
#=======================================================================

def _encontrar_vigas_de_borde(losa, modelo):
    """
    Identifica los elementos estructurales que coinciden geométricamente con 
    el perímetro de la losa analizada.
    """
    # 1. Definición topológica de los bordes de la losa
    vigas_borde = {}
    nodos_losa = losa['nodos']
    bordes_losa_ordenados = {tuple(sorted((nodos_losa[i], nodos_losa[(i + 1) % 4]))) for i in range(4)}

    # 2. Mapeo de vigas colindantes
    for id_elem, (ni, nj, _) in modelo.elementos.items():
        borde_elem_ordenado = tuple(sorted((ni, nj)))
        if borde_elem_ordenado in bordes_losa_ordenados:
            vigas_borde[borde_elem_ordenado] = id_elem
            
    return vigas_borde


def _encontrar_losa_adyacente(borde_actual, id_losa_actual, modelo):
    """
    Busca losas contiguas que compartan un borde específico para determinar 
    condiciones de continuidad.
    """
    # 1. Búsqueda de coincidencia de aristas en el modelo
    borde_ordenado_actual = tuple(sorted(borde_actual))
    for id_losa, datos_losa in modelo.losas.items():
        if id_losa == id_losa_actual:
            continue
        nodos_otra = datos_losa['nodos']
        bordes_otra = [tuple(sorted((nodos_otra[i], nodos_otra[(i + 1) % 4]))) for i in range(4)]
        if borde_ordenado_actual in bordes_otra:
            return id_losa
    return None

def _rotar_vector_2d(vector, angulo_grados):
    """
    Aplica una matriz de rotación en el plano 2D a un vector dado.
    """
    # 1. Transformación angular y producto matricial
    angulo_rad = math.radians(angulo_grados)
    matriz_rotacion = np.array([
        [math.cos(angulo_rad), -math.sin(angulo_rad)],
        [math.sin(angulo_rad), math.cos(angulo_rad)]
    ])
    return matriz_rotacion @ vector

def _ordenar_vertices_poligono(vertices):
    """
    Ordena un conjunto de coordenadas de forma radial respecto a su centroide.
    """
    # 1. Cálculo de centroide y ordenamiento polar
    if len(vertices) <= 3:
        return vertices
    centroide = np.mean(vertices, axis=0)
    return sorted(vertices, key=lambda v: math.atan2(v[1] - centroide[1], v[0] - centroide[0]))

def _calcular_interseccion_lineas(p1, v1, p2, v2):
    """
    Calcula el punto de intersección entre dos líneas definidas por un punto y un vector.
    """
    # 1. Resolución del sistema lineal 2x2
    p1_2d, v1_2d = p1[:2], v1[:2]
    p2_2d, v2_2d = p2[:2], v2[:2]
    A = np.array([[v1_2d[0], -v2_2d[0]], [v1_2d[1], -v2_2d[1]]])
    b = p2_2d - p1_2d
    try:
        t, _ = np.linalg.solve(A, b)
        punto_interseccion = p1 + t * v1
        return punto_interseccion
    except np.linalg.LinAlgError:
        print("      [DEBUG] Las líneas de aporte son paralelas, no se intersectan.")
        return None

def _calcular_area_poligono(vertices):
    """
    Calcula el área de un polígono cerrado utilizando la fórmula de Gauss.
    """
    # 1. Aplicación analítica de la fórmula de áreas topográficas
    if not isinstance(vertices, np.ndarray):
        vertices = np.array(vertices)
    if vertices.ndim == 1 or vertices.shape[0] < 3: 
        return 0.0

    x = vertices[:, 0]
    y = vertices[:, 1]
    return 0.5 * np.abs(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))

#=======================================================================
# III. PROCESAMIENTO DE BORDES Y COLINEALIDAD
#=======================================================================
def _es_colineal_y_en_segmento(coord_p, coord_a, coord_b, tol=1e-3):
    """
    Verifica si el punto p (coordenadas) es colineal con el segmento AB y está 
    dentro o sobre el segmento AB.
    """
    coord_a = np.array(coord_a)
    coord_b = np.array(coord_b)
    coord_p = np.array(coord_p)
    
    vector_ab = coord_b - coord_a
    vector_ap = coord_p - coord_a
    
    # 1. Colinealidad: El área del triángulo ABP debe ser cero (producto cruzado).
    cross_product = np.cross(vector_ab, vector_ap)
    if np.linalg.norm(cross_product) > tol:
        return False

    # 2. En el segmento: La proyección de AP sobre AB debe estar entre 0 y ||AB||.
    longitud_ab_sq = np.dot(vector_ab, vector_ab)
    if longitud_ab_sq < tol: 
        return np.linalg.norm(vector_ap) < tol 
        
    proyeccion_ap_sobre_ab = np.dot(vector_ap, vector_ab)

    if proyeccion_ap_sobre_ab < -tol:
        return False # P está antes de A
    if proyeccion_ap_sobre_ab > longitud_ab_sq + tol:
        return False # P está después de B
        
    return True
    
def _obtener_elementos_en_borde(coord_borde_inicio, coord_borde_fin, losa_borde_ids, modelo):
    """
    Devuelve la lista de elementos 1D cuyos nodos son colineales con el borde 
    principal de la losa y están contenidos en él. La lista se devuelve ordenada
    por proximidad al inicio del borde.
    
    Devuelve: [{'id_viga': ID, 'nodos_viga': (ni, nj), 'longitud': L}, ...]
    """
    elementos_de_borde = []
    
    coord_borde_inicio_np = np.array(coord_borde_inicio)
    coord_borde_fin_np = np.array(coord_borde_fin)

    for id_elem, (ni, nj, _) in modelo.elementos.items():
        coord_ni = np.array(modelo.nodos.get(ni, [0,0,0]))
        coord_nj = np.array(modelo.nodos.get(nj, [0,0,0]))
        
        # 1. Verificar si AMBOS nodos del elemento son colineales y están en el segmento principal
        es_ni_en_segmento = _es_colineal_y_en_segmento(coord_ni, coord_borde_inicio_np, coord_borde_fin_np)
        es_nj_en_segmento = _es_colineal_y_en_segmento(coord_nj, coord_borde_inicio_np, coord_borde_fin_np)

        if es_ni_en_segmento and es_nj_en_segmento and ni != nj:
             longitud = np.linalg.norm(coord_ni - coord_nj)
             if longitud > 1e-6:
                elementos_de_borde.append({
                    'id_viga': id_elem, 
                    'nodos_viga': (ni, nj),
                    'longitud': longitud
                })
             
    # 2. Ordenar por proximidad a coord_borde_inicio (el primer nodo de la losa)
    def ordenar_por_proximidad(item):
        ni, nj = item['nodos_viga']
        coord_ni = np.array(modelo.nodos[ni])
        coord_nj = np.array(modelo.nodos[nj])
        
        dist_ni = np.linalg.norm(coord_ni - coord_borde_inicio_np)
        dist_nj = np.linalg.norm(coord_nj - coord_borde_inicio_np)
        
        return min(dist_ni, dist_nj)
        
    elementos_de_borde.sort(key=ordenar_por_proximidad)

    # 3. Corregir la orientación de los nodos de la viga para que coincida con el borde
    elementos_finales_ordenados = []
    nodo_anterior = losa_borde_ids[0]
    
    for item in elementos_de_borde:
        n1, n2 = item['nodos_viga']
        if n2 == nodo_anterior: 
            item['nodos_viga'] = (n2, n1) 
            nodo_anterior = n1
        elif n1 == nodo_anterior:
            nodo_anterior = n2
        else:
             # Este elemento no está conectado al borde principal, o es un caso de modelado complejo.
             # Lo mantenemos para el flujo de la viga, asumiendo que el ordenamiento por proximidad lo maneja.
             pass 

        elementos_finales_ordenados.append(item)
    
    return [e for e in elementos_finales_ordenados if e['longitud'] > 1e-6]

#=======================================================================
# IV. DISTRIBUCIÓN UNIDIRECCIONAL DE CARGAS
#=======================================================================
def _manejar_distribucion_unidireccional(losa, wz, id_hipotesis, vigas_borde, modelo):
    """
    Calcula y distribuye cargas superficiales hacia apoyos paralelos mediante 
    áreas tributarias rectangulares [McCormac & Brown, 2015].
    """
    # 1. Inicialización de registros de cálculo
    log_datos = {
        'id_losa': losa['id'],
        'tipo': 'unidireccional',
        'wz': wz,
        'ancho_total': 0,
        'ancho_aporte': 0,
        'w_lineal': 0,
        'vigas_cargadas': []
    }
    print(f"\n--- [DEBUG] Iniciando Distribución Unidireccional para Losa ID: {losa['id']} ---")
    print(f"    Carga Superficial (wz): {wz:.2f} kPa")
    
    eje_uni = losa.get('eje_uni', 'Global Y')
    nodos_losa = losa['nodos']
    
    eje_paralelo_viga = np.array([1.0, 0.0, 0.0]) if 'Y' in eje_uni else np.array([0.0, 1.0, 0.0])

    bordes_principales_losa = [(nodos_losa[i], nodos_losa[(i + 1) % 4]) for i in range(4)]
    
    # 2. Identificar los 2 bordes principales paralelos al eje de distribución
    bordes_paralelos = []
    for borde_original in bordes_principales_losa:
        p_inicio = np.array(modelo.nodos[borde_original[0]])
        p_fin = np.array(modelo.nodos[borde_original[1]])
        vector_borde = p_fin - p_inicio
        norm_vector = np.linalg.norm(vector_borde)
        if norm_vector < 1e-9: continue
        
        vector_borde_unitario = vector_borde / norm_vector
        
        if abs(np.dot(vector_borde_unitario, eje_paralelo_viga)) > 0.98:
             bordes_paralelos.append(borde_original)
             
    if len(bordes_paralelos) != 2:
        raise ValueError(f"Error en Losa {losa['id']}: Para distribución unidireccional, se requieren exactamente 2 bordes de apoyo paralelos y opuestos. Se encontraron {len(bordes_paralelos)}.")

    # 3. Calcular ancho de aporte total
    p1_viga1 = np.array(modelo.nodos[bordes_paralelos[0][0]])
    p2_viga_opuesta = np.array(modelo.nodos[bordes_paralelos[1][0]])
    v_base = np.array(modelo.nodos[bordes_paralelos[0][1]]) - p1_viga1
    v_punto = p2_viga_opuesta - p1_viga1
    
    norm_v_base = np.linalg.norm(v_base)
    if norm_v_base < 1e-9: 
         raise ValueError(f"Error: Longitud de borde en losa {losa['id']} es cero.")
         
    v_base_unitario = v_base / norm_v_base
    proyeccion = np.dot(v_punto, v_base_unitario) * v_base_unitario
    ancho_aporte_total = np.linalg.norm(v_punto - proyeccion)
    
    ancho_aporte_por_viga = ancho_aporte_total / 2.0
    w_lineal = wz * ancho_aporte_por_viga
    
    print(f"    Ancho total de aporte (distancia entre bordes): {ancho_aporte_total:.2f} m")
    print(f"    Ancho de aporte por borde: {ancho_aporte_por_viga:.2f} m")
    print(f"    Cálculo Carga Lineal: {wz:.2f} kPa * {ancho_aporte_por_viga:.2f} m = {w_lineal:.2f} kN/m")

    log_datos['ancho_total'] = ancho_aporte_total
    log_datos['ancho_aporte'] = ancho_aporte_por_viga
    log_datos['w_lineal'] = w_lineal
    
    cargas_generadas = []
    
    # 4. OBTENER *TODOS* LOS ELEMENTOS DE BORDE Y ASIGNAR LA CARGA
    for borde_principal_ids in bordes_paralelos:
        p_inicio_borde = modelo.nodos[borde_principal_ids[0]]
        p_fin_borde = modelo.nodos[borde_principal_ids[1]]
        
        elementos_en_borde = _obtener_elementos_en_borde(p_inicio_borde, p_fin_borde, borde_principal_ids, modelo)
        
        if not elementos_en_borde:
            print(f"    -> ADVERTENCIA: No se encontraron elementos en el borde {borde_principal_ids[0]}-{borde_principal_ids[1]}.")
            continue

        for elem_info in elementos_en_borde:
            id_viga = elem_info['id_viga']
            longitud_viga = elem_info['longitud']
            ni_viga, nj_viga = elem_info['nodos_viga']
            p_inicio_viga, p_fin_viga = modelo.nodos[ni_viga], modelo.nodos[nj_viga]
            
            print(f"    -> Asignando a Viga ID: {id_viga} (Longitud: {longitud_viga:.2f} m, Nodos: {ni_viga}-{nj_viga})")
            
            # Cálculo de carga local
            T, _ = matriz_transformacion_portico_3d(p_inicio_viga, p_fin_viga)
            R = T[:3, :3]
            w_global = np.array([0.0, 0.0, w_lineal])
            w_local = R @ w_global

            cargas_generadas.append({
                "id_elemento": id_viga, "id_hipotesis": id_hipotesis,
                "datos_carga": ('uniforme', w_local[0], w_local[1], w_local[2], 0.0)
            })

            log_datos['vigas_cargadas'].append({
                'id_viga': id_viga, 
                'longitud': longitud_viga, 
                'w_local': w_local
            })
        
    print(f"--- [DEBUG] Fin Distribución Unidireccional para Losa ID: {losa['id']} ---")
    return cargas_generadas, log_datos

#=======================================================================
# V. DISTRIBUCIÓN BIDIRECCIONAL DE CARGAS (ÁREAS TRIBUTARIAS)
#=======================================================================
def _calcular_geometria_aporte_bidireccional(id_losa_actual, losa, modelo):
    """
    Establece la partición del área de la losa generando trapecios y triángulos 
    basados en líneas de rotura.
    """
    # 1. Extracción de coordenadas y verificación del área general
    nodos_losa_ids = losa['nodos']
    coords = {nid: np.array(modelo.nodos[nid]) for nid in nodos_losa_ids}
    p_esquinas = [coords[nid] for nid in nodos_losa_ids]
    area_losa_real = _calcular_area_poligono(np.array([p[:2] for p in p_esquinas]))
    vigas_borde_dict = _encontrar_vigas_de_borde(losa, modelo)

    # 2. Trazado paramétrico de líneas de influencia (rotura) según continuidad
    lineas_aporte = []
    for i in range(4):
        nodo_esquina_id = nodos_losa_ids[i]
        borde_anterior = (nodos_losa_ids[i-1], nodo_esquina_id)
        borde_siguiente = (nodo_esquina_id, nodos_losa_ids[(i + 1) % 4])
        
        tiene_viga1 = tuple(sorted(borde_anterior)) in vigas_borde_dict
        es_continuo1 = _encontrar_losa_adyacente(borde_anterior, id_losa_actual, modelo) is not None and tiene_viga1
        
        tiene_viga2 = tuple(sorted(borde_siguiente)) in vigas_borde_dict
        es_continuo2 = _encontrar_losa_adyacente(borde_siguiente, id_losa_actual, modelo) is not None and tiene_viga2

        estatus1 = "continuo" if es_continuo1 else "discontinuo"
        estatus2 = "continuo" if es_continuo2 else "discontinuo"
        
        angulo = 45.0
        if estatus1 != estatus2:
            if estatus1 == "continuo": angulo = 30.0
            else: angulo = 60.0
        
        vector_borde2 = coords[nodos_losa_ids[(i + 1) % 4]] - coords[nodo_esquina_id]
        norm_borde2 = np.linalg.norm(vector_borde2[:2])
        if norm_borde2 < 1e-9: continue
        
        vector_aporte_2d = _rotar_vector_2d(vector_borde2[:2] / norm_borde2, angulo)
        vector_aporte_3d = np.array([vector_aporte_2d[0], vector_aporte_2d[1], 0.0])
        lineas_aporte.append({'punto': coords[nodo_esquina_id], 'vector': vector_aporte_3d})

    if len(lineas_aporte) != 4: return {'poligonos_finales': [], 'puntos_cresta': []}

    # 3. Intersección de líneas para la construcción de polígonos
    p_h1 = _calcular_interseccion_lineas(lineas_aporte[0]['punto'], lineas_aporte[0]['vector'], lineas_aporte[3]['punto'], lineas_aporte[3]['vector'])
    p_h2 = _calcular_interseccion_lineas(lineas_aporte[1]['punto'], lineas_aporte[1]['vector'], lineas_aporte[2]['punto'], lineas_aporte[2]['vector'])
    poligonos_h, area_total_h = [], 0
    if p_h1 is not None and p_h2 is not None:
        poligonos_h_sin_orden = [
            [p_esquinas[0], p_esquinas[1], p_h2, p_h1], 
            [p_esquinas[1], p_esquinas[2], p_h2], 
            [p_esquinas[2], p_esquinas[3], p_h1, p_h2],
            [p_esquinas[3], p_esquinas[0], p_h1]
        ]
        poligonos_h = [_ordenar_vertices_poligono(p) for p in poligonos_h_sin_orden]
        area_total_h = sum(_calcular_area_poligono(np.array([v[:2] for v in p])) for p in poligonos_h)

    p_v1 = _calcular_interseccion_lineas(lineas_aporte[0]['punto'], lineas_aporte[0]['vector'], lineas_aporte[1]['punto'], lineas_aporte[1]['vector'])
    p_v2 = _calcular_interseccion_lineas(lineas_aporte[2]['punto'], lineas_aporte[2]['vector'], lineas_aporte[3]['punto'], lineas_aporte[3]['vector'])
    poligonos_v, area_total_v = [], 0
    if p_v1 is not None and p_v2 is not None:
        poligonos_v_sin_orden = [
            [p_esquinas[0], p_esquinas[1], p_v1], 
            [p_esquinas[1], p_esquinas[2], p_v2, p_v1], 
            [p_esquinas[2], p_esquinas[3], p_v2],
            [p_esquinas[3], p_esquinas[0], p_v2, p_v1]
        ]
        poligonos_v = [_ordenar_vertices_poligono(p) for p in poligonos_v_sin_orden]
        area_total_v = sum(_calcular_area_poligono(np.array([v[:2] for v in p])) for p in poligonos_v)

    # 4. Comprobación y selección de la solución geométrica óptima
    tolerancia_area = 1e-4
    es_valido_h = abs(area_total_h - area_losa_real) < tolerancia_area
    es_valido_v = abs(area_total_v - area_losa_real) < tolerancia_area

    poligonos_finales, puntos_cresta, es_cresta_horizontal = [], [], None
    if es_valido_h and not es_valido_v:
        poligonos_finales, puntos_cresta, es_cresta_horizontal = poligonos_h, [p_h1, p_h2], True
    elif es_valido_v and not es_valido_h:
        poligonos_finales, puntos_cresta, es_cresta_horizontal = poligonos_v, [p_v1, p_v2], False
    elif es_valido_h and es_valido_v:
        if np.linalg.norm(p_h1 - p_h2) <= np.linalg.norm(p_v1 - p_v2):
            poligonos_finales, puntos_cresta, es_cresta_horizontal = poligonos_h, [p_h1, p_h2], True
        else:
            poligonos_finales, puntos_cresta, es_cresta_horizontal = poligonos_v, [p_v1, p_v2], False
    else:
        p_central = np.mean(p_esquinas, axis=0)
        poligonos_finales = [[p_esquinas[i], p_esquinas[(i+1)%4], p_central] for i in range(4)]
        puntos_cresta = [p_central, p_central]

    return {'poligonos_finales': poligonos_finales, 'puntos_cresta': puntos_cresta,
            'es_cresta_horizontal': es_cresta_horizontal,
            'p_h1': p_h1, 'p_h2': p_h2, 'p_v1': p_v1, 'p_v2': p_v2}

def _manejar_distribucion_bidireccional(id_losa_actual, losa, wz, id_hipotesis, modelo):
    """
    Asigna cargas perimetrales variables basadas en el análisis de áreas tributarias 
    poligonales.
    """
    # 1. Configuración y cálculo inicial de áreas
    log_datos = {
        'id_losa': id_losa_actual,
        'tipo': 'bidireccional',
        'wz': wz,
        'vigas_cargadas': []
    }
    print(f"\n--- [DEBUG] Iniciando Distribución Bidireccional para Losa ID: {id_losa_actual} ---")
    print(f"    Carga Superficial (wz): {wz:.2f} kPa")

    geometria = _calcular_geometria_aporte_bidireccional(id_losa_actual, losa, modelo)
    poligonos_finales = geometria.get('poligonos_finales')
    if not poligonos_finales:
        print(f"    -> ADVERTENCIA: No se pudo calcular la geometría de aporte para la Losa {id_losa_actual}.")
        return [], log_datos

    cargas_generadas, nodos_losa_ids = [], losa['nodos']
    p_esquinas = {nid: np.array(modelo.nodos[nid]) for nid in nodos_losa_ids}
    
    bordes_principales_losa = [(nodos_losa_ids[i], nodos_losa_ids[(i + 1) % 4]) for i in range(4)]
    elementos_de_borde_por_principal = {}
    for borde_principal_ids in bordes_principales_losa:
        p_inicio = p_esquinas[borde_principal_ids[0]]
        p_fin = p_esquinas[borde_principal_ids[1]]
        elementos_de_borde_por_principal[borde_principal_ids] = _obtener_elementos_en_borde(
            p_inicio, p_fin, borde_principal_ids, modelo
        )

    v_global_load = np.array([0.0, 0.0, 1.0]) # Vector unitario de carga global Z

    # 2. Iteración sobre bordes para trazar funciones de carga
    for i, borde_principal_ids in enumerate(bordes_principales_losa):
        n1_borde, n2_borde = borde_principal_ids
        
        # Parámetros del borde principal
        p_inicio_borde = p_esquinas[n1_borde]
        p_fin_borde = p_esquinas[n2_borde]
        longitud_borde_total = np.linalg.norm(p_fin_borde - p_inicio_borde)
        
        if longitud_borde_total < 1e-6: continue
        
        # Si no hay elementos en este borde, continuar
        if not elementos_de_borde_por_principal[borde_principal_ids]: continue

        # 3. CALCULAR EL PERFIL DE CARGA Q(X) SOBRE LA LONGITUD TOTAL (0 a 1)
        
        # a) Lógica de sistema local (debe ser la misma para todos los segmentos)
        T_borde, L_borde = matriz_transformacion_portico_3d(p_inicio_borde, p_fin_borde)
        R_borde = T_borde[:3, :3]
        v_local_y = R_borde[1, :]
        v_local_z = R_borde[2, :]
        
        comp_y = np.dot(v_global_load, v_local_y)
        comp_z = np.dot(v_global_load, v_local_z)
        eje_local = 'y' if abs(comp_y) > abs(comp_z) else 'z'
        magnitud_base = wz * (comp_y if eje_local == 'y' else comp_z) 
        
        # b) Reutilizar la lógica existente para generar la lista_de_puntos TOTAL
        poligono_aporte = poligonos_finales[i]
        
        # c) Encontrar los puntos de la "cresta" (los que no están en la viga)
        viga_vector_unitario = (p_fin_borde - p_inicio_borde) / longitud_borde_total
        puntos_cresta_locales = []
        for p_vertice in poligono_aporte:
            v_to_p = p_vertice - p_inicio_borde
            dist_proyectada = np.dot(v_to_p, viga_vector_unitario)
            v_proyeccion = dist_proyectada * viga_vector_unitario
            v_perp = v_to_p - v_proyeccion
            
            if np.linalg.norm(v_perp) > 1e-6:
                puntos_cresta_locales.append({
                    'p_norm': dist_proyectada / longitud_borde_total, 
                    'ancho': np.linalg.norm(v_perp)
                })
        
        # d) Construir la lista de puntos TOTAL (p_norm_total, q_real)
        lista_de_puntos_total = [(0.0, 0.0)]
        puntos_cresta_locales.sort(key=lambda item: item['p_norm'])
        for punto in puntos_cresta_locales:
            p_norm = max(0.0, min(1.0, punto['p_norm']))
            q_real = magnitud_base * punto['ancho'] 
            lista_de_puntos_total.append((p_norm, q_real))
        lista_de_puntos_total.append((1.0, 0.0))
        
        # e) Limpiar puntos duplicados (usamos el limpiador local de la función original)
        clean_puntos_total = []
        if lista_de_puntos_total:
            clean_puntos_total.append(lista_de_puntos_total[0])
            for j in range(1, len(lista_de_puntos_total)):
                if abs(lista_de_puntos_total[j][0] - lista_de_puntos_total[j-1][0]) > 1e-6:
                     clean_puntos_total.append(lista_de_puntos_total[j])
                else:
                     clean_puntos_total[-1] = lista_de_puntos_total[j] # Usar el último valor q si p_norm es igual
        
        # Usamos la función auxiliar del procesador de cargas para interpolar q(x)
        from procesador_cargas import _interpolar_carga_en_punto 
        
        # 4. Asignación paramétrica de fragmentos de carga por elemento soportante
        distancia_acumulada = 0.0
        
        for elem_info in elementos_de_borde_por_principal[borde_principal_ids]:
            id_viga = elem_info['id_viga']
            L_viga = elem_info['longitud']
            ni_viga, nj_viga = elem_info['nodos_viga']

            ni_real, nj_real, _ = modelo.elementos[id_viga]
            es_invertida = False
            # Si el inicio del segmento procesado (ni_viga) no coincide con el inicio real (ni_real),
            # significa que la viga está definida al revés respecto al recorrido del borde.
            if ni_viga != ni_real:
                es_invertida = True
            
            print(f"    -> Procesando Viga ID: {id_viga} (Borde {n1_borde}-{n2_borde}, Segmento {ni_viga}-{nj_viga})")

            # a) Normalizar el tramo de la viga sobre la longitud TOTAL [0, 1]
            a_norm_total = distancia_acumulada / longitud_borde_total
            b_norm_total = (distancia_acumulada + L_viga) / longitud_borde_total
            
            # b) Crear la lista de puntos LOCAL (0.0 a 1.0 local)
            lista_puntos_local = []
            
            # Añadir el punto de inicio (0.0 local)
            q_inicio = _interpolar_carga_en_punto(clean_puntos_total, a_norm_total)
            lista_puntos_local.append((0.0, q_inicio))
            
            # Añadir los puntos de quiebre (kinks) que caen dentro del segmento
            for p_norm_total, q_total in clean_puntos_total:
                if a_norm_total < p_norm_total < b_norm_total:
                    p_norm_local = (p_norm_total - a_norm_total) / (b_norm_total - a_norm_total) # Re-normalizar
                    lista_puntos_local.append((p_norm_local, q_total))
            
            # Añadir el punto final (1.0 local)
            q_fin = _interpolar_carga_en_punto(clean_puntos_total, b_norm_total)
            lista_puntos_local.append((1.0, q_fin))
            
            # c) Limpiar puntos locales duplicados y nulos (usando el limpiador local)
            lista_puntos_local.sort(key=lambda item: item[0])
            clean_puntos_local = []
            if lista_puntos_local:
                clean_puntos_local.append(lista_puntos_local[0])
                for j in range(1, len(lista_puntos_local)):
                    if abs(lista_puntos_local[j][0] - lista_puntos_local[j-1][0]) > 1e-6:
                         clean_puntos_local.append(lista_puntos_local[j])
                    else:
                         clean_puntos_local[-1] = lista_puntos_local[j]

            if es_invertida:
                # Invertimos el eje X local: x_nuevo = 1.0 - x_viejo
                # El valor de carga q se mantiene, solo se mueve de posición.
                clean_puntos_local_invertidos = []
                for p, q in clean_puntos_local:
                    clean_puntos_local_invertidos.append((1.0 - p, q))
                
                # Al invertir, el 0 se vuelve 1 y viceversa
                clean_puntos_local_invertidos.sort(key=lambda item: item[0])
                clean_puntos_local = clean_puntos_local_invertidos
            # ---------------------------------------------
            
            # d) Generar la carga
            datos_carga_final = ('tramos_locales', eje_local, clean_puntos_local)
            
            cargas_generadas.append({
                "id_elemento": id_viga, 
                "id_hipotesis": id_hipotesis, 
                "datos_carga": datos_carga_final
            })
            
            log_datos['vigas_cargadas'].append({
                'id_viga': id_viga,
                'borde': f"{n1_borde}-{n2_borde}",
                'longitud': L_viga,
                'datos_carga': datos_carga_final
            })
            
            print(f"       - Carga generada (tramos): Eje='{eje_local}', Puntos={clean_puntos_local}")
            
            distancia_acumulada += L_viga
            
    print(f"--- [DEBUG] Fin Distribución Bidireccional para Losa ID: {id_losa_actual} ---")
    return cargas_generadas, log_datos


#=======================================================================
# VI. FUNCIÓN PRINCIPAL 
#=======================================================================
def traducir_carga_losa_a_cargas_lineales(id_losa, wz, id_hipotesis, modelo):
    """
    Recibe la especificación de carga superficial de una losa y delega la 
    evaluación al sub-sistema distributivo correspondiente.
    """
    # 1. Validación de entrada y enrutamiento estructural
    if id_losa not in modelo.losas:
        raise ValueError(f"La losa con ID {id_losa} no existe.")

    losa = modelo.losas[id_losa]
    losa['id'] = id_losa
    vigas_borde = _encontrar_vigas_de_borde(losa, modelo)

    log_datos = {}
    cargas_generadas = []
    
    if losa['distribucion'] == 'unidireccional':
        cargas_generadas, log_datos = _manejar_distribucion_unidireccional(losa, wz, id_hipotesis, vigas_borde, modelo)
        return cargas_generadas, log_datos
    elif losa['distribucion'] == 'bidireccional':
        cargas_generadas, log_datos = _manejar_distribucion_bidireccional(id_losa, losa, wz, id_hipotesis, modelo)
        return cargas_generadas, log_datos
    else:
        raise ValueError(f"Tipo de distribución '{losa['distribucion']}' no reconocido.") 