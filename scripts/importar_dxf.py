"""
Módulo: importar_dxf.py
Descripción: Intérprete de archivos CAD. Lee la geometría de archivos .DXF y 
los traduce automáticamente a coordenadas nodales y conectividad de elementos 
1D en el modelo_estructura.
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

import ezdxf
import numpy as np
import math
import re

# --- FUNCIONES AUXILIARES GEOMÉTRICAS ---

def _procesar_coord(coords, decimales):
    """
    Redondea las coordenadas para evitar errores de punto flotante (ej. 3.000000002 -> 3.000)
    Ayuda a que las comparaciones y diccionarios funcionen correctamente.
    """
    return tuple(np.round(np.array(coords), decimales))

def _ordenar_vertices_losa(vertices):
    """
    Toma una lista de 4 vértices y los devuelve en orden antihorario 
    para asegurar la normal correcta.
    """
    if len(vertices) != 4:
        return vertices
    coords = np.array(vertices)
    centro = np.mean(coords, axis=0)
    
    # Proyección al plano dominante para determinar la normal "visual"
    v1 = coords[1] - coords[0]
    v2 = coords[2] - coords[0]
    normal = np.cross(v1, v2)
    
    # Determinar plano de proyección principal (XY, XZ o YZ)
    if abs(normal[2]) > abs(normal[0]) and abs(normal[2]) > abs(normal[1]): 
        idx1, idx2 = 0, 1 # Plano XY
    elif abs(normal[1]) > abs(normal[0]): 
        idx1, idx2 = 0, 2 # Plano XZ
    else: 
        idx1, idx2 = 1, 2 # Plano YZ

    # Ordenar por ángulo polar respecto al centroide
    angulos = [math.atan2(p[idx2] - centro[idx2], p[idx1] - centro[idx1]) for p in coords]
    vertices_ordenados = [v for _, v in sorted(zip(angulos, coords), key=lambda item: item[0])]
    return vertices_ordenados

def verificar_coplanaridad(puntos, tolerancia=1e-3):
    """
    Verifica si 4 puntos son coplanares calculando el volumen del tetraedro que forman.
    Si el volumen es casi 0, son coplanares.
    """
    if len(puntos) < 4: return True
    a, b, c, d = np.array(puntos[0]), np.array(puntos[1]), np.array(puntos[2]), np.array(puntos[3])
    # Producto triple escalar (Volumen paralelepípedo / 6)
    vol = np.abs(np.dot(a - d, np.cross(b - d, c - d)))
    return vol < tolerancia

def obtener_id_nodo_con_tolerancia(coord_raw, mapa_nodos_existentes, tolerancia=1e-3):
    """
    Busca si existe un nodo cercano dentro de la tolerancia.
    mapa_nodos_existentes: { id_nodo: (x, y, z) }
    Retorna (id_nodo, coords_existentes) si encuentra, o (None, None).
    """
    coord_arr = np.array(coord_raw)
    
    # Búsqueda lineal (Suficiente para < 5000 nodos, luego se recomendaría KDTree)
    for id_nodo, coord_existente in mapa_nodos_existentes.items():
        dist = np.linalg.norm(coord_arr - np.array(coord_existente))
        if dist < tolerancia:
            return id_nodo, coord_existente
            
    return None, None

def obtener_capas_dxf(ruta_archivo):
    try:
        doc = ezdxf.readfile(ruta_archivo)
        return sorted([capa.dxf.name for capa in doc.layers])
    except Exception as e:
        raise IOError(f"Error leyendo capas: {e}")

# --- PARSERS DE CAPAS ---

def parsear_capa_elemento(nombre):
    """
    Sintaxis: EL_NOMBRE_h_b (h y b en cm)
    Retorna: (nombre_material, h_m, b_m)
    """
    partes = nombre.split('_')
    if len(partes) >= 4 and partes[0] == 'EL':
        try:
            b_cm = float(partes[-1])
            h_cm = float(partes[-2])
            nombre_mat = "_".join(partes[1:-2])
            return nombre_mat, h_cm / 100.0, b_cm / 100.0 # Convertir a metros
        except ValueError:
            pass
    return None

def parsear_capa_losa(nombre):
    """
    Sintaxis: LO_DISTRIBUCION_ESPESOR_PESOESPECIFICO
    Ejemplo: LO_BI_20_24 (Bidireccional, 20cm, 24kN/m3)
    Retorna: (tipo_distribucion, eje_uni, espesor_m, peso_esp)
    """
    partes = nombre.split('_')
    # CAMBIO: Ahora validamos len >= 4 para incluir espesor y PE
    if len(partes) >= 4 and partes[0] == 'LO':
        try:
            dist_code = partes[1].upper()
            espesor_cm = float(partes[2])   
            peso_esp = float(partes[3])     
            espesor_m = espesor_cm / 100.0  # Conversión a metros

            if dist_code == 'BI':
                return 'bidireccional', None, espesor_m, peso_esp
            elif dist_code == 'UX':
                return 'unidireccional', 'Global X', espesor_m, peso_esp
            elif dist_code == 'UY':
                return 'unidireccional', 'Global Y', espesor_m, peso_esp
        except ValueError:
            pass
    return None

def parsear_capa_apoyo(nombre):
    """
    Sintaxis: AP_DXDYDZRXRYRZ (Ej: AP_111000)
    Retorna: [bool, bool, bool, bool, bool, bool]
    """
    partes = nombre.split('_')
    if len(partes) >= 2 and partes[0] == 'AP':
        codigo = partes[1]
        if len(codigo) == 6 and codigo.isdigit():
            return [ch == '1' for ch in codigo]
    return None

def parsear_capa_carga_lineal(nombre):
    """
    Sintaxis: CU_TIPO_HIP_EJE_VALOR
    Ejemplo: CU_D_Muro_Z_-10  (Carga Muerta, Hip 'Muro', Eje Z, -10 kN/m)
    Ejemplo: CU_W_Viento_X_5  (Carga Viento, Hip 'Viento', Eje X, 5 kN/m)
    Retorna: (tipo, hipotesis, eje, valor)
    """
    partes = nombre.split('_')
    if len(partes) >= 5 and partes[0] == 'CU':
        try:
            tipo = partes[1]
            hipotesis = partes[2]
            eje = partes[3].upper() 
            valor = float(partes[4]) 
            
            if eje in ['X', 'Y', 'Z']:
                return tipo, hipotesis, eje, valor
        except ValueError:
            pass
    return None

def parsear_capa_carga_superficial(nombre):
    """
    Sintaxis: CS_TIPO_HIPOTESIS_VALOR
    Retorna: (tipo, hipotesis, valor)
    """
    partes = nombre.split('_')
    if len(partes) >= 4 and partes[0] == 'CS':
        try:
            tipo = partes[1]
            hipotesis = partes[2]
            valor = float(partes[3])
            return tipo, hipotesis, valor
        except ValueError:
            pass
    return None

def parsear_capa_carga_puntual(nombre):
    """
    Sintaxis: CP_TIPO_HIPOTESIS_ACCION_VALOR
    Retorna: (tipo, hipotesis, accion, valor)
    """
    partes = nombre.split('_')
    if len(partes) >= 5 and partes[0] == 'CP':
        try:
            tipo = partes[1]
            hipotesis = partes[2]
            accion = partes[3].upper() # FX, FY, FZ, MX, MY, MZ
            valor = float(partes[4])
            if accion in ['FX', 'FY', 'FZ', 'MX', 'MY', 'MZ']:
                return tipo, hipotesis, accion, valor
        except ValueError:
            pass
    return None

# --- FUNCIÓN PRINCIPAL ---

def importar_dxf(ruta_archivo, capas_seleccionadas=None, tolerancia_fusion=1e-3, decimales_redondeo=3):
    try:
        doc = ezdxf.readfile(ruta_archivo)
        msp = doc.modelspace()
    except Exception as e:
        raise IOError(f"Error leyendo DXF: {e}")

    if capas_seleccionadas is None:
        capas_seleccionadas = {capa.dxf.name for capa in doc.layers}
    else:
        capas_seleccionadas = set(capas_seleccionadas)

    # Estructuras de datos
    nodos = {} # {id: (x,y,z)}
    elementos = {}
    losas = {}
    materiales_portico = {} 
    mapa_materiales_existentes = {} 
    
    cargas_importadas = [] 
    cargas_puntuales_importadas = []
    apoyos_importados = []
    
    capas_con_error = set()
    
    id_nodo_actual = 1
    id_elem_actual = 1
    id_losa_actual = 1
    id_mat_actual = 1

    # --- HELPER INTERNO: GESTIÓN DE NODOS CON REDONDEO ---
    def gestionar_nodo(coords_raw):
        nonlocal id_nodo_actual
        # 1. Redondear (Limpieza numérica)
        coords_limpias = _procesar_coord(coords_raw, decimales_redondeo)
        
        # 2. Buscar nodo cercano (Fusión)
        id_existente, _ = obtener_id_nodo_con_tolerancia(coords_limpias, nodos, tolerancia_fusion)
        if id_existente:
            return id_existente
        else:
            nodos[id_nodo_actual] = coords_limpias
            id_nuevo = id_nodo_actual
            id_nodo_actual += 1
            return id_nuevo

    # --- HELPER INTERNO: SNAP DE CARGAS ---
    def obtener_coord_snap(coords_raw):
        """
        Intenta 'pegar' (snap) la coordenada de una carga a un nodo existente.
        Si existe un nodo cerca, devuelve la coordenada DEL NODO (exacta).
        Si no, devuelve la coordenada redondeada de la carga.
        """
        coords_limpias = _procesar_coord(coords_raw, decimales_redondeo)
        id_existente, coords_reales_nodo = obtener_id_nodo_con_tolerancia(coords_limpias, nodos, tolerancia_fusion)
        
        if id_existente:
            return coords_reales_nodo # Usar la exacta del nodo
        return coords_limpias

    # --- 1. PROCESAR ELEMENTOS 1D Y CARGAS LINEALES (Entidad: LINE) ---
    for linea in msp.query('LINE'):
        layer = linea.dxf.layer
        if layer not in capas_seleccionadas: continue
        
        # Intentar parsear como ELEMENTO
        datos_elem = parsear_capa_elemento(layer)
        if datos_elem:
            nombre_mat, h, b = datos_elem
            
            p_start = tuple(np.array(linea.dxf.start))
            p_end = tuple(np.array(linea.dxf.end))
            ni = gestionar_nodo(p_start)
            nj = gestionar_nodo(p_end)
            
            if ni == nj: continue # Elemento longitud cero

            clave_mat = (nombre_mat, b, h)
            if clave_mat in mapa_materiales_existentes:
                id_mat = mapa_materiales_existentes[clave_mat]
            else:
                materiales_portico[id_mat_actual] = {
                    "descripcion": nombre_mat,
                    "tipo": "rectangular",
                    "propiedades": (21000, 0.2, b, h), 
                    "peso_especifico": 24.0
                }
                mapa_materiales_existentes[clave_mat] = id_mat_actual
                id_mat = id_mat_actual
                id_mat_actual += 1
            
            elementos[id_elem_actual] = (ni, nj, id_mat)
            id_elem_actual += 1
            continue

        # Parsear como CARGA LINEAL
        datos_cu = parsear_capa_carga_lineal(layer)
        if datos_cu:
            tipo_carga, hipotesis, eje, valor = datos_cu
            c_inicio = obtener_coord_snap(linea.dxf.start)
            c_fin = obtener_coord_snap(linea.dxf.end)

            cargas_importadas.append({
                'tipo': 'elemento', 
                'tipo_carga_norma': tipo_carga,
                'nombre_hipotesis': hipotesis,
                'eje_carga': eje,      
                'magnitud': valor,     
                'coords_inicio': c_inicio,
                'coords_fin': c_fin
            })
            continue

        if layer.startswith(('EL_', 'CU_')):
            capas_con_error.add(layer)

    # --- 2. PROCESAR LOSAS Y CARGAS SUPERFICIALES (Entidad: 3DFACE) ---
    for face in msp.query('3DFACE'):
        layer = face.dxf.layer
        if layer not in capas_seleccionadas: continue
        
        vertices_raw = list(face.wcs_vertices())
        if len(vertices_raw) != 4: continue
        
        # 1. Redondear
        vertices = [_procesar_coord(v, decimales_redondeo) for v in vertices_raw]

        # 2. Verificar coplanaridad
        if not verificar_coplanaridad(vertices, tolerancia_fusion):
            capas_con_error.add(layer + " (No Coplanar)")
            continue

        # 3. ORDENAR (CRÍTICO: Mantiene la normal correcta)
        vertices_ordenados = _ordenar_vertices_losa(vertices)
        
        # arsear comPo LOSA
        datos_losa = parsear_capa_losa(layer)
        if datos_losa:
            distribucion, eje_uni, h_val, pe_val = datos_losa
            
            # Crear/Buscar nodos (Gestión de topología)
            ids_nodos_losa = [gestionar_nodo(tuple(v)) for v in vertices_ordenados]
            
            if len(set(ids_nodos_losa)) < 3: continue

            losas[id_losa_actual] = {
                'nodos': ids_nodos_losa,
                'distribucion': distribucion,
                'eje_uni': eje_uni,
                'espesor': h_val,           
                'peso_especifico': pe_val,  
                'coords_vertices': [nodos[nid] for nid in ids_nodos_losa] 
            }
            id_losa_actual += 1
            continue

        # Intentar parsear como CARGA SUPERFICIAL
        datos_cs = parsear_capa_carga_superficial(layer)
        if datos_cs:
            tipo_carga, hipotesis, valor = datos_cs
            
            # SNAP: Cargas superficiales se ajustan a nodos si existen
            verts_carga = [obtener_coord_snap(v) for v in vertices_ordenados]

            cargas_importadas.append({
                'tipo': 'superficial',
                'tipo_carga_norma': tipo_carga,
                'nombre_hipotesis': hipotesis,
                'magnitud_wz': valor,
                'coords_vertices': verts_carga
            })
            continue

        if layer.startswith(('LO_', 'CS_')):
            capas_con_error.add(layer)

    # --- 3. PROCESAR APOYOS (Entidad: CIRCLE) ---
    for circle in msp.query('CIRCLE'):
        layer = circle.dxf.layer
        if layer not in capas_seleccionadas: continue
        
        restricciones = parsear_capa_apoyo(layer)
        if restricciones:
            centro = _procesar_coord(circle.dxf.center, decimales_redondeo)
            # Buscar coincidencia
            id_existente, _ = obtener_id_nodo_con_tolerancia(centro, nodos, tolerancia_fusion)
            
            if id_existente:
                apoyos_importados.append({
                    'id_nodo': id_existente,
                    'restricciones': restricciones
                })
            else:
                nuevo_id = gestionar_nodo(circle.dxf.center)
                apoyos_importados.append({
                    'id_nodo': nuevo_id,
                    'restricciones': restricciones
                })
            continue
        
        if layer.startswith('AP_'):
            capas_con_error.add(layer)

    # --- 4. PROCESAR CARGAS PUNTUALES (Entidad: POINT) ---
    for point in msp.query('POINT'):
        layer = point.dxf.layer
        if layer not in capas_seleccionadas: continue
        
        datos_cp = parsear_capa_carga_puntual(layer)
        if datos_cp:
            tipo_carga, hipotesis, accion, valor = datos_cp
            
            # Gestionar nodo ya redondea internamente
            id_nodo_carga = gestionar_nodo(point.dxf.location)
            
            cargas_puntuales_importadas.append({
                'id_nodo': id_nodo_carga,
                'tipo_carga_norma': tipo_carga,
                'nombre_hipotesis': hipotesis,
                'concepto_fuerza': accion,
                'magnitud': valor
            })
            continue
            
        if layer.startswith('CP_'):
            capas_con_error.add(layer)

    # Empaquetar resultados
    return {
        "nodos": nodos,
        "elementos": elementos,
        "losas": losas,
        "materiales": materiales_portico,
        "cargas_importadas": cargas_importadas,
        "apoyos_importados": apoyos_importados,
        "cargas_puntuales_importadas": cargas_puntuales_importadas,
        "capas_omitidas": sorted(list(capas_con_error))
    }