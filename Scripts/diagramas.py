"""
Módulo: diagramas.py
Descripción: Calcula y discretiza las ecuaciones de momento, cortante y fuerza 
axial a lo largo de los elementos 1D para generar los datos necesarios que 
permitan dibujar los diagramas de fuerzas internas.
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
from calc import matriz_transformacion_portico_3d

class GeneradorDiagramas:
    def __init__(self, modelo):
        if not modelo:
            raise ValueError("Se requiere un modelo válido.")
        self.modelo = modelo

    def get_longitud_elemento(self, id_elem):
        if id_elem not in self.modelo.elementos: return 0
        ni, nj, _ = self.modelo.elementos[id_elem]
        p1 = np.array(self.modelo.nodos[ni]); p2 = np.array(self.modelo.nodos[nj])
        return np.linalg.norm(p2 - p1)

    def _interpolar_carga_en_punto(self, lista_tramos, p_norm_buscado):
        """
        Interpola linealmente el valor de carga 'q' para un 'p_norm_buscado'
        dentro de una lista de tramos [(p1, q1), (p2, q2), ...].
        (Este es un método auxiliar para la integración).
        """
        if not lista_tramos:
            return 0.0
        
        if p_norm_buscado < lista_tramos[0][0] - 1e-9:
            return 0.0
        
        if p_norm_buscado > lista_tramos[-1][0] + 1e-9:
            return 0.0

        for i in range(len(lista_tramos) - 1):
            p_a, q_a = lista_tramos[i]
            p_b, q_b = lista_tramos[i+1]
            
            if p_a - 1e-9 <= p_norm_buscado <= p_b + 1e-9:
                if abs(p_b - p_a) < 1e-9: return q_a
                factor_t = (p_norm_buscado - p_a) / (p_b - p_a)
                q_interpolado = q_a + factor_t * (q_b - q_a)
                return q_interpolado
                
        if abs(p_norm_buscado - lista_tramos[-1][0]) < 1e-9:
            return lista_tramos[-1][1]

        return 0.0 

    def _crear_puntos_evaluacion(self, L, cargas_dist, n_puntos_base):
        """
        Crea una lista de posiciones 'x' para evaluar el diagrama,
        asegurando que se incluyan todos los "kinks" (quiebres)
        de las cargas por tramos.
        """
        puntos_x = set()
        
        for x in np.linspace(0, L, n_puntos_base):
            puntos_x.add(x)
        
        if cargas_dist:
            for p_norm, _ in cargas_dist.get('tramos_y', []):
                puntos_x.add(p_norm * L)
            for p_norm, _ in cargas_dist.get('tramos_z', []):
                puntos_x.add(p_norm * L)
                
        puntos_finales = sorted(list(puntos_x))
        if not puntos_finales or puntos_finales[0] > 1e-9:
            puntos_finales.insert(0, 0.0)
        if not puntos_finales or puntos_finales[-1] < L - 1e-9:
            puntos_finales.append(L)
            
        return puntos_finales

    def _get_datos_elemento_y_cargas(self, id_elem, resultados_especificos):
        """
        Obtiene las fuerzas nodales y las cargas distribuidas para un caso de resultado específico.
        MODIFICADO para leer el nuevo formato de diccionario de cargas.
        """
        ni, nj, _ = self.modelo.elementos[id_elem]
        p1, p2 = self.modelo.nodos[ni], self.modelo.nodos[nj]
        try:
            _, L = matriz_transformacion_portico_3d(p1, p2)
        except ValueError:
            L = 0

        if not resultados_especificos:
            
            return np.zeros(12), {}, L
        
        fuerzas_internas_dict = resultados_especificos.get('fuerzas_internas', {})
        f_local = fuerzas_internas_dict.get(id_elem, np.zeros(12))

        cargas_dist_combo = resultados_especificos.get('cargas_distribuidas', {})
        
        cargas_dict_elem = cargas_dist_combo.get(id_elem, {})
        return f_local, cargas_dict_elem, L

    def get_diagrama(self, id_elem, resultados_o_nombre_combo, tipo_efecto, n_puntos=51):
        """
        Calcula los puntos (x, y) para un diagrama de esfuerzos.
        AHORA CON INTEGRACIÓN NUMÉRICA para cargas por tramos.
        """
        resultados_a_usar = None 

        if isinstance(resultados_o_nombre_combo, dict):
            resultados_a_usar = resultados_o_nombre_combo
        elif isinstance(resultados_o_nombre_combo, str):
            nombre_combo = resultados_o_nombre_combo
            if self.modelo and self.modelo.resultados_calculo and nombre_combo in self.modelo.resultados_calculo:
                sub_casos = self.modelo.resultados_calculo[nombre_combo]
                if sub_casos:
                    primer_nombre_sub_caso = next(iter(sub_casos.keys()))
                    resultados_a_usar = sub_casos.get(primer_nombre_sub_caso)
        
        if not isinstance(resultados_a_usar, dict):
            print(f"[WARN] get_diagrama: No se pudieron obtener resultados válidos para '{resultados_o_nombre_combo}'. Devolviendo diagrama vacío.")
            return np.array([0]), np.array([0])
        f_local, cargas_dist, L = self._get_datos_elemento_y_cargas(id_elem, resultados_a_usar)

        if L < 1e-9: return np.array([0]), np.array([0])

        Px_i, Py_i, Pz_i, Mx_i, My_i, Mz_i = f_local[:6]
        
        puntos_x = self._crear_puntos_evaluacion(L, cargas_dist, n_puntos)
        n_puntos_total = len(puntos_x)
        y = np.zeros(n_puntos_total)
        x_final = np.array(puntos_x)
        
        if tipo_efecto == 'Axial (Px)':
            q_axial = cargas_dist.get('axial_x', 0.0)
            for i, x in enumerate(puntos_x):
                # Fórmula simple: P(x) = P_i + q_x * x
                y[i] = -Px_i - q_axial * x
                
        elif tipo_efecto == 'Torsión (Mx)':
            q_torsion = cargas_dist.get('torsion_mx', 0.0)
            for i, x in enumerate(puntos_x):
                # Fórmula simple: T(x) = T_i + q_mx * x
                y[i] = Mx_i + q_torsion * x
        
        # Carga en Z-local -> flexión alrededor de Y-local (My)
        elif tipo_efecto == 'Cortante (Pz)' or tipo_efecto == 'Momento (My)':
            # CONVENCIÓN: Carga en 'Z' local -> Cortante Pz, Momento My
            # dVz/dx = -qz  (¡OJO! Signo negativo)
            # dMy/dx = Vz
            
            Vz_actual = -Pz_i
            My_actual = My_i
            lista_tramos = cargas_dist.get('tramos_z', [(0.0, 0.0), (1.0, 0.0)])
            
            # INVERTIMOS EL SIGNO SOLO PARA EL GRÁFICO DE CORTANTE
            y[0] = -Vz_actual if tipo_efecto == 'Cortante (Pz)' else My_actual

            for i in range(1, n_puntos_total):
                x0 = puntos_x[i-1]
                x1 = puntos_x[i]
                dx = x1 - x0
                
                if dx < 1e-9: 
                    y[i] = y[i-1]
                    continue
                
                # Obtener cargas (q) en los puntos
                p_norm_0 = x0 / L if L > 1e-9 else 0.0
                p_norm_1 = x1 / L if L > 1e-9 else 0.0
                q_z_0 = self._interpolar_carga_en_punto(lista_tramos, p_norm_0)
                q_z_1 = self._interpolar_carga_en_punto(lista_tramos, p_norm_1)
                
                # Integrar para Vz (área de trapecio)
                area_carga_z = (q_z_0 + q_z_1) / 2.0 * dx
                Vz_siguiente = Vz_actual - area_carga_z # dVz/dx = -qz
                
                # Integrar para My (integral exacta de cortante lineal)
                # M(x1) = M0 + V0*dx - (q0*dx^2 / 2) - ((q1-q0)*dx^2 / 6)
                My_siguiente = My_actual - (Vz_actual * dx) + (q_z_0 * dx**2 / 2) + ((q_z_1 - q_z_0) * dx**2 / 6) # dMy/dx = -Vz
                
                if tipo_efecto == 'Cortante (Pz)':
                    # INVERTIMOS EL SIGNO DEL CORTANTE PARA EL PLOT
                    y[i] = -Vz_siguiente
                else:
                    y[i] = My_siguiente
                
                Vz_actual = Vz_siguiente
                My_actual = My_siguiente

        # Carga en Y-local -> flexión alrededor de Z-local (Mz)
        elif tipo_efecto == 'Cortante (Py)' or tipo_efecto == 'Momento (Mz)':
            # CONVENCIÓN: Carga en 'Y' local -> Cortante Py, Momento Mz
            # dVy/dx = qy  (¡OJO! Signo positivo)
            # dMz/dx = -Vy (¡OJO! Signo negativo)
            
            Vy_actual = Py_i
            Mz_actual = Mz_i
            lista_tramos = cargas_dist.get('tramos_y', [(0.0, 0.0), (1.0, 0.0)])
            
            # Invertir signo del diagrama (salida negada)
            y[0] = -Vy_actual if tipo_efecto == 'Cortante (Py)' else -Mz_actual

            for i in range(1, n_puntos_total):
                x0 = puntos_x[i-1]
                x1 = puntos_x[i]
                dx = x1 - x0

                if dx < 1e-9: 
                    y[i] = y[i-1]
                    continue
                
                # Obtener cargas (q) en los puntos
                p_norm_0 = x0 / L if L > 1e-9 else 0.0
                p_norm_1 = x1 / L if L > 1e-9 else 0.0
                q_y_0 = self._interpolar_carga_en_punto(lista_tramos, p_norm_0)
                q_y_1 = self._interpolar_carga_en_punto(lista_tramos, p_norm_1)
                
                # Integrar para Vy (área de trapecio)
                area_carga_y = (q_y_0 + q_y_1) / 2.0 * dx
                Vy_siguiente = Vy_actual + area_carga_y # dVy/dx = qy
                
                # Integrar para Mz (integral exacta de cortante lineal)
                # M(x1) = M0 - V0*dx - (q0*dx^2 / 2) - ((q1-q0)*dx^2 / 6)
                Mz_siguiente = Mz_actual - (Vy_actual * dx) - (q_y_0 * dx**2 / 2) - ((q_y_1 - q_y_0) * dx**2 / 6) # dMz/dx = -Vy
                
                if tipo_efecto == 'Cortante (Py)':
                    y[i] = -Vy_siguiente
                else:
                    y[i] = -Mz_siguiente
                
                Vy_actual = Vy_siguiente
                Mz_actual = Mz_siguiente

        return x_final, y