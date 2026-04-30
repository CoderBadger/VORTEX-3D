"""
Módulo: modelo_estructura.py
Descripción: Base de datos central del programa. Define las clases y estructuras 
de datos para nodos, elementos 1D (vigas y columnas), materiales, secciones y 
apoyos necesarios para el Método Matricial de Rigidez.
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
import json
import numpy as np
import math
from typing import Optional
from procesador_cargas import CombinacionCarga, ProcesadorCargas

#=======================================================================
# II. ESTRUCTURA DE DATOS PRINCIPAL DEL MODELO MATEMÁTICO
#=======================================================================
class Estructura:
    """Encapsula todos los datos y operaciones de la estructura."""
    def __init__(self):
        # 1. Inyección de dependencias para el motor de procesamiento de cargas
        from procesador_cargas import ProcesadorCargas
        self.procesador_cargas = ProcesadorCargas(self)
        self.reiniciar()

    def reiniciar(self):
        """Restablece todos los datos a un estado vacío."""
        self.nodos = {}
        self.elementos = {}
        self.materiales = {}
        self.apoyos = {}
        self.losas = {} 
        self.hipotesis_de_carga = {} 
        self.cargas_nodales = []   
        self.cargas_elementos = []
        self.cargas_superficiales = {}   
        self.siguiente_id_carga = 1
        self.siguiente_id_carga_sup = 1
        self.combinaciones = ProcesadorCargas(self).combinaciones_norma.copy()
        self.combinaciones_usuario = []
        self.archivo_actual = None
        self.modificado = False
        self.desplazamientos = None
        self.reacciones = None
        self.fuerzas_internas = None
        self.rigidez_global = None
        self.armados_diseno = {}
        self.resultados_calculo = None
        self.datos_reporte_losas = []

    def get_centro_geometrico(self):
        """Calcula el centro del cuadro delimitador de todos los nodos."""
        if not self.nodos:
            return np.array([0.0, 0.0, 0.0])
        
        coords = np.array(list(self.nodos.values()))
        min_coords = coords.min(axis=0)
        max_coords = coords.max(axis=0)
        return (min_coords + max_coords) / 2.0

    def get_siguiente_id(self, coleccion):
        """Obtiene el siguiente ID disponible en una colección (diccionario)."""
        if not coleccion:
            return 1
        return max(coleccion.keys()) + 1
    
#=======================================================================
# III. GESTIÓN TOPOLÓGICA: NODOS Y ELEMENTOS UNIDIMENSIONALES
#=======================================================================
    def agregar_nodo(self, id_nodo, coords):
        if id_nodo in self.nodos:
            raise ValueError(f"El ID de nodo {id_nodo} ya existe.")
        self.nodos[id_nodo] = coords
        self.modificado = True

    def actualizar_nodo(self, id_nodo, coords):
        if id_nodo not in self.nodos:
            raise ValueError(f"El nodo {id_nodo} no existe.")
        self.nodos[id_nodo] = coords
        self.modificado = True

    def eliminar_nodo(self, id_nodo):
        if id_nodo not in self.nodos:
            return
        del self.nodos[id_nodo]
        
        # 1. Eliminación en cascada de elementos y propiedades dependientes
        elementos_a_eliminar = [eid for eid, (ni, nj, _) in self.elementos.items() if ni == id_nodo or nj == id_nodo]
        for eid in elementos_a_eliminar:
            self.eliminar_elemento(eid)
        
        if id_nodo in self.apoyos: del self.apoyos[id_nodo]
        if id_nodo in self.cargas_nodales: del self.cargas_nodales[id_nodo]
        self.modificado = True

    def agregar_elemento(self, id_elemento, ni, nj, id_material):
        if id_elemento in self.elementos:
            raise ValueError(f"El ID de elemento {id_elemento} ya existe.")
        if ni not in self.nodos or nj not in self.nodos:
            raise ValueError("Uno o ambos nodos del elemento no existen.")
        if id_material not in self.materiales:
            raise ValueError("El material del elemento no existe.")
        if ni == nj:
            raise ValueError("Los nodos de inicio y fin no pueden ser iguales.")
        self.elementos[id_elemento] = (ni, nj, id_material)
        self.modificado = True
        
    def actualizar_elemento(self, id_elemento, ni, nj, id_material):
        if id_elemento not in self.elementos: return
        if ni not in self.nodos or nj not in self.nodos: raise ValueError("Nodos no válidos.")
        if id_material not in self.materiales: raise ValueError("Material no válido.")
        self.elementos[id_elemento] = (ni, nj, id_material)
        self.modificado = True

    def eliminar_elemento(self, id_elemento):
        if id_elemento not in self.elementos: return
        del self.elementos[id_elemento]
        if id_elemento in self.cargas_elementos: del self.cargas_elementos[id_elemento]
        self.modificado = True

    def actualizar_material_de_elementos(self, ids_elementos: list, id_material_nuevo: int):
        """
        Actualiza el material de una lista de elementos 1D (pórticos) de forma masiva.
        Verifica que el material sea compatible (no de placa).
        
        Args:
            ids_elementos (list): Lista de IDs de elementos a modificar.
            id_material_nuevo (int): ID del nuevo material a asignar.
            
        Returns:
            int: Cantidad de elementos que fueron exitosamente actualizados.
            
        Raises:
            ValueError: Si el material no existe.
        """
        
        # 1. Validar el material nuevo
        if id_material_nuevo not in self.materiales:
            raise ValueError(f"Error: El material ID {id_material_nuevo} no existe.")

        # 2. Iterar y actualizar
        ids_no_encontrados = []
        count_actualizados = 0
        
        for id_elem in ids_elementos:
            if id_elem in self.elementos:
                datos_actuales = self.elementos[id_elem]
                self.elementos[id_elem] = (datos_actuales[0], datos_actuales[1], id_material_nuevo)
                
                count_actualizados += 1
            else:
                ids_no_encontrados.append(id_elem)
        
        # 3. Marcar como modificado y reportar
        if count_actualizados > 0:
            self.modificado = True
        
        if ids_no_encontrados:
            print(f"ADVERTENCIA (actualizar_material_de_elementos): No se encontraron los elementos IDs: {ids_no_encontrados}")
        
        return count_actualizados

#=======================================================================
# IV. GESTIÓN DE ELEMENTOS BIDIMENSIONALES: LOSAS
#=======================================================================
    def _ordenar_nodos_placa(self, nodos_ids):
        """
        Garantiza el ordenamiento secuencial (perimetral) de los nodos 
        pertenecientes a un elemento superficial para evitar auto-intersecciones.
        """
        if len(nodos_ids) != 4:
            return nodos_ids 

        coords = np.array([self.nodos[nid] for nid in nodos_ids])
        
        centro = np.mean(coords, axis=0)
        
        # 1. Determinación del vector normal predominante
        v1 = coords[1] - coords[0]
        v2 = coords[2] - coords[0]
        normal = np.cross(v1, v2)
        
        # 2. Proyección sobre el plano principal para cálculo de ángulos polares
        if abs(normal[2]) > abs(normal[0]) and abs(normal[2]) > abs(normal[1]): 
            idx1, idx2 = 0, 1
        elif abs(normal[1]) > abs(normal[0]): 
            idx1, idx2 = 0, 2
        else: 
            idx1, idx2 = 1, 2

        angulos = [math.atan2(p[idx2] - centro[idx2], p[idx1] - centro[idx1]) for p in coords]
            
        nodos_ids_ordenados = [nid for _, nid in sorted(zip(angulos, nodos_ids))]
        return nodos_ids_ordenados

    def agregar_losa(self, id_losa, nodos_ids, distribucion, eje_uni=None, espesor=0.20, peso_especifico=24.0):
        """
        Registra un elemento bidimensional en la base de datos, validando 
        previamente la coplanaridad matemática de sus vértices.
        """
        if id_losa in self.losas:
            raise ValueError(f"El ID de losa {id_losa} ya existe.")
        if len(nodos_ids) != 4:
            raise ValueError("Una losa debe tener exactamente 4 nodos.")
        for nid in nodos_ids:
            if nid not in self.nodos:
                raise ValueError(f"El nodo {nid} no existe.")
            
            # 1. Verificación de coplanaridad mediante Descomposición en Valores Singulares (SVD)
            tolerancia_coplanar = 0.01
            coords = np.array([self.nodos[nid] for nid in nodos_ids])
            coords_centradas = coords - coords.mean(axis=0)

            _, valores_singulares, vh = np.linalg.svd(coords_centradas)
            
            normal_plano = vh[2, :]
            distancias_al_plano = np.abs(np.dot(coords_centradas, normal_plano))
            
            if np.max(distancias_al_plano) > tolerancia_coplanar:
                raise ValueError(f"Los nodos de la losa {id_losa} no son coplanares (desviación máxima > {tolerancia_coplanar} m).")

        nodos_ordenados = self._ordenar_nodos_placa(nodos_ids)

        self.losas[id_losa] = {
            'nodos': nodos_ordenados,
            'distribucion': distribucion, 
            'eje_uni': eje_uni,          
            'espesor': espesor,
            'peso_especifico': peso_especifico
        }
        self.modificado = True


    def actualizar_losa(self, id_losa, nodos_ids, distribucion, eje_uni=None, espesor=0.20, peso_especifico=24.0):
        if id_losa not in self.losas:
            raise ValueError(f"La losa {id_losa} no existe.")
        if len(nodos_ids) != 4:
            raise ValueError("Una losa debe tener exactamente 4 nodos.")
        for nid in nodos_ids:
            if nid not in self.nodos:
                raise ValueError(f"El nodo {nid} no existe.")
            
            tolerancia_coplanar = 0.01
            coords = np.array([self.nodos[nid] for nid in nodos_ids])
            coords_centradas = coords - coords.mean(axis=0)
            _, _, vh = np.linalg.svd(coords_centradas)
            normal_plano = vh[2, :]
            distancias_al_plano = np.abs(np.dot(coords_centradas, normal_plano))
    
            if np.max(distancias_al_plano) > tolerancia_coplanar:
                raise ValueError(f"Los nodos de la losa {id_losa} no son coplanares (desviación máxima > {tolerancia_coplanar} m).")

        nodos_ordenados = self._ordenar_nodos_placa(nodos_ids)

        self.losas[id_losa]['nodos'] = nodos_ordenados
        self.losas[id_losa]['distribucion'] = distribucion
        self.losas[id_losa]['eje_uni'] = eje_uni
        self.losas[id_losa]['espesor'] = espesor
        self.losas[id_losa]['peso_especifico'] = peso_especifico
        self.modificado = True

    def eliminar_losa(self, id_losa):
        if id_losa in self.losas:
            del self.losas[id_losa]
            self.modificado = True

    def actualizar_propiedades_losas_lote(self, 
                                          ids_losas: list, 
                                          distribucion: Optional[str] = None, 
                                          eje_uni: Optional[str] = None, 
                                          espesor: Optional[float] = None, 
                                          peso_especifico: Optional[float] = None) -> int:
        """
        Actualiza propiedades seleccionadas (distribución, espesor, PE) 
        de una lista de losas de forma masiva.
        Las propiedades enviadas como None no se modificarán.
        
        Args:
            ids_losas (list): Lista de IDs de losas a modificar.
            distribucion (str, optional): 'bidireccional' o 'unidireccional'.
            eje_uni (str, optional): 'Global X' o 'Global Y'.
            espesor (float, optional): Nuevo valor de espesor.
            peso_especifico (float, optional): Nuevo valor de PE.
            
        Returns:
            int: Cantidad de losas que fueron exitosamente actualizadas.
        """
        # 1. Validación de consistencia de los parámetros de entrada
        if distribucion is not None:
            if distribucion == 'unidireccional' and eje_uni not in ['Global X', 'Global Y']:
                raise ValueError("El eje de distribución debe ser 'Global X' o 'Global Y' para el tipo unidireccional.")
            if distribucion == 'bidireccional' and eje_uni is not None:
                 raise ValueError("No se puede especificar un eje para el tipo bidireccional.")
        
        if espesor is not None and espesor <= 0:
            raise ValueError("El espesor debe ser un valor positivo.")
            
        if peso_especifico is not None and peso_especifico < 0:
             raise ValueError("El peso específico no puede ser negativo.")

        count_actualizados = 0

        # 2. Iteración y actualización de parámetros        
        for id_losa in ids_losas:
            if id_losa in self.losas:
                if distribucion is not None:
                    self.losas[id_losa]['distribucion'] = distribucion
                    self.losas[id_losa]['eje_uni'] = eje_uni 
                
                if espesor is not None:
                    self.losas[id_losa]['espesor'] = espesor
                
                if peso_especifico is not None:
                    self.losas[id_losa]['peso_especifico'] = peso_especifico
                
                count_actualizados += 1
        
        if count_actualizados > 0:
            self.modificado = True
        
        return count_actualizados

#=======================================================================
# V. GESTIÓN DE MATERIALES Y PROPIEDADES MECÁNICAS
#=======================================================================
    def agregar_material(self, id_mat, descripcion, tipo_seccion, props, peso_especifico=0.0):
        if id_mat in self.materiales:
            raise ValueError(f"El material con ID {id_mat} ya existe.")
        
        if tipo_seccion == 'general':
            if len(props) != 8:
                raise ValueError("Las propiedades para 'general' deben ser 8 valores positivos (E, G, A, J, Iy, Iz, Ay, Az).")
            
        elif not all(p > 0 for p in props if p is not None):
             raise ValueError("Las propiedades deben ser valores positivos.")

        self.materiales[id_mat] = {
            'tipo': tipo_seccion, 
            'descripcion': descripcion, 
            'propiedades': props,
            'peso_especifico': peso_especifico
        }
        self.modificado = True

    def actualizar_material(self, id_mat, descripcion, tipo_seccion, props, peso_especifico=0.0):
        if id_mat not in self.materiales:
            raise ValueError(f"El material con ID {id_mat} no existe.")

        if tipo_seccion == 'general':
            if len(props) != 8:
                raise ValueError("Las propiedades para 'general' deben ser 8 valores positivos (E, G, A, J, Iy, Iz, Ay, Az).")
            
        elif not all(p > 0 for p in props if p is not None):
             raise ValueError("Las propiedades deben ser valores positivos.")
           
        self.materiales[id_mat] = {
            'tipo': tipo_seccion, 
            'descripcion': descripcion, 
            'propiedades': props,
            'peso_especifico': peso_especifico
        }
        self.modificado = True
        
    def get_propiedades_calculadas(self, id_mat):
        """
        Extrae y computa las constantes mecánicas y geométricas de la sección 
        transversal para su integración en la matriz de rigidez [Hibbeler, 2017].
        """
        if id_mat not in self.materiales:
            raise ValueError(f"Material inexistente ID {id_mat}.")

        material = self.materiales[id_mat]
        tipo = material.get('tipo', 'rectangular')

        print(f"--- Obteniendo propiedades para Material ID: {id_mat} (Tipo: {tipo}) ---")

        # 1. Determinación de inercias y módulos para secciones rectangulares estándar
        if tipo == 'rectangular':
            E, nu, b, h, *_ = material['propiedades']
            G = E / (2 * (1 + nu))
            A = b * h
            Iy = (b * (h**3)) / 12
            Iz = (h * (b**3)) / 12
            a, B = (h, b) if h > b else (b, h)
            J = a * (B**3) * (1/3 - 0.21 * (B/a) * (1 - (B**4) / (12 * a**4)))
            Ay = 5/6 * A
            Az = Ay
            print("================ MATERIAL TIPO RECTANGULAR ================")
            print(f"G={G:.8e}; E={E:.8e}    b={b}, h={h} -> Iy={Iy:.8e}, Iz={Iz:.8e}, A={A:.8e}, J={J:.8e}, Ay={Ay:.8e}, Az={Az:.8e}")
            print("============================================================")
            return (E, G, A, J, Iy, Iz, Ay, Az)
        
        # 2. Extracción de propiedades explícitas para perfiles generales
        elif tipo == 'general':
            props = material['propiedades']
            if len(props) != 8:
                print(f"    ADVERTENCIA: El material 'general' ID {id_mat} tiene 6 propiedades. Se asumirá Ay=Az=A.")
                E, G, A, J, Iy, Iz = props
                Ay, Az = A, A
                return (E, G, A, J, Iy, Iz, Ay, Az)
            print("================ MATERIAL TIPO GENERAL ====================")
            print(f"    Propiedades generales (8): {props}")
            print("============================================================")
            return material['propiedades']
        
        else:
            raise TypeError(f"Tipo de material desconocido: {tipo}")

    def eliminar_material(self, id_material):
        if id_material not in self.materiales: return
        del self.materiales[id_material]
        elementos_a_eliminar = [eid for eid, (_, _, mid) in self.elementos.items() if mid == id_material]
        for eid in elementos_a_eliminar:
            self.eliminar_elemento(eid)
        self.modificado = True

#=======================================================================
# VI. CONDICIONES DE CONTORNO Y ESTADOS DE CARGA
#=======================================================================
    def agregar_o_actualizar_apoyo(self, id_nodo, restricciones):
        if id_nodo not in self.nodos:
            raise ValueError(f"El nodo {id_nodo} no existe.")
        self.apoyos[id_nodo] = restricciones
        self.modificado = True

    def eliminar_apoyo(self, id_nodo):
        if id_nodo in self.apoyos:
            del self.apoyos[id_nodo]
            self.modificado = True

    def agregar_hipotesis(self, nombre, tipo):
        if any(h['nombre'] == nombre for h in self.hipotesis_de_carga.values()):
            raise ValueError(f"Ya existe una hipótesis con el nombre '{nombre}'.")
        
        nuevo_id = self.get_siguiente_id(self.hipotesis_de_carga)
        self.hipotesis_de_carga[nuevo_id] = {'nombre': nombre, 'tipo': tipo}
        self.modificado = True
        return nuevo_id

    def eliminar_hipotesis(self, id_hipotesis):
        if id_hipotesis not in self.hipotesis_de_carga:
            return
            
        del self.hipotesis_de_carga[id_hipotesis]
        
        self.cargas_nodales = [c for c in self.cargas_nodales if c['id_hipotesis'] != id_hipotesis]
        self.cargas_elementos = [c for c in self.cargas_elementos if c['id_hipotesis'] != id_hipotesis]
        
        self.modificado = True

    def actualizar_hipotesis(self, id_hipotesis, nuevo_nombre, nuevo_tipo):
        if id_hipotesis not in self.hipotesis_de_carga:
            raise ValueError(f"La hipótesis con ID {id_hipotesis} no existe.")
            
        if any(h['nombre'] == nuevo_nombre for id_h, h in self.hipotesis_de_carga.items() if id_h != id_hipotesis):
            raise ValueError(f"El nombre '{nuevo_nombre}' ya está en uso por otra hipótesis.")

        self.hipotesis_de_carga[id_hipotesis]['nombre'] = nuevo_nombre
        self.hipotesis_de_carga[id_hipotesis]['tipo'] = nuevo_tipo
        self.modificado = True

    def agregar_carga_nodal(self, id_nodo, id_hipotesis, vector_carga):
        if id_nodo not in self.nodos:
            raise ValueError(f"El nodo {id_nodo} no existe.")
        if id_hipotesis not in self.hipotesis_de_carga:
            raise ValueError(f"La hipótesis de carga con ID {id_hipotesis} no existe.")
        
        nueva_carga = {
            'id_carga': self.siguiente_id_carga,
            'id_nodo': id_nodo,
            'id_hipotesis': id_hipotesis,
            'vector': vector_carga
        }
        self.cargas_nodales.append(nueva_carga)
        self.siguiente_id_carga += 1
        self.modificado = True
        
    def agregar_carga_elemento(self, id_elemento, id_hipotesis, datos_carga):
        if id_elemento not in self.elementos:
            raise ValueError(f"El elemento {id_elemento} no existe.")
        if id_hipotesis not in self.hipotesis_de_carga:
            raise ValueError(f"La hipótesis de carga con ID {id_hipotesis} no existe.")
            
        nueva_carga = {
            'id_carga': self.siguiente_id_carga,
            'id_elemento': id_elemento,
            'id_hipotesis': id_hipotesis,
            'datos_carga': datos_carga 
        }
        self.cargas_elementos.append(nueva_carga)
        self.siguiente_id_carga += 1
        self.modificado = True

    def eliminar_carga(self, id_carga):
        """Elimina una carga individual (nodal o de elemento) por su ID único."""
        len_inicial = len(self.cargas_nodales) + len(self.cargas_elementos)
        
        self.cargas_nodales = [c for c in self.cargas_nodales if c.get('id_carga') != id_carga]
        self.cargas_elementos = [c for c in self.cargas_elementos if c.get('id_carga') != id_carga]

        len_final = len(self.cargas_nodales) + len(self.cargas_elementos)
        
        if len_final < len_inicial:
            self.modificado = True

    def agregar_o_actualizar_carga_superficial(self, id_carga_sup, id_losa, id_hipotesis, magnitud_wz):
        """Agrega o actualiza una carga superficial definida sobre una losa."""
        if id_losa not in self.losas:
            raise ValueError(f"La losa con ID {id_losa} no existe.")
        if id_hipotesis not in self.hipotesis_de_carga:
            raise ValueError(f"La hipótesis de carga con ID {id_hipotesis} no existe.")

        if id_carga_sup is None or id_carga_sup not in self.cargas_superficiales:
            nuevo_id = self.get_siguiente_id(self.cargas_superficiales)
            self.cargas_superficiales[nuevo_id] = {
                'id_carga': nuevo_id,
                'id_losa': id_losa,
                'id_hipotesis': id_hipotesis,
                'magnitud': magnitud_wz
            }
            self.modificado = True
            return nuevo_id
        else:
            self.cargas_superficiales[id_carga_sup]['id_losa'] = id_losa
            self.cargas_superficiales[id_carga_sup]['id_hipotesis'] = id_hipotesis
            self.cargas_superficiales[id_carga_sup]['magnitud'] = magnitud_wz
            self.modificado = True
            return id_carga_sup

    def eliminar_carga_superficial(self, id_carga_sup):
        """Elimina una carga superficial por su ID."""
        if id_carga_sup in self.cargas_superficiales:
            del self.cargas_superficiales[id_carga_sup]
            self.modificado = True

#=======================================================================
# VII. PERSISTENCIA DE DATOS Y SERIALIZACIÓN
#=======================================================================
    def cargar_desde_archivo(self, ruta_archivo):
        """
        Deserializa el estado estructural desde un archivo JSON, reconstruyendo 
        el modelo en memoria RAM [Sommerville, 2011].
        """
        try:
            with open(ruta_archivo, 'r') as f:
                datos = json.load(f)
            
            self.reiniciar()

            # 1. Reconstrucción de diccionarios con casteo de claves a enteros
            self.nodos = {int(k): tuple(v) for k, v in datos.get('nodos', {}).items()}
            self.elementos = {int(k): tuple(v) for k, v in datos.get('elementos', {}).items()}
            self.materiales = {int(k): v for k, v in datos.get('materiales', {}).items()}
            self.apoyos = {int(k): v for k, v in datos.get('apoyos', {}).items()}
            self.losas = {int(k): v for k, v in datos.get('losas', {}).items()}
            self.cargas_superficiales = {int(k): v for k, v in datos.get('cargas_superficiales', {}).items()}
            self.armados_diseno = {int(k): v for k, v in datos.get('armados_diseno', {}).items()}
            
            self.hipotesis_de_carga = {int(k): v for k, v in datos.get('hipotesis_de_carga', {}).items()}
            self.cargas_nodales = datos.get('cargas_nodales', [])
            self.cargas_elementos = datos.get('cargas_elementos', [])
            
            # 2. Recalcular el siguiente ID de carga disponible para evitar colisiones
            max_id = 0
            all_cargas = self.cargas_nodales + self.cargas_elementos
            if all_cargas:
                max_id = max(c.get('id_carga', 0) for c in all_cargas)
            self.siguiente_id_carga = max_id + 1

            max_id_sup = 0
            if self.cargas_superficiales:
                max_id_sup = max(self.cargas_superficiales.keys())
            self.siguiente_id_carga_sup = max_id_sup + 1
            
            combos_cargados = datos.get('combinaciones', [])
            if combos_cargados:
                 self.combinaciones = [CombinacionCarga.desde_dict(c) for c in combos_cargados]

            self.archivo_actual = ruta_archivo
            self.modificado = False
        except Exception as e:
            raise IOError(f"No se pudo cargar el archivo (puede que el formato sea incompatible): {e}")

    def guardar_en_archivo(self, ruta_archivo):
        """
        Serializa la instancia actual de la estructura y la exporta 
        al sistema de archivos en formato JSON.
        """
        try:
            datos = {
                'nodos': self.nodos, 'elementos': self.elementos, 'materiales': self.materiales,
                'losas': self.losas, 'apoyos': self.apoyos,
                'hipotesis_de_carga': self.hipotesis_de_carga,
                'cargas_nodales': self.cargas_nodales,
                'cargas_elementos': self.cargas_elementos,
                'cargas_superficiales': self.cargas_superficiales,
                'armados_diseno': self.armados_diseno,
                'combinaciones': [c.to_dict() for c in self.combinaciones]
            }
            with open(ruta_archivo, 'w') as f:
                json.dump(datos, f, indent=4)
            self.archivo_actual = ruta_archivo
            self.modificado = False
        except Exception as e:
            raise IOError(f"No se pudo guardar el archivo: {e}")