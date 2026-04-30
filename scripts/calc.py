"""
Módulo: calc.py
Descripción: Subrutinas matemáticas y utilidades de cálculo matricial para el 
motor de rigidez. Contiene las definiciones de matrices de rigidez local y 
matrices de transformación de coordenadas para elementos 1D espaciales.
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

import numpy as np

#=======================================================================
# I. MATRIZ DE TRANSFORMACIÓN DE COORDENADAS PARA PÓRTICOS 3D
#=======================================================================
def matriz_transformacion_portico_3d(p1, p2):
    """
    Genera la matriz de transformación de coordenadas espaciales (12x12) 
    que relaciona el sistema de coordenadas local del elemento con el 
    sistema global de la estructura.
    """
    # 1. Determinación del vector direccional y longitud geométrica del elemento
    v = np.array(p2) - np.array(p1)
    L = np.linalg.norm(v)
    if L < 1e-9: raise ValueError("La longitud del elemento de pórtico no puede ser cero.")

    # 2. Vector unitario correspondiente al eje X local (eje longitudinal de la barra)
    vx = v / L

    # 3. Orientación del eje Z global utilizado como referencia espacial
    eje_Z_global = np.array([0.0, 0.0, 1.0])

    # 4. Cálculo de vectores unitarios transversales (ejes Y y Z locales)
    if np.allclose(np.abs(vx), eje_Z_global):
        # Caso particular: Elemento puramente vertical (columna perfecta)
        vy = np.array([1.0, 0.0, 0.0])
        vz = np.cross(vx, vy)
    else:
        # Caso general: Elemento con inclinación respecto a la vertical
        vy = np.cross(eje_Z_global, vx)
        vy /= np.linalg.norm(vy)
        vz = np.cross(vx, vy)

    # 5. Ensamblaje de la matriz de rotación (3x3) y proyección a la matriz de transformación (12x12)
    R = np.vstack([vx, vy, vz]); T = np.zeros((12, 12))
    for i in range(4): T[i*3:(i+1)*3, i*3:(i+1)*3] = R
    return T, L

#=======================================================================
# II. MATRIZ DE RIGIDEZ LOCAL DEL ELEMENTO (EULER-BERNOULLI / TIMOSHENKO)
#=======================================================================
def matriz_rigidez_local_portico_3d(L, E, G, A, J, Iy, Iz, Ay, Az, usar_timoshenko=True):
    """
    Formulación de la matriz de rigidez elemental (12x12) en el sistema de 
    coordenadas locales. El algoritmo permite alternar entre la teoría clásica 
    de Euler-Bernoulli y la teoría de Timoshenko.
    """
    # 1. Componentes de rigidez axial y torsional básicas
    EA_L=E*A/L
    GJ_L=G*J/L 

    # 2. Factores adimensionales de corrección por cortante (Teoría de Timoshenko)
    if usar_timoshenko and Ay > 1e-12 and Az > 1e-12:
        # Factor de cortante para el plano X-Y (flexión Mz)
        phi_z = (12 * E * Iz) / (G * Ay * L**2)
        # Factor de cortante para el plano X-Z (flexión My)
        phi_y = (12 * E * Iy) / (G * Az * L**2)
    else:
        # Si no se usa Timoshenko (o áreas son cero), los factores son 0
        # y las ecuaciones se reducen a Euler-Bernoulli.
        phi_y = 0.0
        phi_z = 0.0
    
    # 3. Denominadores modificados para términos de flexión
    den_y = 1.0 + phi_y
    den_z = 1.0 + phi_z

    # 4. Cálculo de términos de rigidez a flexión y cortante (Plano X-Y, Momento Mz, Cortante Vy)
    EIz_L3 = (12 * E * Iz) / (L**3 * den_z)
    EIz_L2 = (6 * E * Iz) / (L**2 * den_z)
    EIz_L_4 = ((4.0 + phi_z) * E * Iz) / (L * den_z)
    EIz_L_2 = ((2.0 - phi_z) * E * Iz) / (L * den_z)

    # 5. Cálculo de términos de rigidez a flexión y cortante (Plano X-Z, Momento My, Cortante Vz)
    EIy_L3 = (12 * E * Iy) / (L**3 * den_y)
    EIy_L2 = (6 * E * Iy) / (L**2 * den_y)
    EIy_L_4 = ((4.0 + phi_y) * E * Iy) / (L * den_y)
    EIy_L_2 = ((2.0 - phi_y) * E * Iy) / (L * den_y)

    # 6. Ensamblaje y retorno explícito de la matriz de rigidez local 12x12
    return np.array([
        [EA_L,0,0,0,0,0,-EA_L,0,0,0,0,0],
        [0,EIz_L3,0,0,0,EIz_L2,0,-EIz_L3,0,0,0,EIz_L2],
        [0,0,EIy_L3,0,-EIy_L2,0,0,0,-EIy_L3,0,-EIy_L2,0],
        [0,0,0,GJ_L,0,0,0,0,0,-GJ_L,0,0],
        [0,0,-EIy_L2,0,EIy_L_4,0,0,0,EIy_L2,0,EIy_L_2,0],
        [0,EIz_L2,0,0,0,EIz_L_4,0,-EIz_L2,0,0,0,EIz_L_2],
        [-EA_L,0,0,0,0,0,EA_L,0,0,0,0,0],
        [0,-EIz_L3,0,0,0,-EIz_L2,0,EIz_L3,0,0,0,-EIz_L2],
        [0,0,-EIy_L3,0,EIy_L2,0,0,0,EIy_L3,0,EIy_L2,0],
        [0,0,0,-GJ_L,0,0,0,0,0,GJ_L,0,0],
        [0,0,-EIy_L2,0,EIy_L_2,0,0,0,EIy_L2,0,EIy_L_4,0],
        [0,EIz_L2,0,0,0,EIz_L_2,0,-EIz_L2,0,0,0,EIz_L_4]])

#=======================================================================
# III. CLASE PRINCIPAL: MOTOR DE RESOLUCIÓN MATRICIAL
#=======================================================================
class Solucionador3D:
    """
    Clase contenedora que ejecuta el Análisis Matricial de Estructuras.
    Se encarga de orquestar el ensamblaje de la matriz de rigidez global
    y la resolución algorítmica del sistema fundamental de ecuaciones.
    """
    def __init__(self, modelo, usar_timoshenko=True):
        # 1. Instanciación del modelo geométrico y de cargas
        self.modelo = modelo
        self.usar_timoshenko = usar_timoshenko

        # 2. Diccionario de almacenamiento precalculado de propiedades mecánicas y geométricas
        self.propiedades_porticos = {}
        ids_portico = {e[2] for e in modelo.elementos.values()}
        for id_mat in ids_portico:
            if id_mat in modelo.materiales:
                 self.propiedades_porticos[id_mat] = modelo.get_propiedades_calculadas(id_mat)
    
#=======================================================================
# IV. ENSAMBLAJE DE LA MATRIZ DE RIGIDEZ GLOBAL
#=======================================================================
    def ensamblar_K_global(self):
        """
        Calcula y superpone las contribuciones de rigidez elementales (k) en las 
        posiciones topológicas correctas dentro de la Matriz de Rigidez Global (K).
        """
        # 1. Inicialización de la estructura de datos para la Memoria de Cálculo (Auditoría)
        datos_reporte = {
            'log_ensamblaje': [],
            'k_locales': {},
            'T_matrices': {},
            'K_global_elem': {},
            'K_global': None
        }
        log = datos_reporte['log_ensamblaje']
        
        # 2. Definición de la dimensión de la matriz global (6 GDL totales por cada nodo)
        gdl_totales = len(self.modelo.nodos) * 6
        K_global = np.zeros((gdl_totales, gdl_totales))
        log.append("--- INICIO: Ensamblaje de Matriz de Rigidez Global ---")
        
        # 3. Iteración sobre la topología del modelo estructural
        for id_elem, (ni, nj, mat_id) in self.modelo.elementos.items():
            log.append(f"  -> Ensamblando Pórtico E{id_elem} (Nodos {ni}-{nj})")
            p1, p2 = self.modelo.nodos[ni], self.modelo.nodos[nj]

            # 4. Extracción de propiedades y conversión de módulos elásticos a unidades base (kPa)
            E, G, A, J, Iy, Iz, Ay, Az = self.propiedades_porticos[mat_id]
            EkPa= E*1000
            GkPa= G*1000
            
            # 5. Cálculo de matrices elementales del pórtico 3D
            T, L = matriz_transformacion_portico_3d(p1, p2)
            K_local = matriz_rigidez_local_portico_3d(L, EkPa, GkPa, A, J, Iy, Iz, Ay, Az, self.usar_timoshenko)
            
            # 6. Transformación por congruencia de la matriz elemental al sistema global
            K_global_elem = T.T @ K_local @ T
            
            # 7. Almacenamiento temporal de matrices para trazabilidad del reporte
            datos_reporte['k_locales'][id_elem] = K_local
            datos_reporte['T_matrices'][id_elem] = T
            datos_reporte['K_global_elem'][id_elem] = K_global_elem
            
            # 8. Mapeo de sub-índices y superposición aditiva en la matriz K global
            gdl = list(range((ni-1)*6, ni*6)) + list(range((nj-1)*6, nj*6))
            for i in range(12):
                for j in range(12):
                    K_global[gdl[i], gdl[j]] += K_global_elem[i, j]

        log.append(f"--- FIN: Ensamblaje explícito completado. Dimensión de K_global: {K_global.shape} ---")
        
        # 9. Inyección del resultado en los datos del reporte y retorno de la Matriz Global
        datos_reporte['K_global'] = K_global 
        return K_global, datos_reporte 

#=======================================================================
# V. RESOLUCIÓN MATRICIAL Y POST-PROCESO DE RESULTADOS
#=======================================================================
    def resolver(self, vector_fuerzas, K_global, fep_por_elemento={}):
        """
        Aplica las condiciones de borde, ejecuta la resolución algebraica del sistema 
        reducido para hallar los desplazamientos nodales y realiza el post-proceso 
        de reacciones y solicitaciones internas.
        """
        # 1. Inicialización de contenedor de datos para trazabilidad algorítmica
        datos_reporte_resolucion = {
            'log_resolucion': [],
            'gdl_totales': 0,
            'gdl_libres': [],
            'gdl_restringidos': [],
            'K_reducida': None,
            'F_reducido': None,
            'cond_K_reducida': 0.0
        }
        log = datos_reporte_resolucion['log_resolucion']
        
        # 2. Identificación geométrica de grados de libertad (GDL) libres y restringidos (apoyos)
        gdl_totales = len(self.modelo.nodos) * 6
        gdl_restringidos = [
            (id_nodo - 1) * 6 + i 
            for id_nodo, restr in self.modelo.apoyos.items() 
            for i, r_bool in enumerate(restr) if r_bool 
        ]
        gdl_libres = [i for i in range(gdl_totales) if i not in gdl_restringidos]
        
        # Almacenamiento de variables de estado para el reporte
        datos_reporte_resolucion['gdl_totales'] = gdl_totales
        datos_reporte_resolucion['gdl_libres'] = gdl_libres
        datos_reporte_resolucion['gdl_restringidos'] = gdl_restringidos

        log.append(f"--- INICIO: Resolución del sistema de ecuaciones ---")
        log.append(f"  GDL Totales: {gdl_totales}, Libres: {len(gdl_libres)}, Restringidos: {len(gdl_restringidos)}")

         # 3. Partición de la matriz global para obtener el subsistema matemáticamente resoluble
        K_reducida = K_global[np.ix_(gdl_libres, gdl_libres)]
        F_reducida = vector_fuerzas.copy()[gdl_libres]

        # 4. Verificación de la estabilidad numérica del sistema estructural
        cond_k = 0.0
        try:
            cond_k = np.linalg.cond(K_reducida)
            print(f"  -> Condición de la matriz de rigidez reducida: {cond_k:.2e}")
            log.append(f"  -> Condición de la matriz de rigidez reducida: {cond_k:.2e}")
        except np.linalg.LinAlgError:
            print("  -> Advertencia: Matriz singular, la condición no puede ser calculada.")
            log.append("  -> Advertencia: Matriz singular, la condición no puede ser calculada.")

        datos_reporte_resolucion['K_reducida'] = K_reducida
        datos_reporte_resolucion['F_reducido'] = F_reducida
        datos_reporte_resolucion['cond_K_reducida'] = cond_k
        
        # 5. Resolución computacional del vector de desplazamientos [ d ] delegada a NumPy
        try:
            d_reducidos = np.linalg.solve(K_reducida, F_reducida)
        except np.linalg.LinAlgError:
            raise RuntimeError("La estructura es inestable (matriz singular). Verifique los apoyos y la conectividad.")

        # 6. Reconstrucción del vector de desplazamientos general incluyendo condiciones de borde nulas
        desplazamientos = np.zeros(gdl_totales)
        desplazamientos[gdl_libres] = d_reducidos

        print("  -> Desplazamientos calculados.")
        log.append("  -> Desplazamientos calculados.")

        # 7. Post-proceso: Determinación analítica de las reacciones en los apoyos
        reacciones = (K_global @ desplazamientos) - vector_fuerzas

        print("  -> Reacciones en apoyos calculadas.")
        log.append("  -> Reacciones en apoyos calculadas.")
        
        # 8. Post-proceso: Extracción de esfuerzos internos elementales
        fuerzas_internas = {}
        print("--- INICIO: Cálculo de Fuerzas Internas en Elementos Locales ---")
        log.append("--- INICIO: Cálculo de Fuerzas Internas en Elementos Locales ---")

        for id_elem, (ni, nj, mat_id) in self.modelo.elementos.items():
            p1, p2 = self.modelo.nodos[ni], self.modelo.nodos[nj]

            # Recálculo de las matrices locales específicas de cada elemento
            E, G, A, J, Iy, Iz, Ay, Az = self.propiedades_porticos[mat_id]
            EkPa = E * 1000
            GkPa = G * 1000
            T, L = matriz_transformacion_portico_3d(p1, p2)
            K_local = matriz_rigidez_local_portico_3d(L, EkPa, GkPa, A, J, Iy, Iz, Ay, Az, self.usar_timoshenko)

            # Extracción del sub-vector de desplazamientos asociado a los nodos del elemento
            gdl = list(range((ni-1)*6, ni*6)) + list(range((nj-1)*6, nj*6))

            # Transformación de desplazamientos al sistema local (T @ d_global)
            d_local = T @ desplazamientos[gdl]

            # Superposición de efectos: Fuerzas por desplazamiento + Fuerzas de Empotramiento Perfecto (FEP)
            fep = fep_por_elemento.get(id_elem, np.zeros(12))
            fuerzas_internas[id_elem] = (K_local @ d_local) + fep
        
        print("--- FIN: Cálculo de Fuerzas y Reacciones completado. ---")
        log.append("--- FIN: Cálculo de Fuerzas y Reacciones completado. ---")
        
        # 9. Retorno consolidado de los datos computados del análisis estructural
        resultados_completos = {
            'desplazamientos': desplazamientos,
            'reacciones': reacciones,
            'fuerzas_internas': fuerzas_internas,
            'reporte_resolucion': datos_reporte_resolucion
        }
        return resultados_completos