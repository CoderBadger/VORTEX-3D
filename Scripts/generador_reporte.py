"""
Módulo: generador_reporte.py
Descripción: Extrae los resultados del motor de cálculo (desplazamientos, 
reacciones, fuerzas internas) y formatea la salida para crear memorias de 
cálculo y reportes estructurados.
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
from datetime import datetime
from collections import defaultdict
try:
    from diagramas import GeneradorDiagramas
except ImportError:
    GeneradorDiagramas = None

# --- Funciones de Formateo de Texto ---

def _formatear_matriz(matriz, titulo, gdl_libres=None, max_dim=18):
    """
    Formatea una matriz NumPy como texto para el reporte.
    Si gdl_libres se proporciona, mapea los índices.
    """
    reporte = [f"  {titulo}:"]
    
    if matriz is None or matriz.size == 0:
        reporte.append("    (Matriz no disponible o vacía)")
        return reporte

    filas, columnas = matriz.shape

    if filas > max_dim or columnas > max_dim:
        reporte.append(f"    (Matriz de {filas}x{columnas}. Mostrando resumen de la diagonal)")
        if gdl_libres:
            indices = [gdl_libres[i] for i in range(min(filas, max_dim))]
        else:
            indices = list(range(min(filas, max_dim)))
        
        for i, idx in enumerate(indices):
            reporte.append(f"    [GDL {idx+1:2d}] -> {matriz[i, i]: 12.5e}")
        return reporte

    # Mapeo de índices a GDL si se proporciona
    if gdl_libres:
        indices_f = [gdl_libres[i] for i in range(filas)]
        indices_c = [gdl_libres[j] for j in range(columnas)]
    else:
        indices_f = list(range(filas))
        indices_c = list(range(columnas))

    # Encabezado de columnas (GDL)
    encabezado = "    GDL   |"
    for idx in indices_c:
        encabezado += f" {idx+1:9d}"
    reporte.append(encabezado)
    reporte.append("    " + "-" * (len(encabezado) - 4))

    # Filas
    for i in range(filas):
        linea = f"    {indices_f[i]+1:<5d} |"
        for j in range(columnas):
            linea += f" {matriz[i, j]: 9.2e}"
        reporte.append(linea)
    
    return reporte

def _formatear_vector(vector, titulo, gdl_libres=None):
    """Formatea un vector NumPy para el reporte."""
    reporte = [f"  {titulo} ({vector.size}x1):"]
    
    if vector is None or vector.size == 0:
        reporte.append("    (Vector no disponible o vacío)")
        return reporte
        
    if gdl_libres:
        indices = gdl_libres
    else:
        indices = list(range(vector.size))
    
    for i, idx in enumerate(indices):
        reporte.append(f"    GDL {idx+1:<5d}: {vector[i]: 12.5e}")
    return reporte

def _formatear_vector_fuerzas_internas(vector):
    """Formatea el vector de 12 GDL de fuerzas internas."""
    labels = ["Px", "Py", "Pz", "Mx", "My", "Mz"]
    lineas = []
    lineas.append("                     Px           Py           Pz           Mx           My           Mz")
    lineas.append("    Nodo i:  " + " ".join([f"{v: 12.4e}" for v in vector[:6]]))
    lineas.append("    Nodo j:  " + " ".join([f"{v: 12.4e}" for v in vector[6:]]))
    return lineas

def _formatear_tabla_desplazamientos(modelo, desplazamientos_vector, nodos_a_mostrar=None):
    """Genera líneas de texto para la tabla de desplazamientos."""
    if desplazamientos_vector is None or desplazamientos_vector.size == 0:
        return ["    (No hay datos de desplazamientos disponibles)"]
        
    lineas = []
    lineas.append(f"  {'Nodo':<6}{'Ux (m)':>15}{'Uy (m)':>15}{'Uz (m)':>15}{'Rx (rad)':>15}{'Ry (rad)':>15}{'Rz (rad)':>15}")
    lineas.append("  " + "-" * 100)
    
    nodos_ids = sorted(nodos_a_mostrar) if nodos_a_mostrar else sorted(modelo.nodos.keys())
    
    for id_nodo in nodos_ids:
        idx = (id_nodo - 1) * 6
        if idx + 6 <= len(desplazamientos_vector):
            d = desplazamientos_vector[idx:idx+6]
            # Mostrar solo si algún valor es significativo
            if np.any(np.abs(d) > 1e-9):
                lineas.append(f"  {id_nodo:<6}{d[0]:>15.5e}{d[1]:>15.5e}{d[2]:>15.5e}{d[3]:>15.5e}{d[4]:>15.5e}{d[5]:>15.5e}")
    if len(lineas) <= 2: # Solo cabeceras
        lineas.append("    (Sin desplazamientos significativos)")
    return lineas

def _formatear_tabla_reacciones(modelo, reacciones_vector, apoyos_a_mostrar=None):
    """Genera líneas de texto para la tabla de reacciones."""
    if reacciones_vector is None or reacciones_vector.size == 0:
        return ["    (No hay datos de reacciones disponibles)"]

    lineas = []
    lineas.append(f"  {'Nodo':<6}{'Fx (kN)':>15}{'Fy (kN)':>15}{'Fz (kN)':>15}{'Mx (kN-m)':>15}{'My (kN-m)':>15}{'Mz (kN-m)':>15}")
    lineas.append("  " + "-" * 100)
    
    apoyos_ids = sorted(apoyos_a_mostrar) if apoyos_a_mostrar else sorted(modelo.apoyos.keys())

    for id_nodo in apoyos_ids:
        idx = (id_nodo - 1) * 6
        if idx + 6 <= len(reacciones_vector):
            r = reacciones_vector[idx:idx+6]
            # Mostrar solo si algún valor es significativo (y es un apoyo real)
            if id_nodo in modelo.apoyos and np.any(np.abs(r) > 1e-9):
                lineas.append(f"  {id_nodo:<6}{r[0]:>15.4f}{r[1]:>15.4f}{r[2]:>15.4f}{r[3]:>15.4f}{r[4]:>15.4f}{r[5]:>15.4f}")
    if len(lineas) <= 2: # Solo cabeceras
        lineas.append("    (Sin reacciones significativas)")
    return lineas
# --- Clase Principal del Generador ---

class GeneradorReporte:
    def __init__(self, modelo):
        self.modelo = modelo
        self.reporte = []
        self.generador_diagramas = GeneradorDiagramas(modelo) if GeneradorDiagramas else None

    def _limpiar_reporte(self):
        self.reporte = []

    def _agregar_titulo(self):
        self.reporte.append("=" * 70)
        self.reporte.append(" " * 20 + "MEMORIA DE CÁLCULO ESTRUCTURAL - VORTEX 3D")
        self.reporte.append("=" * 70)
        self.reporte.append(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.reporte.append(f"Archivo: {self.modelo.archivo_actual or 'Sin guardar'}")
        self.reporte.append("\n")

    def _generar_seccion_1_datos_entrada(self, config): 
        self.reporte.append("1. DATOS DE ENTRADA")
        self.reporte.append("-" * 70)
        self.reporte.append("1.1 Nodos:")
        self.reporte.append("  Nodo       X (m)        Y (m)        Z (m)")
        for id_nodo, (x, y, z) in sorted(self.modelo.nodos.items()):
            self.reporte.append(f"  {id_nodo:<5d}   {x: 10.3f}   {y: 10.3f}   {z: 10.3f}")
        self.reporte.append("\n")
        self.reporte.append("1.2 Materiales (Propiedades Calculadas):")
        self.reporte.append("  ID   Tipo          E (kPa)      G (kPa)      A (m²)       J (m⁴)       Iy (m⁴)      Iz (m⁴)      Avy (m²)      Avz (m²)   PE (kN/m³)")
        for id_mat, datos in sorted(self.modelo.materiales.items()):
            if datos.get('tipo', 'rectangular') != 'placa':
                try:
                    # Desempaquetamos las 8 propiedades
                    E, G, A, J, Iy, Iz, Ay, Az = self.modelo.get_propiedades_calculadas(id_mat)
                    # Obtenemos el PE
                    pe = datos.get('peso_especifico', 0.0)
                    # Imprimimos la fila completa
                    self.reporte.append(f"  {id_mat:<3d}  {datos['tipo']:<12s}  {E: 10.3e}   {G: 10.3e}   {A: 10.3e}   {J: 10.3e}   {Iy: 10.3e}   {Iz: 10.3e}   {Ay: 10.3e}   {Az: 10.3e}   {pe: 10.2f}")
                except Exception as e:
                    self.reporte.append(f"  {id_mat:<3d}  {datos['tipo']:<12s}  Error al calcular props: {e}")
        self.reporte.append("\n")

        self.reporte.append("1.3 Elementos (Pórtico):")
        self.reporte.append("  ID       Nodo i     Nodo j     Material   Longitud (m)")
        for id_elem, (ni, nj, mid) in sorted(self.modelo.elementos.items()):
            try:
                p1, p2 = self.modelo.nodos[ni], self.modelo.nodos[nj]
                longitud = np.linalg.norm(np.array(p2) - np.array(p1))
                self.reporte.append(f"  {id_elem:<8d} {ni:<10d} {nj:<10d} {mid:<10d} {longitud: 10.3f}")
            except Exception:
                self.reporte.append(f"  {id_elem:<8d} {ni:<10d} {nj:<10d} {mid:<10d} (Error en nodos)")
        self.reporte.append("\n")

        self.reporte.append("1.4 Losas (Definición):")
        self.reporte.append("  ID     Nodos                  Distribución     Eje Uni.   Espesor (m)  PE (kN/m³)")
        for id_losa, datos in sorted(self.modelo.losas.items()):
            nodos_str = ", ".join(map(str, datos['nodos']))
            eje_str = datos.get('eje_uni', 'N/A') or 'N/A'
            espesor_val = datos.get('espesor', 0.0)
            pe_val = datos.get('peso_especifico', 0.0)
            self.reporte.append(f"  {id_losa:<5d}  {nodos_str:<20s}   {datos['distribucion']:<15s}  {eje_str:<9s}  {espesor_val:^11.3f}  {pe_val:^11.2f}")
        self.reporte.append("\n")

        self.reporte.append("1.5 Apoyos (R=Restringido, L=Libre):")
        self.reporte.append("  Nodo     Tx    Ty    Tz    Rx    Ry    Rz")
        for id_nodo, restr in sorted(self.modelo.apoyos.items()):
            restr_str = " ".join([f"{'R':<5s}" if r else f"{'L':<5s}" for r in restr])
            self.reporte.append(f"  {id_nodo:<5d}   {restr_str}")
        self.reporte.append("\n")

        self.reporte.append("1.6 Hipótesis y Cargas Asignadas:")
        if not self.modelo.hipotesis_de_carga:
            self.reporte.append("  (No hay hipótesis definidas)")
        for id_hip, datos_hip in sorted(self.modelo.hipotesis_de_carga.items()):
            self.reporte.append(f"\n  Hipótesis {id_hip}: \"{datos_hip['nombre']}\" (Tipo: {datos_hip['tipo']})")

            cargas_nodales_hip = [c for c in self.modelo.cargas_nodales if c['id_hipotesis'] == id_hip]
            if cargas_nodales_hip:
                self.reporte.append("    Cargas Nodales:")
                for c in cargas_nodales_hip:
                    vec_str = ", ".join([f"{v:.2f}" for v in c['vector'] if abs(v) > 1e-9])
                    self.reporte.append(f"      - Nodo {c['id_nodo']}: [{vec_str}]")

            cargas_elem_hip = [c for c in self.modelo.cargas_elementos if c['id_hipotesis'] == id_hip]
            if cargas_elem_hip:
                self.reporte.append("    Cargas en Elementos:")
                for c in cargas_elem_hip:
                    datos_str = ", ".join([f"{v:.2f}" for v in c['datos_carga'][1:] if abs(v) > 1e-9])
                    self.reporte.append(f"      - Elem {c['id_elemento']} ({c['datos_carga'][0]}): [{datos_str}]")

            cargas_sup_hip = [cs for cs in self.modelo.cargas_superficiales.values() if cs['id_hipotesis'] == id_hip]
            if cargas_sup_hip:
                self.reporte.append("    Cargas Superficiales (Definición):")
                for c in cargas_sup_hip:
                    self.reporte.append(f"      - ID {c['id_carga']}: Losa {c['id_losa']} -> [wz: {c['magnitud']:.2f} kPa]")
        
        self.reporte.append("\n  1.7 Cargas de Peso Propio (1D Automáticas):")
        log_pp_1d = self.modelo.resultados_calculo.get('reporte_global_data', {}).get('log_pp_1d', [])
        if not log_pp_1d:
            self.reporte.append("    (No se calcularon Cargas PP 1D para este análisis)")
        else:
            for log_item in log_pp_1d:
                id_elem = log_item['id_elem']
                w_global_z = log_item['w_global_z']
                self.reporte.append(f"    - Elem {id_elem}: Carga Global Wz = {w_global_z:.3f} kN/m")

        self.reporte.append("\n")

    def _generar_seccion_2_losas(self, config):
        if not config.get('mostrar_proc_losas', True): return

        self.reporte.append("2. PROCESAMIENTO DE CARGAS DE LOSA")
        self.reporte.append("-" * 70)
        
        datos_losas = self.modelo.datos_reporte_losas
        if not datos_losas:
            self.reporte.append("  (No se registraron distribuciones de carga por losas para este cálculo)")
        else:
            for dato_losa in datos_losas:
                id_losa = dato_losa['id_losa']
                tipo = dato_losa['tipo'] 
                wz = dato_losa['wz']

                if 'unidireccional' in tipo:
                
                    self.reporte.append(f"[Losa {id_losa} - {tipo}]: Iniciando Distribución (wz = {wz:.2f} kPa)")
                    self.reporte.append(f"    Ancho total: {dato_losa['ancho_total']:.2f} m, Ancho por viga: {dato_losa['ancho_aporte']:.2f} m")
                    self.reporte.append(f"    Carga Lineal Eq: {wz:.2f} * {dato_losa['ancho_aporte']:.2f} = {dato_losa['w_lineal']:.5f} kN/m")
                    for viga_info in dato_losa['vigas_cargadas']:
                        self.reporte.append(f"    -> Asignando a Viga ID: {viga_info['id_viga']} (Long: {viga_info['longitud']:.2f} m)")
                    self.reporte.append(f"[Losa {id_losa} - {tipo}]: Fin de distribución.")

                elif 'bidireccional' in tipo:
                    self.reporte.append(f"[Losa {id_losa} - {tipo}]: Iniciando Distribución (wz = {wz:.3f} kPa)")
                    for viga_info in dato_losa['vigas_cargadas']:
                        self.reporte.append(f"    -> Procesando Viga ID: {viga_info['id_viga']} (Borde {viga_info['borde']})")
    
                        longitud_viga = viga_info['longitud']
                        datos_carga = viga_info['datos_carga']
                        
                        self.reporte.append(f"       - Long. Viga: {longitud_viga:.2f} m")

                        tipo_carga_aplicada = datos_carga[0]
                        if tipo_carga_aplicada == 'tramos_locales':
                            eje_local = datos_carga[1]
                            lista_puntos = datos_carga[2]
                            puntos_str = ", ".join([f"({p[0]:.5f}, {p[1]:.5f})" for p in lista_puntos])
                            
                            self.reporte.append(f"       - Carga Aplicada: {tipo_carga_aplicada} (Eje: {eje_local})")
                            self.reporte.append(f"       - Puntos (p_norm, q): {puntos_str}")
                        else:
                            self.reporte.append(f"       - Carga Aplicada (Datos Crudos): {datos_carga}")
                        
                    self.reporte.append(f"[Losa {id_losa} - {tipo}]: Fin de distribución.")

                self.reporte.append("-" * 30)

        self.reporte.append("\n")


    def _generar_seccion_3_ensamblaje(self, config):
        if not config.get('mostrar_analisis_mat', True): return

        self.reporte.append("3. ANÁLISIS MATRICIAL")
        self.reporte.append("-" * 70)
        
        reporte_global = self.modelo.resultados_calculo.get('reporte_global_data', {})
        if not reporte_global:
            self.reporte.append("  (No hay datos de ensamblaje disponibles.)")
            return

        datos_ensamblaje = reporte_global.get('ensamblaje', {})

        # Mostrar Logs (si está activado en avanzadas)
        if config.get('mostrar_logs_ensamblaje', False): 
            self.reporte.append("3.1 Logs de Ensamblaje:")
            log_ens = datos_ensamblaje.get('log_ensamblaje', [])
            if not log_ens: self.reporte.append("  (No se generaron logs)")
            else: self.reporte.extend([f"  {linea}" for linea in log_ens])
            self.reporte.append("\n")

        # Mostrar Matrices Locales/T (si está activado en avanzadas)
        if config.get('mostrar_matrices_locales', False):
             self.reporte.append("3.2 Matrices Locales y de Transformación por Elemento:")
             k_locales = datos_ensamblaje.get('k_locales', {})
             t_matrices = datos_ensamblaje.get('T_matrices', {})
             
             for id_elem in sorted(k_locales.keys()):
                 self.reporte.append(f"  --- ELEMENTO {id_elem} ---")
                 
                 # Matriz de Transformación
                 if id_elem in t_matrices: 
                     self.reporte.extend(_formatear_matriz(t_matrices[id_elem], f"Matriz de Transformación [T] E{id_elem}", max_dim=12))
                 
                 # Matriz de Rigidez Local
                 if id_elem in k_locales: 
                     self.reporte.extend(_formatear_matriz(k_locales[id_elem], f"Matriz de Rigidez Local [k] E{id_elem}", max_dim=12))
                 
                 self.reporte.append("-" * 40) # Separador visual por elemento
                 
             if not k_locales:
                 self.reporte.append("  (No hay matrices locales/T disponibles)")
             self.reporte.append("\n")
        
        # Mostrar K_global según configuración avanzada
        mostrar_kglobal_opt = config.get('mostrar_kglobal', 'diagonal') # Default 'diagonal'
        if mostrar_kglobal_opt != 'no':
            self.reporte.append("3.3 Matriz de Rigidez Global [K_global]:")
            K_global = datos_ensamblaje.get('K_global')
            if K_global is not None:
                if mostrar_kglobal_opt == 'completa':
                    self.reporte.extend(_formatear_matriz(K_global, "K_global (Completa)", max_dim=K_global.shape[0])) # Sin límite
                else: # Diagonal
                    self.reporte.extend(_formatear_matriz(K_global, "K_global (Resumen Diagonal)"))
            else:
                self.reporte.append("  (No se encontró la Matriz Global)")
            self.reporte.append("\n")


    def _generar_seccion_4_resolucion(self, config):
        if not config.get('mostrar_resolucion', True): return
        
        self.reporte.append("4. RESOLUCIÓN POR COMBINACIÓN DE CARGA")
        self.reporte.append("=" * 70)

        casos_seleccionados = config.get('casos_seleccionados', [])
        if not casos_seleccionados:
            self.reporte.append("  (No se seleccionaron combinaciones/casos para mostrar)")
            return

        # Agrupar casos por combinación principal para el reporte
        casos_por_combo = defaultdict(list)
        for nombre_combo, nombre_sub_caso in casos_seleccionados:
            casos_por_combo[nombre_combo].append(nombre_sub_caso)

        for i, nombre_combo in enumerate(sorted(casos_por_combo.keys())):
            self.reporte.append(f"\n4.{i+1} Combinación: \"{nombre_combo}\"")
            self.reporte.append("-" * 70)
            
            sub_casos_nombres = sorted(casos_por_combo[nombre_combo])
            for nombre_sub_caso in sub_casos_nombres:
                resultados = self.modelo.resultados_calculo.get(nombre_combo, {}).get(nombre_sub_caso)
                if not resultados: continue # Seguridad

                self.reporte.append(f"  Caso: \"{nombre_sub_caso}\"")
                reporte_resolucion = resultados.get('reporte_resolucion', {})
                
                # --- Sistema Reducido (según config avanzada) ---
                if config.get('mostrar_k_reducida_completa', False):
                    self.reporte.append("\n  4.x.1 Sistema de Ecuaciones (Reducido - Completo):")
                    gdl_libres = reporte_resolucion.get('gdl_libres', [])
                    self.reporte.append(f"    GDL Libres ({len(gdl_libres)}): {[g+1 for g in gdl_libres]}")
                    self.reporte.extend(_formatear_matriz(reporte_resolucion.get('K_reducida'), "K_reducida", gdl_libres=gdl_libres, max_dim=len(gdl_libres)))
                    self.reporte.extend(_formatear_vector(reporte_resolucion.get('F_reducido'), "F_reducido", gdl_libres=gdl_libres))
                else: # Mostrar solo info básica (default)
                    self.reporte.append("\n  4.x.1 Sistema de Ecuaciones (Reducido - Resumen):")
                    gdl_libres = reporte_resolucion.get('gdl_libres', [])
                    k_reducida = reporte_resolucion.get('K_reducida')
                    dim = k_reducida.shape[0] if k_reducida is not None else 0
                    cond = reporte_resolucion.get('cond_K_reducida', 0.0)
                    self.reporte.append(f"    GDL Libres: {len(gdl_libres)}")
                    self.reporte.append(f"    Dimensiones K_reducida: {dim}x{dim}")
                    self.reporte.append(f"    Número de Condición K_reducida: {cond:.3e}")
                
                # --- Resultados (Desplazamientos y Reacciones) ---
                self.reporte.append("\n  4.x.2 Resultados:")
                if config.get('mostrar_vectores_desplazamiento', False):
                     self.reporte.extend(_formatear_vector(resultados.get('desplazamientos'), "Vector Desplazamientos [U] (m, rad)"))
                else: # Mostrar tabla formateada (default)
                    self.reporte.append("    Desplazamientos Nodales Globales:")
                    self.reporte.extend(_formatear_tabla_desplazamientos(self.modelo, resultados.get('desplazamientos')))

                if config.get('mostrar_vectores_reacciones', False):
                     self.reporte.extend(_formatear_vector(resultados.get('reacciones'), "Vector Reacciones [R] (kN, kN-m)"))
                else: # Mostrar tabla formateada (default)
                    self.reporte.append("\n    Reacciones en Apoyos Globales:")
                    self.reporte.extend(_formatear_tabla_reacciones(self.modelo, resultados.get('reacciones')))
                
                self.reporte.append("\n" + "-" * 50 + "\n") # Separador entre casos


    def _generar_seccion_5_fuerzas_internas(self, config):
        if not config.get('mostrar_fuerzas_int', True): return

        self.reporte.append("5. FUERZAS INTERNAS POR ELEMENTO (LOCALES)")
        self.reporte.append("=" * 70)

        casos_seleccionados = config.get('casos_seleccionados', [])
        if not casos_seleccionados or not self.generador_diagramas:
            self.reporte.append("  (No se seleccionaron casos o generador de diagramas no disponible)")
            return

        # --- Lógica Default: Envolventes por Elemento ---
        if not config.get('mostrar_detalle_fuerzas_todas', False):
            self.reporte.append("  Modo: Envolvente por elemento para casos seleccionados")
            
            # 1. Agrupar resultados por elemento
            resultados_por_elem = defaultdict(lambda: {'Px': [], 'Py': [], 'Pz': [], 'Mx': [], 'My': [], 'Mz': []})
            efectos = ['Axial (Px)', 'Cortante (Py)', 'Cortante (Pz)', 'Torsión (Mx)', 'Momento (My)', 'Momento (Mz)']
            
            for id_elem in sorted(self.modelo.elementos.keys()):
                 for nombre_combo, nombre_sub_caso in casos_seleccionados:
                     resultados = self.modelo.resultados_calculo.get(nombre_combo, {}).get(nombre_sub_caso)
                     if not resultados: continue
                     
                     for i, efecto_nombre in enumerate(efectos):
                         tipo_corto = efecto_nombre.split(' ')[-1][1:-1] # Extrae Px, Py, etc.
                         x, y = self.generador_diagramas.get_diagrama(id_elem, resultados, efecto_nombre)
                         if y.size > 0:
                             resultados_por_elem[id_elem][tipo_corto].append({
                                 'caso': f"{nombre_combo}/{nombre_sub_caso}",
                                 'y_data': y,
                                 'max_pos': np.max(y) if np.any(y > 1e-9) else 0.0,
                                 'max_neg': np.min(y) if np.any(y < -1e-9) else 0.0,
                             })

            # 2. Formatear reporte por elemento
            for id_elem, datos_efectos in sorted(resultados_por_elem.items()):
                self.reporte.append(f"\n  --- Elemento {id_elem} ---")
                self.reporte.append(f"    {'Efecto':<7} {'Máx Pos (+)':>15} {'(Caso)':<30} {'Máx Neg (-)':>15} {'(Caso)':<30}")
                self.reporte.append("    " + "-" * 95)
                
                for tipo_corto in ['Px', 'Py', 'Pz', 'Mx', 'My', 'Mz']:
                    lista_resultados = datos_efectos.get(tipo_corto, [])
                    if not lista_resultados: continue

                    max_pos_global = -np.inf
                    caso_max_pos = "N/A"
                    max_neg_global = np.inf
                    caso_max_neg = "N/A"

                    for res in lista_resultados:
                        if res['max_pos'] > max_pos_global:
                            max_pos_global = res['max_pos']
                            caso_max_pos = res['caso']
                        if res['max_neg'] < max_neg_global:
                            max_neg_global = res['max_neg']
                            caso_max_neg = res['caso']
                            
                    # Ajustar si no hay positivos o negativos
                    if max_pos_global == -np.inf: max_pos_global = 0.0
                    if max_neg_global == np.inf: max_neg_global = 0.0

                    # Truncar nombres de casos si son muy largos
                    caso_max_pos = caso_max_pos[:28] + ".." if len(caso_max_pos) > 30 else caso_max_pos
                    caso_max_neg = caso_max_neg[:28] + ".." if len(caso_max_neg) > 30 else caso_max_neg
                    
                    self.reporte.append(f"    {tipo_corto:<7} {max_pos_global:>15.4f} {caso_max_pos:<30} {max_neg_global:>15.4f} {caso_max_neg:<30}")
                    
        # --- Lógica Avanzada: Detalle por Caso ---
        else:
            self.reporte.append("  Modo: Detalle de fuerzas nodales por caso seleccionado")
            
            for nombre_combo, nombre_sub_caso in sorted(casos_seleccionados):
                 resultados = self.modelo.resultados_calculo.get(nombre_combo, {}).get(nombre_sub_caso)
                 if not resultados: continue

                 self.reporte.append(f"\n  Caso: \"{nombre_combo} / {nombre_sub_caso}\"")
                 fuerzas_internas_dict = resultados.get('fuerzas_internas', {})
                
                 if not fuerzas_internas_dict:
                     self.reporte.append("    (Sin fuerzas internas calculadas para este caso)")
                     continue
                
                 for id_elem in sorted(self.modelo.elementos.keys()): 
                     f_int_vec = fuerzas_internas_dict.get(id_elem) 
                     if f_int_vec is not None:
                         self.reporte.append(f"    Elemento {id_elem}:")
                         self.reporte.extend(_formatear_vector_fuerzas_internas(f_int_vec))
                 self.reporte.append("-" * 40)
        
        self.reporte.append("\n")


    def _generar_seccion_6_resumen(self, config):
        if not config.get('mostrar_resumen_max', True): return
        
        self.reporte.append("6. RESUMEN DE MÁXIMOS GLOBALES (ENVOLVENTE REAL)")
        self.reporte.append("=" * 70)

        casos_seleccionados = config.get('casos_seleccionados', [])
        if not casos_seleccionados or not self.generador_diagramas:
            self.reporte.append("  (No se seleccionaron casos o generador de diagramas no disponible)")
            return

        maximos = {
            'Px': {'max+': (-np.inf, "", ""), 'max-': (np.inf, "", "")},
            'Py': {'max+': (-np.inf, "", ""), 'max-': (np.inf, "", "")},
            'Pz': {'max+': (-np.inf, "", ""), 'max-': (np.inf, "", "")},
            'Mx': {'max+': (-np.inf, "", ""), 'max-': (np.inf, "", "")},
            'My': {'max+': (-np.inf, "", ""), 'max-': (np.inf, "", "")},
            'Mz': {'max+': (-np.inf, "", ""), 'max-': (np.inf, "", "")},
        }
        efectos_map = { 
            'Axial (Px)': 'Px', 'Cortante (Py)': 'Py', 'Cortante (Pz)': 'Pz',
            'Torsión (Mx)': 'Mx', 'Momento (My)': 'My', 'Momento (Mz)': 'Mz'
        }

        for id_elem in self.modelo.elementos.keys():
            for nombre_combo, nombre_sub_caso in casos_seleccionados:
                resultados = self.modelo.resultados_calculo.get(nombre_combo, {}).get(nombre_sub_caso)
                if not resultados: continue
                caso_str = f"{nombre_combo}/{nombre_sub_caso}"
                
                for efecto_largo, tipo_corto in efectos_map.items():
                    x, y = self.generador_diagramas.get_diagrama(id_elem, resultados, efecto_largo)
                    if y.size > 0:
                        max_y = np.max(y)
                        min_y = np.min(y)
                        
                        if max_y > maximos[tipo_corto]['max+'][0]:
                            maximos[tipo_corto]['max+'] = (max_y, f"Elem {id_elem}", caso_str)
                        if min_y < maximos[tipo_corto]['max-'][0]:
                            maximos[tipo_corto]['max-'] = (min_y, f"Elem {id_elem}", caso_str)

        self.reporte.append("  Efecto   Valor Máx (+)       Elemento      Caso                                 Valor Máx (-)       Elemento      Caso")
        self.reporte.append("  " + "-" * 120)
        for tipo_corto in ['Px', 'Py', 'Pz', 'Mx', 'My', 'Mz']:
            max_pos_val, max_pos_elem, max_pos_caso = maximos[tipo_corto]['max+']
            max_neg_val, max_neg_elem, max_neg_caso = maximos[tipo_corto]['max-']

            # Formatear valores (cero si no se encontraron)
            max_pos_val_str = f"{max_pos_val:15.4f}" if max_pos_val > -np.inf else f"{0.0:15.4f}"
            max_neg_val_str = f"{max_neg_val:15.4f}" if max_neg_val < np.inf else f"{0.0:15.4f}"
            max_pos_elem = max_pos_elem if max_pos_val > -np.inf else "N/A"
            max_neg_elem = max_neg_elem if max_neg_val < np.inf else "N/A"
            max_pos_caso = max_pos_caso[:33] + ".." if len(max_pos_caso) > 35 else max_pos_caso
            max_neg_caso = max_neg_caso[:33] + ".." if len(max_neg_caso) > 35 else max_neg_caso
            
            self.reporte.append(f"  {tipo_corto:<7} {max_pos_val_str} {max_pos_elem:<13} {max_pos_caso:<35} {max_neg_val_str} {max_neg_elem:<13} {max_neg_caso:<35}")
            
        self.reporte.append("\n")


    # --- MÉTODO PRINCIPAL ---
    def generar_reporte_personalizado(self, config):
        """
        Genera el reporte completo basado en el diccionario de configuración.
        """
        self._limpiar_reporte()
        
        try:
            self._agregar_titulo()
            
            # Llamar a cada sección pasando la configuración
            self._generar_seccion_1_datos_entrada(config)
            self._generar_seccion_2_losas(config)
            self._generar_seccion_3_ensamblaje(config)
            self._generar_seccion_4_resolucion(config)
            self._generar_seccion_5_fuerzas_internas(config)
            self._generar_seccion_6_resumen(config)
            
            self.reporte.append("=" * 70)
            self.reporte.append(" " * 27 + "FIN DEL REPORTE")
            self.reporte.append("=" * 70)

        except Exception as e:
            self._limpiar_reporte()
            self.reporte.append("=" * 70); self.reporte.append("ERROR AL GENERAR EL REPORTE"); self.reporte.append("=" * 70)
            self.reporte.append(f"Detalle del error: {e}")
            import traceback
            self.reporte.append(traceback.format_exc())

        return "\n".join(self.reporte)