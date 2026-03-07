"""
Módulo: procesador_cargas.py
Descripción: Gestiona la definición de estados y combinaciones de carga. 
Transforma las cargas aplicadas (puntuales, distribuidas, superficiales) en 
vectores de fuerzas equivalentes en los nodos para el análisis matricial.
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

#=======================================================================
# I. IMPORTACIONES Y DEPENDENCIAS
#=======================================================================
import numpy as np
from collections import defaultdict
import itertools
from PySide6.QtWidgets import QMessageBox
from calc import Solucionador3D, matriz_transformacion_portico_3d
from distribuidor_losas import traducir_carga_losa_a_cargas_lineales

#=======================================================================
# II. FUNCIONES ANALÍTICAS: FUERZAS DE EMPOTRAMIENTO PERFECTO (FEP)
#=======================================================================
def _fep_uniforme_parcial(L, w, a, b):
    """
    Calcula los FEPs (Reacciones y Momentos anti-horarios) para una carga
    uniforme 'w' aplicada en un tramo [a, b] de una viga de longitud 'L'.
    Devuelve (R_i, M_i, R_j, M_j)
    """
    # 1. Validación geométrica del elemento
    if L < 1e-9: return (0.0, 0.0, 0.0, 0.0)
    L2, L3 = L*L, L*L*L

    # 2. Pre-cálculo de potencias integradas (integrales de x^n de 'a' a 'b')
    b0 = (b - a)
    b1 = (b**2 - a**2) / 2.0
    b2 = (b**3 - a**3) / 3.0
    b3 = (b**4 - a**4) / 4.0
    
    # 3. R_i = w * integral( (1 - 3(x/L)^2 + 2(x/L)^3) dx) de 'a' a 'b'
    R_i = w * (b0 - 3*b2/L2 + 2*b3/L3)
    
    # 4. M_i = w * integral( (x - 2x^2/L + x^3/L^2) dx) de 'a' a 'b'
    M_i = w * (b1 - 2*b2/L + b3/L2)
    
    # 5. R_j = w * integral( (3(x/L)^2 - 2(x/L)^3) dx) de 'a' a 'b'
    R_j = w * (3*b2/L2 - 2*b3/L3)
    
    # 6. M_j = w * integral( (x^3/L^2 - x^2/L) dx) de 'a' a 'b'
    M_j = w * (b3/L2 - b2/L)

    return (R_i, M_i, R_j, M_j)

def _fep_triangular_parcial(L, w_pico, a, b):
    """
    Calcula los FEPs para una carga triangular (pico 'w_pico' en x=b, 
    cero en x=a) aplicada en [a, b] en una viga de longitud 'L'.
    Devuelve (R_i, M_i, R_j, M_j)
    """
    # 1. Validación de la existencia geométrica del tramo de aplicación
    if L < 1e-9 or abs(b - a) < 1e-9: return (0.0, 0.0, 0.0, 0.0)
    L2, L3 = L*L, L*L*L
    
    # 2. Constante de la pendiente: w(x) = k * (x - a)
    denominador = (b - a)
    k = w_pico / denominador

    # 3. Pre-cálculo de potencias integradas (integrales de x^n * (x-a) de 'a' a 'b')
    # integral(k * (x-a) * x^n dx) = k * integral(x^(n+1) - a*x^n dx)
    
    # n=0: k * [x^2/2 - ax]
    i0 = k * ( (b**2 - a**2)/2.0 - a*(b - a) )
    # n=1: k * [x^3/3 - ax^2/2]
    i1 = k * ( (b**3 - a**3)/3.0 - a*(b**2 - a**2)/2.0 )
    # n=2: k * [x^4/4 - ax^3/3]
    i2 = k * ( (b**4 - a**4)/4.0 - a*(b**3 - a**3)/3.0 )
    # n=3: k * [x^5/5 - ax^4/4]
    i3 = k * ( (b**5 - a**5)/5.0 - a*(b**4 - a**4)/4.0 )
    
    # 4. R_i = integral( w(x) * (1 - 3(x/L)^2 + 2(x/L)^3) dx)
    R_i = i0 - 3*i2/L2 + 2*i3/L3
    
    # 5. M_i = integral( w(x) * (x - 2x^2/L + x^3/L^2) dx)
    M_i = i1 - 2*i2/L + i3/L2
    
    # 6. R_j = integral( w(x) * (3(x/L)^2 - 2(x/L)^3) dx)
    R_j = 3*i2/L2 - 2*i3/L3
    
    # 7. M_j = integral( w(x) * (x^3/L^2 - x^2/L) dx)
    M_j = i3/L2 - i2/L
    
    return (R_i, M_i, R_j, M_j)

#=======================================================================
# III. UTILIDADES TOPOLÓGICAS Y MATEMÁTICAS PARA TRAMOS DE CARGA
#=======================================================================

def _interpolar_carga_en_punto(lista_tramos, p_norm_buscado):
    """
    Interpola linealmente el valor de carga 'q' para un 'p_norm_buscado'
    dentro de una lista de tramos [(p1, q1), (p2, q2), ...].
    """
    # 1. Verificación de nulidad en el arreglo de entrada
    if not lista_tramos:
        return 0.0
        
    # 2. Control de límites de contorno (fuera del dominio interpolable)
    
        # Caso 1: Antes del inicio de la lista
    if p_norm_buscado < lista_tramos[0][0] - 1e-9:
        return 0.0 # O el valor del primer punto, según convención. 0 es más seguro.
    
        # Caso 2: Después del final de la lista
    if p_norm_buscado > lista_tramos[-1][0] + 1e-9:
        return 0.0 # O el valor del último punto.

    # 3. Búsqueda iterativa del sub-dominio y cálculo del factor de interpolación
    for i in range(len(lista_tramos) - 1):
        p_a, q_a = lista_tramos[i]
        p_b, q_b = lista_tramos[i+1]
        
        if p_a - 1e-9 <= p_norm_buscado <= p_b + 1e-9:
            # Evitar división por cero si los puntos son idénticos
            if abs(p_b - p_a) < 1e-9:
                return q_a
            
            # Interpolación lineal
            factor_t = (p_norm_buscado - p_a) / (p_b - p_a)
            q_interpolado = q_a + factor_t * (q_b - q_a)
            return q_interpolado
            
    # 4. Tolerancia numérica para convergencia en el nodo final
    if abs(p_norm_buscado - lista_tramos[-1][0]) < 1e-9:
        return lista_tramos[-1][1]

    return 0.0 # Fallback

def _sumar_tramos_lineales(lista_tramos_1, lista_tramos_2):
    """
    Suma dos listas de cargas por tramos [(p, q), ...],
    con fusión de puntos cercanos para evitar errores numéricos.
    """
    # 1. Definición del umbral de tolerancia para convergencia geométrica
    TOLERANCIA_FUSION = 1e-4  # 0.1 mm en una viga de 1m. Ajustable.

    # 2. Extracción y ordenamiento del conjunto de coordenadas paramétricas
    puntos_raw = []
    for p, _ in lista_tramos_1: puntos_raw.append(p)
    for p, _ in lista_tramos_2: puntos_raw.append(p)
    
    puntos_raw.sort()
    
    # 3. Fusionar puntos muy cercanos
    if not puntos_raw: return [(0.0, 0.0), (1.0, 0.0)]
    
    puntos_filtrados = [puntos_raw[0]]
    for p in puntos_raw[1:]:
        if p - puntos_filtrados[-1] > TOLERANCIA_FUSION:
            puntos_filtrados.append(p)
        # Si está muy cerca, ignoramos 'p' y nos quedamos con el anterior,
        # asumiendo que son el mismo punto geométrico.

    # 4. Interpolar y sumar
    lista_sumada = []
    for p in puntos_filtrados:
        if p < -1e-9 or p > 1.0 + 1e-9: continue
            
        q1 = _interpolar_carga_en_punto(lista_tramos_1, p)
        q2 = _interpolar_carga_en_punto(lista_tramos_2, p)
        q_total = q1 + q2
        lista_sumada.append((p, q_total))
            
    # 5. Asegurar extremos 0.0 y 1.0
    if not lista_sumada or lista_sumada[0][0] > 1e-9:
        q_start = _interpolar_carga_en_punto(lista_tramos_1, 0.0) + _interpolar_carga_en_punto(lista_tramos_2, 0.0)
        lista_sumada.insert(0, (0.0, q_start))
    
    if lista_sumada[-1][0] < 1.0 - 1e-9:
        q_end = _interpolar_carga_en_punto(lista_tramos_1, 1.0) + _interpolar_carga_en_punto(lista_tramos_2, 1.0)
        lista_sumada.append((1.0, q_end))

    return lista_sumada

#=======================================================================
# IV. DEFINICIÓN DE COMBINACIONES DE ESTADOS DE CARGA
#=======================================================================
class CombinacionCarga:
    """Clase para definir una combinación de carga con sus factores."""
    def __init__(self, nombre, factores, tipo='Norma'):
        self.nombre = nombre
        self.factores = factores
        self.tipo = tipo
    def to_dict(self):
        # 1. Serialización del objeto para persistencia de datos
        return {'nombre': self.nombre, 'factores': self.factores, 'tipo': self.tipo}
    
    @classmethod
    def desde_dict(cls, data):
        # 2. Deserialización del objeto desde un diccionario estructurado
        return cls(data['nombre'], data['factores'], data.get('tipo', 'Usuario'))

#=======================================================================
# V. MOTOR DE PROCESAMIENTO Y DISTRIBUCIÓN DE CARGAS
#=======================================================================
class ProcesadorCargas:
    """
    Clase principal responsable de la orquestación, transformación y ensamble 
    de los estados de carga aplicados sobre la topología estructural.
    """
    def __init__(self, modelo):
        # 1. Inyección de dependencias del modelo matemático global
        self.modelo = modelo
        self.combinaciones_norma = self._get_combinaciones_nb1225002()

    def _get_combinaciones_nb1225002(self):
        """Define las combinaciones de carga estándar de la norma."""
        return [
            CombinacionCarga("Cálculo Simple", {'D': 1.0}),
            CombinacionCarga("1.4D", {'D': 1.4}),
            CombinacionCarga("1.2D + 1.6L + 0.5Lr", {'D': 1.2, 'L': 1.6, 'Lr': 0.5}),
            CombinacionCarga("1.2D + 1.6Lr + 1.0L", {'D': 1.2, 'Lr': 1.6, 'L': 1.0}),
            CombinacionCarga("1.2D + 1.0W + 1.0L + 0.5Lr", {'D': 1.2, 'W': 1.0, 'L': 1.0, 'Lr': 0.5}),
            CombinacionCarga("0.9D + 1.0W", {'D': 0.9, 'W': 1.0}),
        ]

    def _generar_cargas_pp_auto(self):
        """
        Calcula el Peso Propio (PP) Just-in-Time (JIT) para todos los elementos
        (1D y 2D) y genera los vectores, FEPs, cargas distribuidas y logs
        necesarios tanto para el cálculo como para el reporte.
        """
        # 1. Inicialización de contenedores matriciales
        num_gdl = len(self.modelo.nodos) * 6
        vector_pp_total = np.zeros(num_gdl)
        feps_pp_total_dict = defaultdict(lambda: np.zeros(12))
        cargas_dist_pp_total_dict = defaultdict(lambda: {
            'tramos_y': [(0.0, 0.0), (1.0, 0.0)],
            'tramos_z': [(0.0, 0.0), (1.0, 0.0)],
            'axial_x': 0.0,
            'torsion_mx': 0.0
        })
        log_pp_1d = []

        print("[INFO] Calculando PP (JIT) para Elementos 1D...")

        # 1. Procesar Elementos 1D (Vigas/Columnas) 
        for id_elem, (ni, nj, id_mat) in self.modelo.elementos.items():
            if id_mat not in self.modelo.materiales: 
                continue
            
            # Obtener PE y Área
            pe_1d = self.modelo.materiales[id_mat].get('peso_especifico', 0.0)
            if abs(pe_1d) < 1e-9: 
                continue

            try:
                # 3. Extracción de propiedades geométricas transversales
                propiedades = self.modelo.get_propiedades_calculadas(id_mat)
                A = propiedades[2]
                if abs(A) < 1e-9: 
                    continue
                
                # 4. Obtener Transformación
                p1, p2 = self.modelo.nodos[ni], self.modelo.nodos[nj]
                T, L = matriz_transformacion_portico_3d(p1, p2)
                R = T[:3, :3]
                if L < 1e-9: 
                    continue

            except Exception as e:
                print(f"[WARN] Omitiendo PP para Elem {id_elem}: {e}")
                continue

            # 5. Calcular carga local
            w_pp = pe_1d * A # Carga (kN/m)
            w_global = np.array([0.0, 0.0, -w_pp]) # Actúa en Z Global negativo
            w_local = R @ w_global

            # 6. Evaluación de las componentes del vector de Fuerzas de Empotramiento Perfecto
            fep_local = np.zeros(12)
            fep_local[0] = -w_local[0] * L / 2
            fep_local[6] = -w_local[0] * L / 2
            fep_local[1] = -w_local[1] * L / 2
            fep_local[7] = -w_local[1] * L / 2
            fep_local[5] = -w_local[1] * L**2 / 12 # Mz_i
            fep_local[11] = w_local[1] * L**2 / 12 # Mz_j
            fep_local[2] = -w_local[2] * L / 2
            fep_local[8] = -w_local[2] * L / 2
            fep_local[4] = w_local[2] * L**2 / 12  # My_i
            fep_local[10] = -w_local[2] * L**2 / 12 # My_j
            # (No hay torsión 'mt' para PP)

            # 7. Sumar a los totales
            feps_pp_total_dict[id_elem] += fep_local
            fep_global = T.T @ fep_local
            indices_globales = list(range((ni-1)*6, ni*6)) + list(range((nj-1)*6, nj*6))
            vector_pp_total[indices_globales] -= fep_global # FEPs se restan

            # 8. Poblar cargas_dist (para diagramas)
            cargas_dist_pp_total_dict[id_elem]['axial_x'] += w_local[0]
            
            tramos_y_nuevos = [(0.0, w_local[1]), (1.0, w_local[1])] if abs(w_local[1]) > 1e-9 else []
            tramos_z_nuevos = [(0.0, w_local[2]), (1.0, w_local[2])] if abs(w_local[2]) > 1e-9 else []

            if tramos_y_nuevos:
                tramos_y_actuales = cargas_dist_pp_total_dict[id_elem]['tramos_y']
                cargas_dist_pp_total_dict[id_elem]['tramos_y'] = _sumar_tramos_lineales(tramos_y_actuales, tramos_y_nuevos)
            
            if tramos_z_nuevos:
                tramos_z_actuales = cargas_dist_pp_total_dict[id_elem]['tramos_z']
                cargas_dist_pp_total_dict[id_elem]['tramos_z'] = _sumar_tramos_lineales(tramos_z_actuales, tramos_z_nuevos)

            # 9. Registro del proceso para la memoria de cálculo
            log_pp_1d.append({'id_elem': id_elem, 'w_global_z': -w_pp, 'w_local': w_local})

        
        print("[INFO] Calculando PP (JIT) para Losas 2D...")

        # 10. Procesar Losas (2D)
        for id_losa, datos_losa in self.modelo.losas.items():
            pe_2d = datos_losa.get('peso_especifico', 0.0)
            espesor = datos_losa.get('espesor', 0.0)
            
            if abs(pe_2d) < 1e-9 or abs(espesor) < 1e-9:
                continue
                
            wz_pp = -pe_2d * espesor # Carga superficial (hacia abajo)
            
            try:
                # 11. Traducción del plano de carga a fuerzas equivalentes en apoyos lineales
                cargas_generadas, log_datos_losa = traducir_carga_losa_a_cargas_lineales(
                    id_losa, wz_pp, -1, self.modelo
                )
                
                # 12. Inyección de datos al registro global de reporte
                log_datos_losa['tipo'] = f"PP_{log_datos_losa['tipo']}" # Marcarla como PP
                if hasattr(self.modelo, 'datos_reporte_losas'):
                    self.modelo.datos_reporte_losas.append(log_datos_losa)
                
                # 13. Ensamblaje iterativo de cargas tributarias en pórticos adyacentes
                for carga_elem_gen in cargas_generadas:
                    id_elem = carga_elem_gen['id_elemento']
                    datos_carga = carga_elem_gen['datos_carga']
                    
                    if id_elem not in self.modelo.elementos: continue
                    
                    ni, nj, _ = self.modelo.elementos[id_elem]
                    if ni not in self.modelo.nodos or nj not in self.modelo.nodos: continue
                    
                    p1, p2 = self.modelo.nodos[ni], self.modelo.nodos[nj]
                    
                    try:
                        T, L = matriz_transformacion_portico_3d(p1, p2)
                    except ValueError:
                        continue
                    if L < 1e-9: continue
                    
                    tipo_carga_losa = datos_carga[0]
                    fep_local = np.zeros(12)
                    
                    # 14. Procesamiento condicional según el tipo topológico de la carga incidente
                    if tipo_carga_losa == 'uniforme':
                        # (uniforme, wx_local, wy_local, wz_local, mt_local)
                        _, wlx, wly, wlz, mlt = datos_carga 
                        w_local = np.array([wlx, wly, wlz])
                        mt = mlt
                        
                        # Poblar cargas_dist (para diagramas)
                        cargas_dist_pp_total_dict[id_elem]['axial_x'] += w_local[0]
                        cargas_dist_pp_total_dict[id_elem]['torsion_mx'] += mt
                        
                        tramos_y_nuevos = [(0.0, w_local[1]), (1.0, w_local[1])] if abs(w_local[1]) > 1e-9 else []
                        tramos_z_nuevos = [(0.0, w_local[2]), (1.0, w_local[2])] if abs(w_local[2]) > 1e-9 else []

                        if tramos_y_nuevos:
                            tramos_y_actuales = cargas_dist_pp_total_dict[id_elem]['tramos_y']
                            cargas_dist_pp_total_dict[id_elem]['tramos_y'] = _sumar_tramos_lineales(tramos_y_actuales, tramos_y_nuevos)
                        
                        if tramos_z_nuevos:
                            tramos_z_actuales = cargas_dist_pp_total_dict[id_elem]['tramos_z']
                            cargas_dist_pp_total_dict[id_elem]['tramos_z'] = _sumar_tramos_lineales(tramos_z_actuales, tramos_z_nuevos)
                        
                        # 15. Formulación del vector FEP para el patrón uniforme sobre el elemento receptor
                        fep_local[0] = -w_local[0] * L / 2
                        fep_local[6] = -w_local[0] * L / 2
                        fep_local[1] = -w_local[1] * L / 2
                        fep_local[7] = -w_local[1] * L / 2
                        fep_local[5] = -w_local[1] * L**2 / 12 # Mz_i
                        fep_local[11] = w_local[1] * L**2 / 12 # Mz_j
                        fep_local[2] = -w_local[2] * L / 2
                        fep_local[8] = -w_local[2] * L / 2
                        fep_local[4] = w_local[2] * L**2 / 12  # My_i
                        fep_local[10] = -w_local[2] * L**2 / 12 # My_j
                        fep_local[3] = -mt * L / 2
                        fep_local[9] = -mt * L / 2

                    elif tipo_carga_losa == 'tramos_locales':
                        _, eje_local, lista_de_puntos = datos_carga
                        
                        # Poblar cargas_dist (para diagramas)
                        if eje_local == 'y':
                            clave_tramos = 'tramos_y'
                        elif eje_local == 'z':
                            clave_tramos = 'tramos_z'
                        else:
                            continue # Eje no soportado, omitimos esta carga
                            
                        tramos_actuales = cargas_dist_pp_total_dict[id_elem][clave_tramos]
                        cargas_dist_pp_total_dict[id_elem][clave_tramos] = _sumar_tramos_lineales(tramos_actuales, lista_de_puntos)

                        # 16. Calcular FEPs - Integración de superposición para perfiles de carga discontinuos
                        fep_superposicion = np.zeros(4) # (R_i, M_i, R_j, M_j)
                        for i in range(len(lista_de_puntos) - 1):
                            (p_a_norm, q_a) = lista_de_puntos[i]
                            (p_b_norm, q_b) = lista_de_puntos[i+1]
                            a = p_a_norm * L
                            b = p_b_norm * L
                            if abs(b - a) < 1e-9: continue
                            w_unif = q_a
                            w_tria = q_b - q_a
                            if abs(w_unif) > 1e-9:
                                fep_superposicion += np.array(_fep_uniforme_parcial(L, w_unif, a, b))
                            if abs(w_tria) > 1e-9:
                                fep_superposicion += np.array(_fep_triangular_parcial(L, w_tria, a, b))

                        R_i_total, M_i_total, R_j_total, M_j_total = fep_superposicion
                        
                        if eje_local == 'y':
                            fep_local[1] = -R_i_total; fep_local[7] = -R_j_total
                            fep_local[5] = -M_i_total; fep_local[11] = -M_j_total
                        elif eje_local == 'z':
                            fep_local[2] = -R_i_total; fep_local[8] = -R_j_total
                            fep_local[4] = M_i_total; fep_local[10] = M_j_total
                    
                    # 17. Ensamblaje final de aportes tributarios hacia el vector general de solicitación
                    if np.any(fep_local):
                        feps_pp_total_dict[id_elem] += fep_local
                        fep_global = T.T @ fep_local
                        indices_globales = list(range((ni-1)*6, ni*6)) + list(range((nj-1)*6, nj*6))
                        vector_pp_total[indices_globales] -= fep_global

            except Exception as e:
                print(f"[WARN] Omitiendo PP para Losa {id_losa}: Error en distribución: {e}")

        print("[INFO] Cálculo JIT de PP finalizado.")
        return (vector_pp_total, feps_pp_total_dict, cargas_dist_pp_total_dict, log_pp_1d)

    def _agrupar_cargas_por_hipotesis(self):
        """
        Agrupa todas las cargas del modelo por su ID de hipótesis.
        Devuelve los vectores de fuerza globales, FEPs y cargas distribuidas locales.
        AHORA TAMBIÉN DEVUELVE UN LOG DE DATOS.
        """
        # 1. Definición del registro de trazabilidad procedimental
        log_reporte_agrupacion = []

        # 2. Inicialización de tensores acumuladores
        num_gdl = len(self.modelo.nodos) * 6
        vectores_carga_base = defaultdict(lambda: np.zeros(num_gdl))
        feps_base = defaultdict(dict)

        cargas_dist_base = defaultdict(lambda: defaultdict(lambda: {
            'tramos_y': [(0.0, 0.0), (1.0, 0.0)],
            'tramos_z': [(0.0, 0.0), (1.0, 0.0)],
            'axial_x': 0.0,
            'torsion_mx': 0.0
        }))

        # 3. PROCESAR CARGAS NODALES 
        for carga in self.modelo.cargas_nodales:
            id_hipotesis = carga['id_hipotesis']
            id_nodo = carga['id_nodo']
            idx_inicio = (id_nodo - 1) * 6
            vectores_carga_base[id_hipotesis][idx_inicio : idx_inicio + 6] += carga['vector']

            log_reporte_agrupacion.append({'tipo': 'nodal', 'id_hipotesis': id_hipotesis, 'id_nodo': id_nodo, 'vector': carga['vector']})

        # 4. PROCESAR CARGAS DE ELEMENTOS
        for carga in self.modelo.cargas_elementos:
            id_hipotesis = carga['id_hipotesis']
            id_elem = carga['id_elemento']
            
            if id_elem not in self.modelo.elementos: continue
            ni, nj, _ = self.modelo.elementos[id_elem]
            p1, p2 = self.modelo.nodos[ni], self.modelo.nodos[nj]
            
            try:
                T, L = matriz_transformacion_portico_3d(p1, p2)
                R = T[:3, :3]
            except ValueError:
                continue

            if L < 1e-9: continue
            
            tipo_carga = carga['datos_carga'][0]
            fep_local = np.zeros(12)
            w_global = np.zeros(3)
            w_local = np.zeros(3)
            mt = 0.0

            # 5. Cálculo y acumulación paramétrica para distribuciones uniformes explícitas
            if tipo_carga == 'uniforme':
                _, wx, wy, wz, mt_val = carga['datos_carga']
                mt = mt_val
                w_global = np.array([wx, wy, wz])
                w_local = R @ w_global # [wlx, wly, wlz]
                
                cargas_dist_base[id_hipotesis][id_elem]['axial_x'] += w_local[0]
                cargas_dist_base[id_hipotesis][id_elem]['torsion_mx'] += mt
                
                tramos_y_nuevos = []
                if abs(w_local[1]) > 1e-9: # Carga en Y local
                    tramos_y_nuevos = [(0.0, w_local[1]), (1.0, w_local[1])]
                
                tramos_z_nuevos = []
                if abs(w_local[2]) > 1e-9: # Carga en Z local
                    tramos_z_nuevos = [(0.0, w_local[2]), (1.0, w_local[2])]

                if tramos_y_nuevos:
                    tramos_y_actuales = cargas_dist_base[id_hipotesis][id_elem]['tramos_y']
                    cargas_dist_base[id_hipotesis][id_elem]['tramos_y'] = _sumar_tramos_lineales(tramos_y_actuales, tramos_y_nuevos)
                
                if tramos_z_nuevos:
                    tramos_z_actuales = cargas_dist_base[id_hipotesis][id_elem]['tramos_z']
                    cargas_dist_base[id_hipotesis][id_elem]['tramos_z'] = _sumar_tramos_lineales(tramos_z_actuales, tramos_z_nuevos)

                # Asignación FEP para uniforme
                fep_local[0] = -w_local[0] * L / 2
                fep_local[6] = -w_local[0] * L / 2
                fep_local[1] = -w_local[1] * L / 2
                fep_local[7] = -w_local[1] * L / 2
                fep_local[5] = -w_local[1] * L**2 / 12 # Mz_i (FEP) es Horario (-)
                fep_local[11] = w_local[1] * L**2 / 12 # Mz_j (FEP) es Anti-Horario (+)
                fep_local[2] = -w_local[2] * L / 2
                fep_local[8] = -w_local[2] * L / 2
                fep_local[4] = w_local[2] * L**2 / 12  # My_i (FEP) es Anti-Horario (+)
                fep_local[10] = -w_local[2] * L**2 / 12 # My_j (FEP) es Horario (-)
                fep_local[3] = -mt * L / 2
                fep_local[9] = -mt * L / 2

            # 6. Ejecución del algoritmo de superposición para distribuciones de tramos seccionales
            elif tipo_carga == 'tramos_locales':
                # El formato es ('tramos_locales', 'y' o 'z', [(p_norm1, q1), (p_norm2, q2), ...])
                _, eje_local, lista_de_puntos = carga['datos_carga']
                print(f"\n[DEBUG proc_cargas Elem {id_elem} Hip {id_hipotesis}] Procesando 'tramos_locales' Eje='{eje_local}' Puntos={lista_de_puntos}") # <-- PRINT

                if eje_local == 'y':
                    clave_tramos = 'tramos_y'
                elif eje_local == 'z':
                    clave_tramos = 'tramos_z'
                else:
                    print(f"ADVERTENCIA: Eje '{eje_local}' no soportado para tramos en Elem {id_elem}")
                    continue 

                tramos_actuales = cargas_dist_base[id_hipotesis][id_elem][clave_tramos]
                cargas_dist_base[id_hipotesis][id_elem][clave_tramos] = _sumar_tramos_lineales(tramos_actuales, lista_de_puntos)
                
                fep_superposicion = np.zeros(4) # (R_i, M_i, R_j, M_j)
                
                for i in range(len(lista_de_puntos) - 1):
                    (p_a_norm, q_a) = lista_de_puntos[i]
                    (p_b_norm, q_b) = lista_de_puntos[i+1]
                    
                    a = p_a_norm * L
                    b = p_b_norm * L
                    
                    if abs(b - a) < 1e-9: continue
                    
                    w_unif = q_a
                    w_tria = q_b - q_a
                    print(f"  [DEBUG Elem {id_elem} Seg {i}] Tramo [{a:.2f}m - {b:.2f}m], w_unif={w_unif:.2f}, w_tria={w_tria:.2f}")

                    if abs(w_unif) > 1e-9:
                        print(f"    [DEBUG Elem {id_elem} Seg {i}] Llamando _fep_uniforme_parcial(L={L:.2f}, w={w_unif:.2f}, a={a:.2f}, b={b:.2f})") # <-- PRINT
                        fep_u = np.array(_fep_uniforme_parcial(L, w_unif, a, b))
                        print(f"      Resultado FEP Unif: {fep_u}")
                        fep_superposicion += fep_u
                    
                    if abs(w_tria) > 1e-9:
                        print(f"    [DEBUG Elem {id_elem} Seg {i}] Llamando _fep_triangular_parcial(L={L:.2f}, w_pico={w_tria:.2f}, a={a:.2f}, b={b:.2f})") # <-- PRINT
                        fep_t = np.array(_fep_triangular_parcial(L, w_tria, a, b))
                        print(f"      Resultado FEP Tria: {fep_t}")
                        fep_superposicion += fep_t

                R_i_total, M_i_total, R_j_total, M_j_total = fep_superposicion
                print(f"  [DEBUG Elem {id_elem}] FEP 2D Totales (R_i, M_i, R_j, M_j): {fep_superposicion}")
                
                if eje_local == 'y': # Carga en 'y' local -> Momento en 'z' local
                    fep_local[1] = -R_i_total
                    fep_local[7] = -R_j_total
                    fep_local[5] = -M_i_total  # Mz_i (FEP) es Clockwise (-)
                    fep_local[11] = -M_j_total # Mz_j (FEP) es Anti-Clockwise (+) (M_j_total es neg)
                elif eje_local == 'z': # Carga en 'z' local -> Momento en 'y' local
                    fep_local[2] = -R_i_total
                    fep_local[8] = -R_j_total
                    fep_local[4] = M_i_total   # My_i (FEP) es Anti-Clockwise (+) (M_i_total es pos)
                    fep_local[10] = M_j_total # My_j (FEP) es Clockwise (-) (M_j_total es neg)
                print(f"  [DEBUG Elem {id_elem}] fep_local (12 comp) calculado: {fep_local}")
            
            else:
                pass 
            
            # 7. Ensamblaje (COMÚN a todos los tipos que generan FEPs)
            if np.any(fep_local): # Solo ensamblar si hay FEPs
                feps_base[id_hipotesis][id_elem] = feps_base[id_hipotesis].get(id_elem, np.zeros(12)) + fep_local
                
                fep_global = T.T @ fep_local
                indices_globales = list(range((ni-1)*6, ni*6)) + list(range((nj-1)*6, nj*6))
                vectores_carga_base[id_hipotesis][indices_globales] -= fep_global

                log_reporte_agrupacion.append({
                    'tipo': 'elemento', 'id_hipotesis': id_hipotesis, 'id_elem': id_elem,
                    'w_global': w_global, 'w_local': w_local, 'mt': mt, 'fep_local': fep_local, 'fep_global': fep_global,
                    'tipo_carga_aplicada': tipo_carga
                })
        
        # 8. Módulo de traducción bidimensional: Recreación y purga de logs previos
        if hasattr(self.modelo, 'datos_reporte_losas'):
            self.modelo.datos_reporte_losas.clear()
        
        print("--- Iniciando traducción de Cargas Superficiales a Cargas de Elemento ---")

        for id_carga_sup, carga_sup in self.modelo.cargas_superficiales.items():
            try:
                id_losa = carga_sup['id_losa']
                wz = carga_sup['magnitud']
                id_hipotesis = carga_sup['id_hipotesis']
                
                # Asegurarnos que la hipótesis existe en nuestro diccionario
                if id_hipotesis not in vectores_carga_base:
                    vectores_carga_base[id_hipotesis] = np.zeros(num_gdl)

                print(f"  -> Procesando CargaSup {id_carga_sup} en Losa {id_losa} (Hip: {id_hipotesis})...")

                # Llamamos al distribuidor "just-in-time"
                cargas_generadas, log_datos = traducir_carga_losa_a_cargas_lineales(
                    id_losa, wz, id_hipotesis, self.modelo
                )
                
                # Guardamos el log para el reporte
                if hasattr(self.modelo, 'datos_reporte_losas'):
                    self.modelo.datos_reporte_losas.append(log_datos)
                
                # 9. Asignación tributaria de cargas de losa hacia los porticos
                for carga_elem_gen in cargas_generadas:
                    id_elem = carga_elem_gen['id_elemento']
                    datos_carga = carga_elem_gen['datos_carga']
                    
                    if id_elem not in self.modelo.elementos: continue
                    
                    ni, nj, _ = self.modelo.elementos[id_elem]
                    
                    if ni not in self.modelo.nodos or nj not in self.modelo.nodos:
                        print(f"Advertencia: Omitiendo carga generada en Elem {id_elem} por nodos faltantes ({ni}, {nj})")
                        continue
                    p1, p2 = self.modelo.nodos[ni], self.modelo.nodos[nj]
                    
                    try:
                        T, L = matriz_transformacion_portico_3d(p1, p2)
                    except ValueError:
                        continue
                    if L < 1e-9: continue

                    tipo_carga_losa = datos_carga[0]
                    fep_local = np.zeros(12)
                    w_local = np.zeros(3)
                    mt = 0.0

                    if tipo_carga_losa == 'uniforme':

                        _, wlx, wly, wlz, mlt = datos_carga # (uniforme, wx_local, wy_local, wz_local, mt_local)
                        w_local = np.array([wlx, wly, wlz])
                        mt = mlt
                    
                        cargas_dist_base[id_hipotesis][id_elem]['axial_x'] += w_local[0]
                        cargas_dist_base[id_hipotesis][id_elem]['torsion_mx'] += mt
                        
                        tramos_y_nuevos = []
                        if abs(w_local[1]) > 1e-9: # Carga en Y local
                            tramos_y_nuevos = [(0.0, w_local[1]), (1.0, w_local[1])]
                        
                        tramos_z_nuevos = []
                        if abs(w_local[2]) > 1e-9: # Carga en Z local
                            tramos_z_nuevos = [(0.0, w_local[2]), (1.0, w_local[2])]

                        if tramos_y_nuevos:
                            tramos_y_actuales = cargas_dist_base[id_hipotesis][id_elem]['tramos_y']
                            cargas_dist_base[id_hipotesis][id_elem]['tramos_y'] = _sumar_tramos_lineales(tramos_y_actuales, tramos_y_nuevos)
                        
                        if tramos_z_nuevos:
                            tramos_z_actuales = cargas_dist_base[id_hipotesis][id_elem]['tramos_z']
                            cargas_dist_base[id_hipotesis][id_elem]['tramos_z'] = _sumar_tramos_lineales(tramos_z_actuales, tramos_z_nuevos)
        

                        # Asignación FEP para uniforme
                        fep_local[0] = -w_local[0] * L / 2
                        fep_local[6] = -w_local[0] * L / 2
                        fep_local[1] = -w_local[1] * L / 2
                        fep_local[7] = -w_local[1] * L / 2
                        fep_local[5] = -w_local[1] * L**2 / 12 # Mz_i
                        fep_local[11] = w_local[1] * L**2 / 12 # Mz_j
                        fep_local[2] = -w_local[2] * L / 2
                        fep_local[8] = -w_local[2] * L / 2
                        fep_local[4] = w_local[2] * L**2 / 12  # My_i
                        fep_local[10] = -w_local[2] * L**2 / 12 # My_j
                        fep_local[3] = -mt * L / 2
                        fep_local[9] = -mt * L / 2
                    
                    elif tipo_carga_losa == 'tramos_locales':
                        # El formato es ('tramos_locales', 'y' o 'z', [(p_norm1, q1), (p_norm2, q2), ...])
                        _, eje_local, lista_de_puntos = datos_carga
                        print(f"\n[DEBUG proc_cargas Losa->Elem {id_elem} Hip {id_hipotesis}] Procesando 'tramos_locales' Eje='{eje_local}' Puntos={lista_de_puntos}") # <-- PRINT
                        
                        # 10. Bloque de auditoría pos-integración
                        id_viga_target = 3 
                        if id_elem == id_viga_target:
                            print(f"\n[DEBUG SUPERPOSICIÓN] Viga {id_elem} recibiendo carga de Losa...")
                            print(f"   -> Carga Entrante: {lista_de_puntos}")

                            clave_tramos_debug = 'tramos_y' if eje_local == 'y' else 'tramos_z'
                            tramos_antes = cargas_dist_base[id_hipotesis][id_elem][clave_tramos_debug]
                            print(f"   -> Carga Acumulada ANTES: {tramos_antes}")
             
                        if eje_local == 'y':
                            clave_tramos = 'tramos_y'
                        elif eje_local == 'z':
                            clave_tramos = 'tramos_z'
                        else:
                            print(f"ADVERTENCIA: Eje '{eje_local}' no soportado para tramos en Losa->Elem {id_elem}")
                            continue

                        tramos_actuales = cargas_dist_base[id_hipotesis][id_elem][clave_tramos]
                        nueva_lista_sumada = _sumar_tramos_lineales(tramos_actuales, lista_de_puntos)
                        cargas_dist_base[id_hipotesis][id_elem][clave_tramos] = nueva_lista_sumada

                        if id_elem == id_viga_target:
                            print(f"   -> Carga Acumulada DESPUÉS: {nueva_lista_sumada}")
                            puntos_x = [p[0] for p in nueva_lista_sumada]
                            for i in range(len(puntos_x)-1):
                                if puntos_x[i+1] - puntos_x[i] < 1e-4: # Si hay puntos demasiado cerca
                                    print(f"   [¡ALERTA!] Puntos muy cercanos detectados en {puntos_x[i]} y {puntos_x[i+1]}. Posible error de interpolación.")
                        
                        fep_superposicion = np.zeros(4) # (R_i, M_i, R_j, M_j)
                        
                        for i in range(len(lista_de_puntos) - 1):
                            (p_a_norm, q_a) = lista_de_puntos[i]
                            (p_b_norm, q_b) = lista_de_puntos[i+1]
                            
                            a = p_a_norm * L
                            b = p_b_norm * L
                            
                            if abs(b - a) < 1e-9: continue
                            
                            w_unif = q_a
                            w_tria = q_b - q_a
                            
                            print(f"  [DEBUG Losa->Elem {id_elem} Seg {i}] Tramo [{a:.2f}m - {b:.2f}m], w_unif={w_unif:.2f}, w_tria={w_tria:.2f}") 

                            if abs(w_unif) > 1e-9:
                                print(f"    [DEBUG Losa->Elem {id_elem} Seg {i}] Llamando _fep_uniforme_parcial(L={L:.2f}, w={w_unif:.2f}, a={a:.2f}, b={b:.2f})") 
                                fep_u = np.array(_fep_uniforme_parcial(L, w_unif, a, b))
                                print(f"      Resultado FEP Unif: {fep_u}") 
                                fep_superposicion += fep_u
                            
                            if abs(w_tria) > 1e-9:
                                print(f"    [DEBUG Losa->Elem {id_elem} Seg {i}] Llamando _fep_triangular_parcial(L={L:.2f}, w_pico={w_tria:.2f}, a={a:.2f}, b={b:.2f})") 
                                fep_t = np.array(_fep_triangular_parcial(L, w_tria, a, b))
                                print(f"      Resultado FEP Tria: {fep_t}") 
                                fep_superposicion += fep_t

                        R_i_total, M_i_total, R_j_total, M_j_total = fep_superposicion
                        print(f"  [DEBUG Losa->Elem {id_elem}] FEP 2D Totales (R_i, M_i, R_j, M_j): {fep_superposicion}")
                        
                        if eje_local == 'y': # Carga en 'y' local -> Momento en 'z' local
                            fep_local[1] = -R_i_total
                            fep_local[7] = -R_j_total
                            fep_local[5] = -M_i_total # Mz_i (FEP) es Horario (-)
                            fep_local[11] = -M_j_total # Mz_j (FEP) es Anti-Horario (+) (M_j_total es neg)
                        elif eje_local == 'z': # Carga en 'z' local -> Momento en 'y' local
                            fep_local[2] = -R_i_total
                            fep_local[8] = -R_j_total
                            fep_local[4] = M_i_total # My_i (FEP) es Anti-Horario (+) (M_i_total es pos)
                            fep_local[10] = M_j_total # My_j (FEP) es Horario (-) (M_j_total es neg)

                        print(f"  [DEBUG Losa->Elem {id_elem}] fep_local (12 comp) calculado: {fep_local}")
                        
                        pass
                    
                    else:
                        pass

                    # 11. Sumatoria final sobre el subespacio global correspondiente a la matriz incidente
                    if np.any(fep_local):
                        feps_base[id_hipotesis][id_elem] = feps_base[id_hipotesis].get(id_elem, np.zeros(12)) + fep_local
                        
                        fep_global = T.T @ fep_local
                        indices_globales = list(range((ni-1)*6, ni*6)) + list(range((nj-1)*6, nj*6))
                        vectores_carga_base[id_hipotesis][indices_globales] -= fep_global
                        
                        log_reporte_agrupacion.append({
                            'tipo': 'losa_a_elemento', 'id_hipotesis': id_hipotesis, 'id_elem': id_elem,
                            'id_losa_origen': id_losa, 'w_local': w_local, 'mt': mt, 'fep_local': fep_local,
                            'tipo_carga_aplicada': tipo_carga_losa
                        })

            except Exception as e:
                print(f"ADVERTENCIA: No se pudo procesar la carga superficial {id_carga_sup}. Error: {e}")
        
        print("--- Fin de traducción de Cargas Superficiales ---")

        return vectores_carga_base, feps_base, cargas_dist_base, log_reporte_agrupacion

    def resolver_combinaciones(self, usar_timoshenko=True, usar_pp=False):
        """
        Orquestación computacional del método de rigidez para múltiples estados 
        de carga combinados. Gestiona la solución estática del sistema evaluando
        la respuesta estructural frente a envolventes de diseño.
        """
        # 1. Validación inicial del número de variables fundamentales del sistema
        num_gdl = len(self.modelo.nodos) * 6
        if num_gdl == 0: raise ValueError("No hay nodos definidos para el cálculo.")

        # 2. Inicialización de la extracción y categorización de cargas
        vectores_carga_base, feps_base, cargas_dist_base, log_agrupacion = self._agrupar_cargas_por_hipotesis()

        # 3. Solicitud de ensamblaje de la matriz de rigidez unificada
        solucionador = Solucionador3D(self.modelo, usar_timoshenko=usar_timoshenko)
        K_global, datos_ensamblaje_reporte = solucionador.ensamblar_K_global()

        # 4. Declaración del diccionario contenedor de respuestas numéricas
        resultados_por_combinacion = defaultdict(dict)
        
        resultados_por_combinacion['reporte_global_data'] = {
            'ensamblaje': datos_ensamblaje_reporte,
            'agrupacion': log_agrupacion
        }

        # 5. Lógica PP=0 (JIT Concurrente)
        if usar_pp:
            print("[INFO] Flag 'usar_pp' detectado. Generando cargas PP (JIT)...")
            # (Esta función la creamos en la Etapa 2)
            (vector_pp, feps_pp, cargas_dist_pp, log_pp_1d) = self._generar_cargas_pp_auto()
            # Guardar el log para el reporte
            resultados_por_combinacion['reporte_global_data']['log_pp_1d'] = log_pp_1d
        else:
            print("[INFO] Flag 'usar_pp' no detectado. Omitiendo cálculo de PP.")
            # Crear contenedores vacíos (Lógica PP=0)
            (vector_pp, feps_pp, cargas_dist_pp) = (np.zeros(num_gdl), {}, defaultdict(dict))
            resultados_por_combinacion['reporte_global_data']['log_pp_1d'] = [] # Log vacío

        # 6. Agrupar Hipótesis de Usuario
        hipotesis_por_tipo = defaultdict(list)
        for id_hip, datos_hip in self.modelo.hipotesis_de_carga.items():
            hipotesis_por_tipo[datos_hip['tipo']].append(id_hip)

        # 7. Bucle Principal de Combinaciones
        for combo in self.modelo.combinaciones:
            tipos_requeridos = combo.factores.keys()
            
            factor_D = combo.factores.get('D', 0.0)

            # 8. Generador de Casos Alternantes (Usuario)
            grupos_a_combinar = []
            for tipo in tipos_requeridos:
                if hipotesis_por_tipo.get(tipo):
                    grupos_a_combinar.append(hipotesis_por_tipo[tipo])
                else:
                    # Si no hay cargas 'D' de usuario, PERO SÍ hay factor D y SÍ usamos PP,
                    # ponemos un 'None' para que el bucle se ejecute al menos una vez.
                    if tipo == 'D' and usar_pp and abs(factor_D) > 1e-9:
                         grupos_a_combinar.append([None])
                    else:
                         grupos_a_combinar.append([None])

            # 9. Iterar sobre cada caso
            for sub_combinacion_ids in itertools.product(*grupos_a_combinar):
                
                # 10. Lógica de Inyección de PP (Concurrente)
                # Inicializamos los totales CON el PP ya escalado
                fuerza_total_sub_combo = vector_pp * factor_D
                feps_sub_combo = defaultdict(lambda: np.zeros(12))
                cargas_dist_sub_combo = defaultdict(lambda: {
                    'tramos_y': [(0.0, 0.0), (1.0, 0.0)],
                    'tramos_z': [(0.0, 0.0), (1.0, 0.0)],
                    'axial_x': 0.0,
                    'torsion_mx': 0.0
                })
                nombre_sub_calculo_partes = []

                if abs(factor_D) > 1e-9 and usar_pp:
                    nombre_sub_calculo_partes.append("PP_Auto")
                    
                    # Inyectar FEPs PP
                    for id_elem, fep_pp in feps_pp.items():
                        feps_sub_combo[id_elem] += fep_pp * factor_D
                    
                    # Inyectar Cargas Dist PP
                    for id_elem, cargas_pp in cargas_dist_pp.items():
                        cargas_dist_sub_combo[id_elem]['axial_x'] += cargas_pp['axial_x'] * factor_D
                        cargas_dist_sub_combo[id_elem]['torsion_mx'] += cargas_pp['torsion_mx'] * factor_D
                        
                        tramos_y_pp_fact = [(p, q * factor_D) for p, q in cargas_pp.get('tramos_y', [])]
                        tramos_z_pp_fact = [(p, q * factor_D) for p, q in cargas_pp.get('tramos_z', [])]

                        if tramos_y_pp_fact:
                            cargas_dist_sub_combo[id_elem]['tramos_y'] = _sumar_tramos_lineales(
                                cargas_dist_sub_combo[id_elem]['tramos_y'], tramos_y_pp_fact
                            )
                        if tramos_z_pp_fact:
                            cargas_dist_sub_combo[id_elem]['tramos_z'] = _sumar_tramos_lineales(
                                cargas_dist_sub_combo[id_elem]['tramos_z'], tramos_z_pp_fact
                            )
                
                # 11. Suma de Cargas de Usuario (Alternantes) ---
                # Este bucle ahora suma "encima" de los vectores de PP
                for id_hip in sub_combinacion_ids:
                    if id_hip is None:
                        continue

                    tipo_carga = self.modelo.hipotesis_de_carga[id_hip]['tipo']
                    factor = combo.factores[tipo_carga]
                    
                    if id_hip in vectores_carga_base:
                        fuerza_total_sub_combo += vectores_carga_base[id_hip] * factor
                    
                    if id_hip in feps_base:
                        for id_elem, fep in feps_base[id_hip].items():
                            feps_sub_combo[id_elem] += fep * factor
                    
                    if id_hip in cargas_dist_base:
                         for id_elem, cargas_elem_base in cargas_dist_base[id_hip].items():
                             cargas_dist_sub_combo[id_elem]['axial_x'] += cargas_elem_base['axial_x'] * factor
                             cargas_dist_sub_combo[id_elem]['torsion_mx'] += cargas_elem_base['torsion_mx'] * factor
                             
                             tramos_y_fact = [(p, q * factor) for p, q in cargas_elem_base['tramos_y'] if any(abs(q) > 1e-9 for _, q in cargas_elem_base['tramos_y'])]
                             tramos_z_fact = [(p, q * factor) for p, q in cargas_elem_base['tramos_z'] if any(abs(q) > 1e-9 for _, q in cargas_elem_base['tramos_z'])]

                             if tramos_y_fact:
                                 cargas_dist_sub_combo[id_elem]['tramos_y'] = _sumar_tramos_lineales(cargas_dist_sub_combo[id_elem]['tramos_y'], tramos_y_fact)
                             if tramos_z_fact:
                                 cargas_dist_sub_combo[id_elem]['tramos_z'] = _sumar_tramos_lineales(cargas_dist_sub_combo[id_elem]['tramos_z'], tramos_z_fact)
                    
                    nombre_sub_calculo_partes.append(self.modelo.hipotesis_de_carga[id_hip]['nombre'])
                
                # 12. Resolución
                if not nombre_sub_calculo_partes:
                    continue # No había ni PP ni cargas de usuario para este tipo

                nombre_sub_calculo = "; ".join(sorted(nombre_sub_calculo_partes))
                
                resultados_completos = solucionador.resolver(fuerza_total_sub_combo, K_global, dict(feps_sub_combo))
                
                resultados_por_combinacion[combo.nombre][nombre_sub_calculo] = {
                    'desplazamientos': resultados_completos['desplazamientos'],
                    'reacciones': resultados_completos['reacciones'],
                    'fuerzas_internas': resultados_completos['fuerzas_internas'],
                    'cargas_distribuidas': dict(cargas_dist_sub_combo),
                    'reporte_resolucion': resultados_completos['reporte_resolucion'],
                    'reporte_vectores': {
                        'F_total': fuerza_total_sub_combo,
                        'FEP_elem': dict(feps_sub_combo)
                    }
                }
            
        if len(resultados_por_combinacion) <= 1: 
            raise ValueError("Ninguna combinación de carga pudo ser calculada. Verifique que las cargas definidas correspondan a los tipos de carga en sus combinaciones, o que al menos exista una hipótesis de carga.")

        return dict(resultados_por_combinacion)