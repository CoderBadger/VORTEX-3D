"""
Módulo: widgets_gui.py
Descripción: Colección de componentes de interfaz de usuario personalizados 
(botones, tablas, paneles) creados en PySide6 para mantener la coherencia 
visual y modularidad del diseño en VOTX3D.
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

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QGridLayout, QSpinBox, 
                             QDoubleSpinBox, QPushButton, QTableWidget, QLabel, QSizePolicy,
                             QTableWidgetItem, QMessageBox, QCheckBox, QComboBox, QInputDialog,
                             QStackedWidget, QHeaderView, QTextEdit, QLineEdit, QFormLayout,
                             QSplitter, QTabWidget, QDialog, QScrollArea, QFrame, QAbstractItemView,
                             QDialogButtonBox, QTreeWidget, QTreeWidgetItem, QRadioButton, QApplication)
from PySide6.QtCore import Qt, Signal, QPoint, QPointF
import pyqtgraph as pg
from PySide6.QtGui import QColor, QPixmap, QFont, QPolygonF, QBrush, QPen, QPainter
import numpy as np
import io
import math
import traceback
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
import ast
from procesador_cargas import CombinacionCarga, ProcesadorCargas
from diagramas import GeneradorDiagramas
from vigas import BARRAS_COMERCIALES
import vigas 
from distribuidor_losas import traducir_carga_losa_a_cargas_lineales

try:
    import matplotlib.pyplot as plt
    MATPLOTLIB_DISPONIBLE = True
except ImportError:
    MATPLOTLIB_DISPONIBLE = False

try:
    from col_flex_com import generar_acero_automatico, generar_diagrama_interaccion
    from diag_int_3d_calc import generar_superficie_interaccion_3d, verificar_punto_numericamente
    from col_corte import realizar_diseno_columna_corte
    from interfaz_diag_int_3d import Ventana3DMatplotlib
    from dialogo_punto import PuntoDialog
    MODULES_COLUMNAS_LOADED = True
except ImportError as e:
    print(f"Advertencia: No se pudieron cargar los módulos de diseño de columnas: {e}")
    MODULES_COLUMNAS_LOADED = False

def render_latex(formula):
    if not MATPLOTLIB_DISPONIBLE:
        label_error = QLabel(f"Error: La biblioteca 'matplotlib' es necesaria para mostrar fórmulas. Instálala con 'pip install matplotlib'.\nFórmula: {formula}")
        return label_error

    try:
        fig, ax = plt.subplots(figsize=(6, 0.4), dpi=150) 
        ax.text(0.5, 0.5, formula, size=8, ha='center', va='center') 
        ax.axis('off')

        buf = io.BytesIO()
        fig.savefig(buf, format='png', bbox_inches='tight', pad_inches=0.05, transparent=True)
        buf.seek(0)
        plt.close(fig)

        pixmap = QPixmap()
        pixmap.loadFromData(buf.read())
        
        label_imagen = QLabel()
        label_imagen.setPixmap(pixmap)
        label_imagen.setAlignment(Qt.AlignmentFlag.AlignCenter)
        return label_imagen

    except Exception as e:
        print(f"Error renderizando LaTeX: {e}")
        return QLabel(f"Error al mostrar fórmula: {formula}")

def crear_diagrama_d():
    try:
        fig, ax = plt.subplots(figsize=(1.5, 2.0), dpi=100) 
        fig.patch.set_alpha(0) 
        
        h, b = 50, 30
        rec = 3
        d_est = 0.8
        d_long = 1.6

        ax.add_patch(plt.Rectangle((0, 0), b, h, facecolor='#d9d9d9', edgecolor='black', linewidth=1.0, zorder=1))
        ax.add_patch(plt.Rectangle((rec, rec), b - 2*rec, h - 2*rec, facecolor='none', edgecolor='#e41a1c', linewidth=1.5, zorder=2))

        cx_izq_inf = rec + d_est + d_long/2
        cy_inf = rec + d_est + d_long/2
        cx_der_inf = b - rec - d_est - d_long/2
        ax.add_patch(plt.Circle((cx_izq_inf, cy_inf), d_long/2, facecolor='white', edgecolor='#e41a1c', linewidth=1.0, zorder=3))
        ax.add_patch(plt.Circle((cx_der_inf, cy_inf), d_long/2, facecolor='white', edgecolor='#e41a1c', linewidth=1.0, zorder=3))
        
        cx_izq_sup = rec + d_est + d_long/2
        cy_sup = h - rec - d_est - d_long/2
        cx_der_sup = b - rec - d_est - d_long/2
        ax.add_patch(plt.Circle((cx_izq_sup, cy_sup), d_long/2, facecolor='white', edgecolor='#e41a1c', linewidth=1.0, zorder=3))
        ax.add_patch(plt.Circle((cx_der_sup, cy_sup), d_long/2, facecolor='white', edgecolor='#e41a1c', linewidth=1.0, zorder=3))
            
        ax.plot([b + 2, b + 2], [cy_inf, h], color='black', linewidth=0.8)
        ax.plot([b + 1.5, b + 2.5], [h, h], color='black', linewidth=0.8)
        ax.plot([b + 1.5, b + 2.5], [cy_inf, cy_inf], color='black', linewidth=0.8)
        ax.text(b + 3, h/2 + cy_inf/2, 'd', ha='center', va='center', fontsize=9, color='black')
        
        ax.plot([-2, -2], [0, h], color='black', linewidth=0.8)
        ax.plot([-2.5, -1.5], [h, h], color='black', linewidth=0.8)
        ax.plot([-2.5, -1.5], [0, 0], color='black', linewidth=0.8)
        ax.text(-3, h/2, 'h', ha='center', va='center', fontsize=9, color='black')

        ax.axis('equal')
        ax.axis('off')
        plt.tight_layout(pad=0.1) 

        buf = io.BytesIO()
        fig.savefig(buf, format='png', transparent=True)
        buf.seek(0)
        plt.close(fig)

        pixmap = QPixmap()
        pixmap.loadFromData(buf.read())
        
        label_imagen = QLabel()
        label_imagen.setPixmap(pixmap)
        label_imagen.setAlignment(Qt.AlignmentFlag.AlignCenter)
        return label_imagen

    except Exception as e:
        print(f"Error creando diagrama: {e}")
        return QLabel("Error al generar diagrama.")

class VentanaReporte(QDialog):
    def __init__(self, memoria_calculo, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Memoria de Cálculo Detallada")
        self.setMinimumSize(700, 800)
        
        layout_principal = QVBoxLayout(self)
        
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        
        contenedor_reporte = QWidget()
        self.layout_reporte = QVBoxLayout(contenedor_reporte)
        self.layout_reporte.setSpacing(0)
        self.layout_reporte.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        scroll_area.setWidget(contenedor_reporte)
        layout_principal.addWidget(scroll_area)
        
        self._poblar_reporte(memoria_calculo)

    def _poblar_reporte(self, memoria_calculo):
        """Llena la ventana con el contenido del reporte."""
        for linea in memoria_calculo:
            if linea.startswith('$'):
                widget_linea = render_latex(linea)
            else:
                widget_linea = QLabel(linea)
                widget_linea.setWordWrap(True)
                widget_linea.setTextFormat(Qt.TextFormat.RichText)
                widget_linea.setStyleSheet("font-size: 10pt;")
            
            self.layout_reporte.addWidget(widget_linea)

class DialogoEditarLosasLote(QDialog):
    """
    Diálogo emergente para la edición por lote de propiedades de losas.
    Permite al usuario activar/desactivar qué propiedades desea modificar.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Editar Propiedades de Losas por Lote")
        self.setMinimumWidth(400)
        
        layout_principal = QVBoxLayout(self)
        
        # --- 1. Grupo Distribución ---
        grupo_dist = QGroupBox("1. Modificar Distribución")
        grupo_dist.setCheckable(True) 
        grupo_dist.setChecked(False)
        layout_dist = QFormLayout(grupo_dist)
        
        self.combo_distribucion_lote = QComboBox()
        self.combo_distribucion_lote.addItems(["Bidireccional", "Unidireccional - Global X", "Unidireccional - Global Y"])
        layout_dist.addRow("Nuevo Tipo:", self.combo_distribucion_lote)
        
        layout_principal.addWidget(grupo_dist)
        
        # --- 2. Grupo Espesor ---
        grupo_esp = QGroupBox("2. Modificar Espesor")
        grupo_esp.setCheckable(True)
        grupo_esp.setChecked(False)
        layout_esp = QFormLayout(grupo_esp)
        
        self.spin_espesor_lote = QDoubleSpinBox(decimals=3, minimum=0.01, maximum=5.0, value=0.20, singleStep=0.01)
        layout_esp.addRow("Nuevo Espesor (m):", self.spin_espesor_lote)
        
        layout_principal.addWidget(grupo_esp)
        
        # --- 3. Grupo Peso Específico ---
        grupo_pe = QGroupBox("3. Modificar Peso Específico")
        grupo_pe.setCheckable(True)
        grupo_pe.setChecked(False)
        layout_pe = QFormLayout(grupo_pe)
        
        self.spin_pe_lote = QDoubleSpinBox(decimals=2, minimum=0.0, maximum=100.0, value=24.0, singleStep=1.0)
        layout_pe.addRow("Nuevo P.E. (kN/m³):", self.spin_pe_lote)
        
        layout_principal.addWidget(grupo_pe)
        
        # --- Botones Aceptar/Cancelar ---
        botones = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        botones.accepted.connect(self.accept)
        botones.rejected.connect(self.reject)
        layout_principal.addWidget(botones)
        
        self.grupo_dist = grupo_dist
        self.grupo_esp = grupo_esp
        self.grupo_pe = grupo_pe

    def get_valores_lote(self):
        """
        Recopila los valores del diálogo y los devuelve en un formato
        listo para el método del modelo.
        """
        valores = {
            'distribucion': None,
            'eje_uni': None,
            'espesor': None,
            'peso_especifico': None
        }
        
        # 1. Leer Distribución
        if self.grupo_dist.isChecked():
            seleccion_dist = self.combo_distribucion_lote.currentText()
            if "Bidireccional" in seleccion_dist:
                valores['distribucion'] = 'bidireccional'
                valores['eje_uni'] = None
            elif "Global X" in seleccion_dist:
                valores['distribucion'] = 'unidireccional'
                valores['eje_uni'] = 'Global X'
            elif "Global Y" in seleccion_dist:
                valores['distribucion'] = 'unidireccional'
                valores['eje_uni'] = 'Global Y'
        
        # 2. Leer Espesor
        if self.grupo_esp.isChecked():
            valores['espesor'] = self.spin_espesor_lote.value()
            
        # 3. Leer Peso Específico
        if self.grupo_pe.isChecked():
            valores['peso_especifico'] = self.spin_pe_lote.value()
            
        return valores

class PestañaBase(QWidget):
    datos_modificados = Signal()
    def __init__(self, modelo, gestor_visualizacion, ventana_principal):
        super().__init__()
        self.modelo = modelo
        self.gestor_visualizacion = gestor_visualizacion
        self.ventana_principal = ventana_principal

    def _parsear_ids(self, texto_ids):
        ids_validos = set()
        if not texto_ids.strip(): return []
        partes = texto_ids.split(',')
        for parte in partes:
            texto_limpio = parte.strip()
            if not texto_limpio: raise ValueError("Formato no válido: comas extra o elementos vacíos.")
            try:
                id_num = int(texto_limpio)
                if id_num <= 0: raise ValueError(f"ID '{id_num}' debe ser positivo.")
                ids_validos.add(id_num)
            except ValueError:
                raise ValueError(f"'{texto_limpio}' no es un número entero positivo.")
        return sorted(list(ids_validos))

    def refrescar_visualizacion(self):
        if self.ventana_principal:
            self.ventana_principal._actualizar_solo_visualizacion()

    def refrescar(self):
        raise NotImplementedError("Cada pestaña debe implementar su propio método de refresco.")

class PestañaNodos(PestañaBase):
    def __init__(self, modelo, gestor_visualizacion, ventana_principal):
        super().__init__(modelo, gestor_visualizacion, ventana_principal)
        
        layout = QVBoxLayout(self)
        grupo_form = QGroupBox("Definición de Nodos"); layout.addWidget(grupo_form)
        
        layout_form = QFormLayout(grupo_form)
        layout_form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapAllRows)
        
        self.id_nodo = QSpinBox(minimum=1, maximum=9999)
        self.x_nodo = QDoubleSpinBox(decimals=3, minimum=-1e6, maximum=1e6, singleStep=1)
        self.y_nodo = QDoubleSpinBox(decimals=3, minimum=-1e6, maximum=1e6, singleStep=1)
        self.z_nodo = QDoubleSpinBox(decimals=3, minimum=-1e6, maximum=1e6, singleStep=1)
        
        layout_form.addRow("ID Nodo:", self.id_nodo)
        layout_form.addRow("Coord X:", self.x_nodo)
        layout_form.addRow("Coord Y:", self.y_nodo)
        layout_form.addRow("Coord Z:", self.z_nodo)

        botones_layout = QHBoxLayout()
        self.btn_agregar = QPushButton("Añadir/Actualizar")
        self.btn_eliminar = QPushButton("Eliminar Seleccionado")
        botones_layout.addWidget(self.btn_agregar)
        botones_layout.addWidget(self.btn_eliminar)
        layout_form.addRow(botones_layout) 

        self.btn_guardar_tabla = QPushButton("Guardar Cambios en Tabla")
        self.btn_guardar_tabla.setEnabled(False)
        layout.addWidget(self.btn_guardar_tabla)

        self.tabla = QTableWidget(columnCount=4); layout.addWidget(self.tabla)
        self.tabla.setHorizontalHeaderLabels(["ID", "X", "Y", "Z"])
        header = self.tabla.horizontalHeader()
        for i in range(self.tabla.columnCount()):
            header.setSectionResizeMode(i, QHeaderView.ResizeToContents)
        self.tabla.setSelectionBehavior(QAbstractItemView.SelectRows)

        self.btn_agregar.clicked.connect(self.agregar)
        self.btn_eliminar.clicked.connect(self.eliminar)
        self.tabla.itemClicked.connect(self.seleccionar_desde_tabla)
        self.tabla.itemChanged.connect(self._marcar_cambios_en_tabla)
        self.btn_guardar_tabla.clicked.connect(self._guardar_cambios_de_tabla)

    def agregar(self):
        try:
            coords = (self.x_nodo.value(), self.y_nodo.value(), self.z_nodo.value())
            id_val = self.id_nodo.value()
            if id_val in self.modelo.nodos: self.modelo.actualizar_nodo(id_val, coords)
            else: self.modelo.agregar_nodo(id_val, coords)
            self.refrescar()
            self.datos_modificados.emit()
        except ValueError as e: QMessageBox.warning(self, "Error", str(e))

    def eliminar(self):
        rows = sorted(list({item.row() for item in self.tabla.selectedItems()}), reverse=True)
        if not rows: return
        if QMessageBox.question(self, "Confirmar", f"¿Eliminar {len(rows)} nodos?") == QMessageBox.Yes:
            for row in rows:
                id_nodo = int(self.tabla.item(row, 0).text())
                self.modelo.eliminar_nodo(id_nodo)
                self.datos_modificados.emit()
            self.refrescar()

    def _marcar_cambios_en_tabla(self): self.btn_guardar_tabla.setEnabled(True)

    def _guardar_cambios_de_tabla(self):
        try:
            for row in range(self.tabla.rowCount()):
                id_nodo = int(self.tabla.item(row, 0).text())
                x = float(self.tabla.item(row, 1).text())
                y = float(self.tabla.item(row, 2).text())
                z = float(self.tabla.item(row, 3).text()) 
                self.modelo.actualizar_nodo(id_nodo, (x, y, z))
            self.btn_guardar_tabla.setEnabled(False)
            self.datos_modificados.emit()
            self.refrescar_visualizacion()
        except (ValueError, TypeError) as e: QMessageBox.critical(self, "Error de Datos", f"Error al guardar los datos en la tabla.\n\nDetalle: {e}")
        except Exception as e: QMessageBox.critical(self, "Error Inesperado", f"Ocurrió un error: {e}")

    def seleccionar_desde_tabla(self, item):
        row = item.row()
        id_nodo = int(self.tabla.item(row, 0).text())
        coords = self.modelo.nodos[id_nodo]
        self.id_nodo.setValue(id_nodo)
        self.x_nodo.setValue(coords[0]); self.y_nodo.setValue(coords[1]); self.z_nodo.setValue(coords[2])

    def refrescar_tabla(self):
        self.tabla.blockSignals(True)
        self.tabla.setRowCount(len(self.modelo.nodos))
        for i, (id_nodo, (x,y,z)) in enumerate(sorted(self.modelo.nodos.items())):
            id_item = QTableWidgetItem(str(id_nodo)); id_item.setFlags(id_item.flags() & ~Qt.ItemIsEditable)
            self.tabla.setItem(i, 0, id_item)
            self.tabla.setItem(i, 1, QTableWidgetItem(f"{x:.3f}"))
            self.tabla.setItem(i, 2, QTableWidgetItem(f"{y:.3f}"))
            self.tabla.setItem(i, 3, QTableWidgetItem(f"{z:.3f}"))
        self.tabla.blockSignals(False)

    def refrescar(self):
        self.refrescar_tabla()
        self.id_nodo.setValue(self.modelo.get_siguiente_id(self.modelo.nodos))

class PestañaElementos(PestañaBase):
    def __init__(self, modelo, gestor_visualizacion, ventana_principal):
        super().__init__(modelo, gestor_visualizacion, ventana_principal)
        self.ultimo_material_id = None
        layout = QVBoxLayout(self)
        grupo_form = QGroupBox("Definición de Elementos 1D (Viga/Columna)"); layout.addWidget(grupo_form)
        
        layout_form = QFormLayout(grupo_form)
        layout_form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapAllRows)

        self.id_elem = QSpinBox(minimum=1, maximum=9999)
        self.nodo_i = QSpinBox(minimum=1, maximum=9999)
        self.nodo_j = QSpinBox(minimum=1, maximum=9999)
        self.material = QComboBox()

        layout_form.addRow("ID Elemento:", self.id_elem)
        layout_form.addRow("Nodo Inicio:", self.nodo_i)
        layout_form.addRow("Nodo Fin:", self.nodo_j)
        layout_form.addRow("Material:", self.material)

        botones_layout = QHBoxLayout()
        self.btn_agregar = QPushButton("Añadir/Actualizar")
        self.btn_eliminar = QPushButton("Eliminar Selección")
        self.btn_asignar_material = QPushButton("Asignar Material a Selección")
        botones_layout.addWidget(self.btn_agregar)
        botones_layout.addWidget(self.btn_eliminar)
        botones_layout.addWidget(self.btn_asignar_material)
        layout_form.addRow(botones_layout)
        
        self.btn_guardar_tabla = QPushButton("Guardar Cambios en Tabla")
        self.btn_guardar_tabla.setEnabled(False)
        layout.addWidget(self.btn_guardar_tabla)        

        self.tabla = QTableWidget(columnCount=4); layout.addWidget(self.tabla)
        self.tabla.setHorizontalHeaderLabels(["ID", "Nodo I", "Nodo J", "Material"])
        self.tabla.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tabla.setSelectionMode(QAbstractItemView.ExtendedSelection)
        header = self.tabla.horizontalHeader()
        for i in range(self.tabla.columnCount()):
            header.setSectionResizeMode(i, QHeaderView.ResizeToContents)

        self.btn_agregar.clicked.connect(self.agregar)
        self.btn_eliminar.clicked.connect(self.eliminar)
        self.btn_asignar_material.clicked.connect(self.asignar_material_a_seleccion)
        self.tabla.itemChanged.connect(self._marcar_cambios_en_tabla)
        self.btn_guardar_tabla.clicked.connect(self._guardar_cambios_de_tabla)
        self.tabla.itemClicked.connect(self.seleccionar_desde_tabla)

    def agregar(self):
        try:
            id_val = self.id_elem.value(); ni = self.nodo_i.value(); nj = self.nodo_j.value()
            mat_id = self.material.currentData()
            if mat_id is None or mat_id == -1: raise ValueError("Debe seleccionar un material válido.")
            self.ultimo_material_id = mat_id
            if id_val in self.modelo.elementos: self.modelo.actualizar_elemento(id_val, ni, nj, mat_id)
            else: self.modelo.agregar_elemento(id_val, ni, nj, mat_id)
            self.datos_modificados.emit()
            self.refrescar()
        except ValueError as e: QMessageBox.warning(self, "Error", str(e))
    
    def eliminar(self):
        rows = sorted(list({item.row() for item in self.tabla.selectedItems()}), reverse=True)
        if not rows: return
        if QMessageBox.question(self, "Confirmar", f"¿Eliminar {len(rows)} elementos?") == QMessageBox.Yes:
            for row in rows:
                id_elem = int(self.tabla.item(row, 0).text())
                self.modelo.eliminar_elemento(id_elem)
            self.datos_modificados.emit()
            self.refrescar()

    def asignar_material_a_seleccion(self):
        """
        Toma todos los elementos seleccionados en la tabla y les asigna un nuevo
        material elegido por el usuario desde un diálogo.
        """
        
        # 1. Obtener filas seleccionadas
        items_seleccionados = self.tabla.selectedItems()
        if not items_seleccionados:
            QMessageBox.information(self, "Selección Vacía", "Debes seleccionar al menos una fila en la tabla.")
            return

        filas_seleccionadas = sorted(list(set(item.row() for item in items_seleccionados)))
        
        # 2. Obtener IDs de elementos de esas filas
        ids_elementos_a_modificar = []
        for fila in filas_seleccionadas:
            try:
                id_elem = int(self.tabla.item(fila, 0).text())
                ids_elementos_a_modificar.append(id_elem)
            except Exception as e:
                print(f"Error al leer ID de elemento en fila {fila}: {e}")
        
        if not ids_elementos_a_modificar:
            QMessageBox.warning(self, "Error", "No se pudieron obtener los IDs de los elementos seleccionados.")
            return

        # 3. Preparar el diálogo para seleccionar material
        materiales_disponibles = {} # Diccionario: { "ID 1; Desc": 1, ... }
        for mat_id, datos in sorted(self.modelo.materiales.items()):
            if datos.get('tipo', 'rectangular') != 'placa':
                desc = datos.get('descripcion', '')
                texto_item = f"ID {mat_id}" + (f"; {desc}" if desc else "")
                materiales_disponibles[texto_item] = mat_id
        
        if not materiales_disponibles:
            QMessageBox.warning(self, "Sin Materiales", "No hay materiales de tipo 'Pórtico' (rectangular/general) definidos en la pestaña 'Materiales'.")
            return

        lista_nombres_materiales = list(materiales_disponibles.keys())

        # 4. Mostrar el QInputDialog para que el usuario elija
        nombre_material_elegido, ok = QInputDialog.getItem(
            self,
            "Asignación Masiva de Material",
            f"Selecciona el material a asignar a los {len(ids_elementos_a_modificar)} elementos seleccionados:",
            lista_nombres_materiales,
            0,      
            False   
        )

        # 5. Si el usuario presiona "OK" y eligió un material
        if ok and nombre_material_elegido:
            id_material_nuevo = materiales_disponibles[nombre_material_elegido]
            
            try:
                # 6. Llamar a la nueva función del modelo
                num_actualizados = self.modelo.actualizar_material_de_elementos(
                    ids_elementos_a_modificar, 
                    id_material_nuevo
                )
                
                QMessageBox.information(self, "Éxito", f"{num_actualizados} elementos han sido actualizados al material ID {id_material_nuevo}.")
                
                # 7. Refrescar la GUI para mostrar los cambios
                self.refrescar() 
                self.datos_modificados.emit() 

            except ValueError as e:
                QMessageBox.critical(self, "Error en Asignación", str(e))
            except Exception as e:
                QMessageBox.critical(self, "Error Inesperado", f"Ocurrió un error: {e}")

    def seleccionar_desde_tabla(self, item):
        row = item.row()
        id_elem = int(self.tabla.item(row, 0).text())
        if id_elem not in self.modelo.elementos: return
        ni, nj, mat_id = self.modelo.elementos[id_elem]
        self.id_elem.setValue(id_elem)
        self.nodo_i.setValue(ni)
        self.nodo_j.setValue(nj)
        index = self.material.findData(mat_id)
        if index != -1: self.material.setCurrentIndex(index)

    def _marcar_cambios_en_tabla(self): self.btn_guardar_tabla.setEnabled(True)

    def _guardar_cambios_de_tabla(self):
        try:
            for row in range(self.tabla.rowCount()):
                id_elem = int(self.tabla.item(row, 0).text())
                ni = int(self.tabla.item(row, 1).text())
                nj = int(self.tabla.item(row, 2).text())
                mat_id = int(self.tabla.item(row, 3).text())
                if mat_id not in self.modelo.materiales: raise ValueError(f"El material ID {mat_id} no existe.")
                self.modelo.actualizar_elemento(id_elem, ni, nj, mat_id)
            self.btn_guardar_tabla.setEnabled(False)
            self.datos_modificados.emit()
            self.refrescar_visualizacion()
        except (ValueError, TypeError) as e: QMessageBox.critical(self, "Error de Datos", f"Error al guardar datos de la tabla.\nDetalle: {e}")
        except Exception as e: QMessageBox.critical(self, "Error Inesperado", f"Ocurrió un error: {e}")

    def refrescar_tabla(self):
        self.tabla.blockSignals(True)
        self.tabla.setRowCount(len(self.modelo.elementos))
        for i, (id_elem, (ni, nj, mid)) in enumerate(sorted(self.modelo.elementos.items())):
            id_item = QTableWidgetItem(str(id_elem)); id_item.setFlags(id_item.flags() & ~Qt.ItemIsEditable)
            self.tabla.setItem(i, 0, id_item)
            self.tabla.setItem(i, 1, QTableWidgetItem(str(ni)))
            self.tabla.setItem(i, 2, QTableWidgetItem(str(nj)))
            self.tabla.setItem(i, 3, QTableWidgetItem(str(mid)))
        self.tabla.blockSignals(False)

    def refrescar_formularios(self):
        self.id_elem.setValue(self.modelo.get_siguiente_id(self.modelo.elementos))
        self.material.clear()
        
        materiales_portico_existen = False
        for mat_id, datos in sorted(self.modelo.materiales.items()):
            if datos.get('tipo', 'rectangular') != 'placa':
                desc = datos['descripcion']
                texto = f"ID {mat_id}" + (f"; {desc}" if desc else "")
                self.material.addItem(texto, mat_id)
                materiales_portico_existen = True
        
        if not materiales_portico_existen:
            self.material.addItem("Cree un material de Pórtico", -1)

        if self.ultimo_material_id is not None:
            index = self.material.findData(self.ultimo_material_id)
            if index != -1: self.material.setCurrentIndex(index)

    def refrescar(self):
        self.refrescar_tabla()
        self.refrescar_formularios()

class PestañaMateriales(PestañaBase):
    datos_modificados = Signal()
    
    def __init__(self, modelo, gestor_visualizacion, ventana_principal):
        super().__init__(modelo, gestor_visualizacion, ventana_principal)
        
        self.datos_modificados.connect(self.refrescar_visualizacion)

        layout = QVBoxLayout(self)
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setMaximumHeight(400) 
        grupo_form = QGroupBox("Definir Propiedades de Materiales y Secciones")
        scroll_area.setWidget(grupo_form)
        layout.addWidget(scroll_area)
        
        layout_grupo = QVBoxLayout(grupo_form)

        layout_controles_superiores = QGridLayout()
        self.id_mat = QSpinBox(minimum=1, maximum=9999)
        self.descripcion_mat = QLineEdit()
        self.combo_tipo_seccion = QComboBox()
        self.combo_tipo_seccion.addItems(["Rectangular", "General"])
        
        layout_controles_superiores.addWidget(QLabel("ID Material:"), 0, 0)
        layout_controles_superiores.addWidget(self.id_mat, 0, 1)
        layout_controles_superiores.addWidget(QLabel("Tipo de Sección:"), 0, 2)
        layout_controles_superiores.addWidget(self.combo_tipo_seccion, 0, 3)
        layout_controles_superiores.addWidget(QLabel("Descripción:"), 1, 0)
        layout_controles_superiores.addWidget(self.descripcion_mat, 1, 1, 1, 3)
        
        layout_grupo.addLayout(layout_controles_superiores)

        self.pila_propiedades = QStackedWidget()
        self.crear_panel_rectangular()
        self.crear_panel_general()
        layout_grupo.addWidget(self.pila_propiedades)

        self.combo_tipo_seccion.currentIndexChanged.connect(self.pila_propiedades.setCurrentIndex)
        
        botones_layout = QHBoxLayout()
        self.btn_agregar = QPushButton("Añadir/Actualizar")
        self.btn_eliminar = QPushButton("Eliminar Seleccionado")
        botones_layout.addWidget(self.btn_agregar)
        botones_layout.addWidget(self.btn_eliminar)
        layout_grupo.addLayout(botones_layout)

        self.btn_guardar_tabla = QPushButton("Guardar Cambios en Tabla")
        self.btn_guardar_tabla.setEnabled(False)
        layout.addWidget(self.btn_guardar_tabla)

        self.tabla = QTableWidget(columnCount=15)
        self.tabla.setHorizontalHeaderLabels(["ID", "Tipo", "Desc.", "E", "ν", "b", "h", "G", "A", "J", "Iy", "Iz", "Ay", "Az", "PE (kN/m³)"])
        self.tabla.setSelectionBehavior(QAbstractItemView.SelectRows)
        header = self.tabla.horizontalHeader()
        for i in range(self.tabla.columnCount()):
            header.setSectionResizeMode(i, QHeaderView.ResizeToContents)
        layout.addWidget(self.tabla, stretch=1)
        
        self.btn_agregar.clicked.connect(self.agregar)
        self.btn_eliminar.clicked.connect(self.eliminar)
        self.btn_guardar_tabla.clicked.connect(self._guardar_cambios_de_tabla)
        self.tabla.itemChanged.connect(self._marcar_cambios_en_tabla)
        self.tabla.itemClicked.connect(self.seleccionar_desde_tabla)

    def crear_panel_rectangular(self):
        panel = QWidget(); layout = QFormLayout(panel)
        layout.setContentsMargins(0, 10, 0, 0); layout.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapAllRows)
        self.E_rect = QDoubleSpinBox(decimals=3, minimum=0, maximum=1e25, value=21000, singleStep=500)
        self.nu_rect = QDoubleSpinBox(decimals=3, minimum=0, maximum=0.5, value=0.3, singleStep=0.1)
        self.b_rect = QDoubleSpinBox(decimals=4, minimum=0, maximum=10000, value=0.20, singleStep=0.01)
        self.h_rect = QDoubleSpinBox(decimals=4, minimum=0, maximum=10000, value=0.30, singleStep=0.01)
        self.pe_rect = QDoubleSpinBox(decimals=2, minimum=0, maximum=100, value=24.0, singleStep=1)
        layout.addRow("Módulo de Young (E) [MPa]:", self.E_rect); layout.addRow("Coef. de Poisson (ν):", self.nu_rect)
        layout.addRow("Base (b) [m]:", self.b_rect); layout.addRow("Altura (h) [m]:", self.h_rect)
        layout.addRow("Peso Específico (kN/m³):", self.pe_rect)
        self.pila_propiedades.addWidget(panel)

    def crear_panel_general(self):
        panel = QWidget(); layout = QFormLayout(panel)
        layout.setContentsMargins(0, 10, 0, 0); layout.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapAllRows)
        self.E_gen = QDoubleSpinBox(decimals=3, minimum=0, maximum=1e25, value=21000, singleStep=500)
        self.G_gen = QDoubleSpinBox(decimals=3, minimum=0, maximum=1e25, value=8750, singleStep=250)
        self.A_gen = QDoubleSpinBox(decimals=8, minimum=0, maximum=1e6, value=0.08, singleStep=0.01)
        self.J_gen = QDoubleSpinBox(decimals=8, minimum=0, maximum=1e6, value=0.001)
        self.Iy_gen = QDoubleSpinBox(decimals=8, minimum=0, maximum=1e6, value=0.00026)
        self.Iz_gen = QDoubleSpinBox(decimals=8, minimum=0, maximum=1e6, value=0.00106)
        self.Ay_gen = QDoubleSpinBox(decimals=8, minimum=0, maximum=1e6, value=0.06)
        self.Ay_gen.setToolTip("Área de cortante local 'y' (resiste V_y, asociada a M_z)")
        self.Az_gen = QDoubleSpinBox(decimals=8, minimum=0, maximum=1e6, value=0.06)
        self.Az_gen.setToolTip("Área de cortante local 'z' (resiste V_z, asociada a M_y)")
        self.pe_gen = QDoubleSpinBox(decimals=2, minimum=0, maximum=100, value=24.0, singleStep=1)
        layout.addRow("Módulo de Young (E) [MPa]:", self.E_gen); layout.addRow("Módulo de Corte (G) [MPa]:", self.G_gen)
        layout.addRow("Área (A) [m²]:", self.A_gen); layout.addRow("Inercia Torsional (J) [m⁴]:", self.J_gen)
        layout.addRow("Inercia Y (Iy) [m⁴]:", self.Iy_gen); layout.addRow("Inercia Z (Iz) [m⁴]:", self.Iz_gen)
        layout.addRow("Área Cortante Ay [m²]:", self.Ay_gen)
        layout.addRow("Área Cortante Az [m²]:", self.Az_gen)
        layout.addRow("Peso Específico (kN/m³):", self.pe_gen)
        self.pila_propiedades.addWidget(panel)

    def agregar(self):
        try:
            id_val = self.id_mat.value(); desc = self.descripcion_mat.text(); idx_tipo = self.combo_tipo_seccion.currentIndex()
            pe_val = 0.0
            if idx_tipo == 0:
                tipo_seccion = 'rectangular'
                props = (self.E_rect.value(), self.nu_rect.value(), self.b_rect.value(), self.h_rect.value())
                pe_val = self.pe_rect.value()
            elif idx_tipo == 1:
                tipo_seccion = 'general'
                props = (self.E_gen.value(), self.G_gen.value(), self.A_gen.value(), 
                         self.J_gen.value(), self.Iy_gen.value(), self.Iz_gen.value(),
                         self.Ay_gen.value(), self.Az_gen.value())
                pe_val = self.pe_gen.value()
                
            if id_val in self.modelo.materiales: self.modelo.actualizar_material(id_val, desc, tipo_seccion, props, pe_val)
            else: self.modelo.agregar_material(id_val, desc, tipo_seccion, props, pe_val)
            self.refrescar()
            self.datos_modificados.emit()
        except ValueError as e: QMessageBox.warning(self, "Error de Datos", str(e))
    
    def eliminar(self):
        rows = sorted(list({item.row() for item in self.tabla.selectedItems()}), reverse=True)
        if not rows: return
        if QMessageBox.question(self, "Confirmar", f"¿Eliminar {len(rows)} materiales?") == QMessageBox.Yes:
            for row in rows:
                id_mat = int(self.tabla.item(row, 0).text())
                self.modelo.eliminar_material(id_mat)
            self.refrescar()
            self.datos_modificados.emit()

    def seleccionar_desde_tabla(self, item):
        row = item.row()
        id_mat = int(self.tabla.item(row, 0).text())
        if id_mat not in self.modelo.materiales: return
        datos = self.modelo.materiales[id_mat]
        self.id_mat.setValue(id_mat)
        self.descripcion_mat.setText(datos.get('descripcion', ''))
        tipo = datos.get('tipo', 'rectangular')
        props = datos.get('propiedades', [])
        pe_val = datos.get('peso_especifico', 24.0) # Obtener PE
        if tipo == 'rectangular':
            self.combo_tipo_seccion.setCurrentIndex(0)
            if len(props) == 4:
                self.E_rect.setValue(props[0]); self.nu_rect.setValue(props[1])
                self.b_rect.setValue(props[2]); self.h_rect.setValue(props[3])
            self.pe_rect.setValue(pe_val) # Asignar PE
        elif tipo == 'general':
            self.combo_tipo_seccion.setCurrentIndex(1)
            if len(props) == 8: 
                self.E_gen.setValue(props[0]); self.G_gen.setValue(props[1]); self.A_gen.setValue(props[2])
                self.J_gen.setValue(props[3]); self.Iy_gen.setValue(props[4]); self.Iz_gen.setValue(props[5])
                self.Ay_gen.setValue(props[6]) 
                self.Az_gen.setValue(props[7]) 
            self.pe_gen.setValue(pe_val) # Asignar PE

    def _marcar_cambios_en_tabla(self): self.btn_guardar_tabla.setEnabled(True)

    def _guardar_cambios_de_tabla(self):
        try:
            materiales_actualizados = {}
            for row in range(self.tabla.rowCount()):
                id_mat = int(self.tabla.item(row, 0).text()); tipo_seccion = self.tabla.item(row, 1).text().lower(); desc = self.tabla.item(row, 2).text()
                props = tuple()
                pe_val = 0.0
                if tipo_seccion == 'rectangular':
                    E_val = float(self.tabla.item(row, 3).text()); nu_val = float(self.tabla.item(row, 4).text())
                    b_val = float(self.tabla.item(row, 5).text()); h_val = float(self.tabla.item(row, 6).text())
                    props = (E_val, nu_val, b_val, h_val)
                    pe_val = float(self.tabla.item(row, 14).text())
                elif tipo_seccion == 'general':
                    E_val = float(self.tabla.item(row, 3).text()); G_val = float(self.tabla.item(row, 7).text())
                    A_val = float(self.tabla.item(row, 8).text()); J_val = float(self.tabla.item(row, 9).text())
                    Iy_val = float(self.tabla.item(row, 10).text()); Iz_val = float(self.tabla.item(row, 11).text())
                    Ay_val = float(self.tabla.item(row, 12).text())
                    Az_val = float(self.tabla.item(row, 13).text())
                    pe_val = float(self.tabla.item(row, 14).text())
                    props = (E_val, G_val, A_val, J_val, Iy_val, Iz_val, Ay_val, Az_val)
                else: 
                    raise ValueError(f"Tipo '{self.tabla.item(row, 1).text()}' no reconocido.")
                materiales_actualizados[id_mat] = {'tipo': tipo_seccion, 'descripcion': desc, 'propiedades': props, 'peso_especifico': pe_val}
            self.modelo.materiales = materiales_actualizados
            self.modelo.modificado = True
            self.btn_guardar_tabla.setEnabled(False)
            self.datos_modificados.emit()
            self.refrescar()
            QMessageBox.information(self, "Éxito", "Cambios en materiales guardados.")
        except (ValueError, TypeError, AttributeError) as e:
            QMessageBox.critical(self, "Error de Datos", f"Error al guardar. Verifique los valores.\nDetalle: {e}")
            self.refrescar()
        except Exception as e:
            QMessageBox.critical(self, "Error Inesperado", f"Ocurrió un error: {e}")
            self.refrescar()

    def refrescar(self):
        self.tabla.blockSignals(True)
        self.tabla.setRowCount(len(self.modelo.materiales))
        for i, (id_mat, datos) in enumerate(sorted(self.modelo.materiales.items())):
            tipo = datos.get("tipo", "rectangular"); desc = datos.get("descripcion", ""); props = datos.get("propiedades", tuple())
            self.tabla.setItem(i, 0, QTableWidgetItem(str(id_mat)))
            self.tabla.setItem(i, 1, QTableWidgetItem(tipo.capitalize()))
            self.tabla.setItem(i, 2, QTableWidgetItem(desc))
            for j in range(3, 15): self.tabla.setItem(i, j, QTableWidgetItem("")) # Limpiar todas las columnas
            if tipo == 'rectangular':
                E, nu, b, h, *_ = props
                self.tabla.setItem(i, 3, QTableWidgetItem(f"{E:.2e}")); self.tabla.setItem(i, 4, QTableWidgetItem(f"{nu:.3f}"))
                self.tabla.setItem(i, 5, QTableWidgetItem(f"{b:.4f}")); self.tabla.setItem(i, 6, QTableWidgetItem(f"{h:.4f}"))
            elif tipo == 'general':
                if len(props) == 8:
                    E, G, A, J, Iy, Iz, Ay, Az = props
                    self.tabla.setItem(i, 3, QTableWidgetItem(f"{E:.2e}")); self.tabla.setItem(i, 7, QTableWidgetItem(f"{G:.2e}"))
                    self.tabla.setItem(i, 8, QTableWidgetItem(f"{A:.6f}")); self.tabla.setItem(i, 9, QTableWidgetItem(f"{J:.6f}"))
                    self.tabla.setItem(i, 10, QTableWidgetItem(f"{Iy:.6f}")); self.tabla.setItem(i, 11, QTableWidgetItem(f"{Iz:.6f}"))
                    self.tabla.setItem(i, 12, QTableWidgetItem(f"{Ay:.6f}")) 
                    self.tabla.setItem(i, 13, QTableWidgetItem(f"{Az:.6f}")) 
                else: # Fallback para archivos viejos
                    E, G, A, J, Iy, Iz = props
                    self.tabla.setItem(i, 3, QTableWidgetItem(f"{E:.2e}")); self.tabla.setItem(i, 7, QTableWidgetItem(f"{G:.2e}"))
                    self.tabla.setItem(i, 8, QTableWidgetItem(f"{A:.6f}")); self.tabla.setItem(i, 9, QTableWidgetItem(f"{J:.6f}"))
                    self.tabla.setItem(i, 10, QTableWidgetItem(f"{Iy:.6f}")); self.tabla.setItem(i, 11, QTableWidgetItem(f"{Iz:.6f}"))
            pe_val = datos.get('peso_especifico', 0.0)
            self.tabla.setItem(i, 14, QTableWidgetItem(f"{pe_val:.2f}"))
        self.tabla.blockSignals(False)
        self.id_mat.setValue(self.modelo.get_siguiente_id(self.modelo.materiales))

class PestañaDefinicionLosas(PestañaBase):
    def __init__(self, modelo, gestor_visualizacion, ventana_principal):
        super().__init__(modelo, gestor_visualizacion, ventana_principal)
        
        layout = QVBoxLayout(self)
        grupo_form = QGroupBox("Definición de Losas para Distribución de Carga")
        layout.addWidget(grupo_form)
        
        layout_form = QFormLayout(grupo_form)
        layout_form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapAllRows)

        # Controles del formulario
        self.id_losa = QSpinBox(minimum=1, maximum=9999)
        self.nodos_ids = QLineEdit()
        self.nodos_ids.setPlaceholderText("Ej: 1, 2, 3, 4 (exactamente 4 nodos)")
        
        self.combo_distribucion = QComboBox()
        self.combo_distribucion.addItems(["Bidireccional", "Unidireccional"])
        
        self.combo_eje_uni = QComboBox()
        self.combo_eje_uni.addItems(["Global X", "Global Y"])
        self.label_eje_uni = QLabel("Eje de Carga (Uni):")

        self.espesor_losa = QDoubleSpinBox(decimals=3, minimum=0.01, maximum=2.0, value=0.20, singleStep=0.01)
        self.pe_losa = QDoubleSpinBox(decimals=2, minimum=0, maximum=100, value=24.0, singleStep=1)


        # Añadir widgets al layout
        layout_form.addRow("ID Losa:", self.id_losa)
        layout_form.addRow("Nodos (IDs):", self.nodos_ids)
        layout_form.addRow("Tipo de Distribución:", self.combo_distribucion)
        layout_form.addRow(self.label_eje_uni, self.combo_eje_uni)
        layout_form.addRow("Espesor (m):", self.espesor_losa)
        layout_form.addRow("Peso Específico (kN/m³):", self.pe_losa)
        
        # Lógica para habilitar/deshabilitar el combo de ejes
        self.combo_distribucion.currentIndexChanged.connect(self._actualizar_estado_eje_uni)
        self._actualizar_estado_eje_uni() # Llamada inicial

        # Botones de acción
        botones_layout = QHBoxLayout()
        self.btn_agregar = QPushButton("Añadir/Actualizar")
        self.btn_eliminar = QPushButton("Eliminar Selección")
        self.btn_asignar_distribucion = QPushButton("Editar Selección")
        botones_layout.addWidget(self.btn_agregar)
        botones_layout.addWidget(self.btn_eliminar)
        botones_layout.addWidget(self.btn_asignar_distribucion)
        layout_form.addRow(botones_layout)
        self.btn_guardar_tabla = QPushButton("Guardar Cambios en Tabla")
        self.btn_guardar_tabla.setEnabled(False)
        layout.addWidget(self.btn_guardar_tabla)

        # Tabla de visualización (modificarla)
        self.tabla = QTableWidget(columnCount=6)
        self.tabla.setHorizontalHeaderLabels(["ID", "Nodos", "Distribución", "Eje Uni.", "Espesor (m)", "PE (kN/m³)"])
        self.tabla.setSelectionBehavior(QAbstractItemView.SelectRows)
        # Permitimos que la tabla se estire, pero ID y Nodos tendrán más peso
        header = self.tabla.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        layout.addWidget(self.tabla)
        
        # Conexiones
        self.btn_agregar.clicked.connect(self.agregar)
        self.btn_eliminar.clicked.connect(self.eliminar)
        self.tabla.itemClicked.connect(self.seleccionar_desde_tabla)
        self.btn_asignar_distribucion.clicked.connect(self.editar_seleccion_lote)
        self.tabla.itemChanged.connect(self._marcar_cambios_en_tabla)
        self.btn_guardar_tabla.clicked.connect(self._guardar_cambios_de_tabla)

    def _actualizar_estado_eje_uni(self):
        es_unidireccional = self.combo_distribucion.currentText() == "Unidireccional"
        self.label_eje_uni.setVisible(es_unidireccional)
        self.combo_eje_uni.setVisible(es_unidireccional)

    def agregar(self):
        try:
            id_val = self.id_losa.value()
            nodos_lista = self._parsear_ids(self.nodos_ids.text())
            distribucion = self.combo_distribucion.currentText().lower()
            eje_uni = self.combo_eje_uni.currentText() if distribucion == "unidireccional" else None
            espesor_val = self.espesor_losa.value()
            pe_val = self.pe_losa.value()

            if id_val in self.modelo.losas:
                self.modelo.actualizar_losa(id_val, nodos_lista, distribucion, eje_uni, espesor_val, pe_val)
            else:
                self.modelo.agregar_losa(id_val, nodos_lista, distribucion, eje_uni, espesor_val, pe_val)
            
            self.datos_modificados.emit()
            self.refrescar()
        except ValueError as e:
            QMessageBox.warning(self, "Error de Entrada", str(e))

    def eliminar(self):
        rows = sorted(list({item.row() for item in self.tabla.selectedItems()}), reverse=True)
        if not rows: return
        if QMessageBox.question(self, "Confirmar", f"¿Eliminar {len(rows)} losas?") == QMessageBox.Yes:
            for row in rows:
                id_losa = int(self.tabla.item(row, 0).text())
                self.modelo.eliminar_losa(id_losa) # Nuevo método del modelo
            self.datos_modificados.emit()
            self.refrescar()

    def seleccionar_desde_tabla(self, item):
        row = item.row()
        id_losa = int(self.tabla.item(row, 0).text())
        if id_losa not in self.modelo.losas: return
        
        datos = self.modelo.losas[id_losa]
        self.id_losa.setValue(id_losa)
        self.nodos_ids.setText(", ".join(map(str, datos['nodos'])))
        
        idx_dist = self.combo_distribucion.findText(datos['distribucion'].capitalize())
        self.combo_distribucion.setCurrentIndex(idx_dist)
        
        if datos['distribucion'] == 'unidireccional' and datos['eje_uni']:
            idx_eje = self.combo_eje_uni.findText(datos['eje_uni'])
            self.combo_eje_uni.setCurrentIndex(idx_eje)
        
        self.espesor_losa.setValue(datos.get('espesor', 0.20))
        self.pe_losa.setValue(datos.get('peso_especifico', 24.0))

    def _marcar_cambios_en_tabla(self):
        self.btn_guardar_tabla.setEnabled(True)

    def _guardar_cambios_de_tabla(self):
        try:
            for row in range(self.tabla.rowCount()):
                id_losa = int(self.tabla.item(row, 0).text())
                nodos_str = self.tabla.item(row, 1).text()
                nodos_lista = self._parsear_ids(nodos_str)
                distribucion = self.tabla.item(row, 2).text().lower()
                eje_uni_item = self.tabla.item(row, 3)
                eje_uni = eje_uni_item.text() if eje_uni_item and eje_uni_item.text() != 'N/A' else None

                espesor_val = float(self.tabla.item(row, 4).text())
                pe_val = float(self.tabla.item(row, 5).text())
                if distribucion not in ['unidireccional', 'bidireccional']:
                    raise ValueError(f"Fila {row+1}: Tipo de distribución '{distribucion}' no válido. Usar 'unidireccional' o 'bidireccional'.")

                if distribucion == 'unidireccional' and eje_uni not in ['Global X', 'Global Y']:
                     raise ValueError(f"Fila {row+1}: Eje '{eje_uni}' no válido para distribución unidireccional.")

                self.modelo.actualizar_losa(id_losa, nodos_lista, distribucion, eje_uni, espesor_val, pe_val)

            self.btn_guardar_tabla.setEnabled(False)
            self.datos_modificados.emit()
            self.refrescar_visualizacion()
            QMessageBox.information(self, "Éxito", "Cambios en la tabla de losas guardados.")
        except (ValueError, TypeError) as e:
            QMessageBox.critical(self, "Error de Datos", f"Error al guardar los datos de la tabla.\n\nDetalle: {e}")
        except Exception as e:
            QMessageBox.critical(self, "Error Inesperado", f"Ocurrió un error: {e}")

    def editar_seleccion_lote(self):
        """
        Abre el nuevo diálogo de edición por lote para modificar
        distribución, espesor y/o PE de las losas seleccionadas.
        """
        
        items_seleccionados = self.tabla.selectedItems()
        if not items_seleccionados:
            QMessageBox.information(self, "Selección Vacía", "Debes seleccionar al menos una fila en la tabla de losas.")
            return

        filas_seleccionadas = sorted(list(set(item.row() for item in items_seleccionados)))
        ids_losas_a_modificar = []
        for fila in filas_seleccionadas:
            try:
                id_losa = int(self.tabla.item(fila, 0).text())
                ids_losas_a_modificar.append(id_losa)
            except Exception as e:
                print(f"Error al leer ID de losa en fila {fila}: {e}")
        
        if not ids_losas_a_modificar:
            QMessageBox.warning(self, "Error", "No se pudieron obtener los IDs de las losas seleccionadas.")
            return

        dialogo = DialogoEditarLosasLote(self)
        
        if dialogo.exec():
            valores = dialogo.get_valores_lote()

            if all(v is None for v in valores.values()):
                QMessageBox.information(self, "Sin Cambios", "No se seleccionó ninguna propiedad para modificar.")
                return
            
            try:
                num_actualizados = self.modelo.actualizar_propiedades_losas_lote(
                    ids_losas=ids_losas_a_modificar, 
                    distribucion=valores['distribucion'],
                    eje_uni=valores['eje_uni'],
                    espesor=valores['espesor'],
                    peso_especifico=valores['peso_especifico']
                )
                
                QMessageBox.information(self, "Éxito", 
                    f"{num_actualizados} losas han sido actualizadas."
                )

                self.refrescar() 
                self.datos_modificados.emit() 

            except ValueError as e:
                QMessageBox.critical(self, "Error en Asignación", str(e))
            except Exception as e:
                QMessageBox.critical(self, "Error Inesperado", f"Ocurrió un error: {e}")

    def refrescar(self):
        self.tabla.blockSignals(True)
        self.tabla.setRowCount(0)

        for i, (id_losa, datos) in enumerate(sorted(self.modelo.losas.items())):
            self.tabla.insertRow(i)
            nodos_str = ", ".join(map(str, datos['nodos']))
            eje_str = datos.get('eje_uni', 'N/A') or 'N/A'
            espesor_val = datos.get('espesor', 0.0)
            pe_val = datos.get('peso_especifico', 0.0)

            id_item = QTableWidgetItem(str(id_losa))
            id_item.setFlags(id_item.flags() & ~Qt.ItemIsEditable)
            self.tabla.setItem(i, 0, id_item)

            self.tabla.setItem(i, 1, QTableWidgetItem(nodos_str))
            self.tabla.setItem(i, 2, QTableWidgetItem(datos['distribucion'].capitalize()))
            self.tabla.setItem(i, 3, QTableWidgetItem(eje_str))
            self.tabla.setItem(i, 4, QTableWidgetItem(f"{espesor_val:.3f}"))
            self.tabla.setItem(i, 5, QTableWidgetItem(f"{pe_val:.2f}"))

        self.tabla.blockSignals(False)
        self.id_losa.setValue(self.modelo.get_siguiente_id(self.modelo.losas))
        self.btn_guardar_tabla.setEnabled(False)

class PestañaHipotesisDeCarga(PestañaBase):
    """Widget para definir y gestionar las hipótesis o casos de carga."""
    def __init__(self, modelo, gestor_visualizacion, ventana_principal):
        super().__init__(modelo, gestor_visualizacion, ventana_principal)
        
        layout = QVBoxLayout(self)
        grupo_form = QGroupBox("Definición de Hipótesis de Carga")
        layout.addWidget(grupo_form)
        
        layout_form = QFormLayout(grupo_form)
        layout_form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapAllRows)

        self.id_hipotesis = QSpinBox(minimum=1, maximum=9999)
        self.nombre_hipotesis = QLineEdit()
        self.nombre_hipotesis.setPlaceholderText("Ej: Carga Viva Oficinas")
        self.tipo_carga_combo = QComboBox()
        self.tipo_carga_combo.addItems(['D', 'L', 'Lr', 'W', 'E', 'S', 'R', 'H'])

        layout_form.addRow("ID Hipótesis:", self.id_hipotesis)
        layout_form.addRow("Nombre Descriptivo:", self.nombre_hipotesis)
        layout_form.addRow("Tipo de Carga:", self.tipo_carga_combo)

        botones_layout = QHBoxLayout()
        self.btn_agregar = QPushButton("Añadir/Actualizar")
        self.btn_eliminar = QPushButton("Eliminar Selección")
        botones_layout.addWidget(self.btn_agregar)
        botones_layout.addWidget(self.btn_eliminar)
        layout_form.addRow(botones_layout)

        self.tabla = QTableWidget(columnCount=3)
        self.tabla.setHorizontalHeaderLabels(["ID", "Nombre", "Tipo"])
        self.tabla.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tabla.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tabla.setEditTriggers(QAbstractItemView.NoEditTriggers) 
        layout.addWidget(self.tabla)
        
        self.btn_agregar.clicked.connect(self.agregar_o_actualizar)
        self.btn_eliminar.clicked.connect(self.eliminar)
        self.tabla.itemClicked.connect(self.seleccionar_desde_tabla)

    def agregar_o_actualizar(self):
        try:
            id_hip = self.id_hipotesis.value()
            nombre = self.nombre_hipotesis.text()
            tipo = self.tipo_carga_combo.currentText()
            
            if not nombre:
                raise ValueError("El nombre de la hipótesis no puede estar vacío.")

            if id_hip in self.modelo.hipotesis_de_carga:
                self.modelo.actualizar_hipotesis(id_hip, nombre, tipo)
            else:
                self.modelo.agregar_hipotesis(nombre, tipo)
            
            self.datos_modificados.emit() 
            self.refrescar()
        except ValueError as e:
            QMessageBox.warning(self, "Error de Datos", str(e))

    def eliminar(self):
        filas = self.tabla.selectionModel().selectedRows()
        if not filas: return
        
        respuesta = QMessageBox.question(self, "Confirmar", f"¿Eliminar {len(filas)} hipótesis y TODAS sus cargas asociadas?")
        if respuesta == QMessageBox.Yes:
            ids_a_eliminar = [int(self.tabla.item(fila.row(), 0).text()) for fila in filas]
            for id_hip in ids_a_eliminar:
                self.modelo.eliminar_hipotesis(id_hip)
            self.datos_modificados.emit()
            self.refrescar()

    def seleccionar_desde_tabla(self, item):
        fila = item.row()
        id_hip = int(self.tabla.item(fila, 0).text())
        datos = self.modelo.hipotesis_de_carga[id_hip]
        
        self.id_hipotesis.setValue(id_hip)
        self.nombre_hipotesis.setText(datos['nombre'])
        self.tipo_carga_combo.setCurrentText(datos['tipo'])

    def refrescar(self):
        self.tabla.setRowCount(0)
        for id_hip, datos in sorted(self.modelo.hipotesis_de_carga.items()):
            fila = self.tabla.rowCount()
            self.tabla.insertRow(fila)
            self.tabla.setItem(fila, 0, QTableWidgetItem(str(id_hip)))
            self.tabla.setItem(fila, 1, QTableWidgetItem(datos['nombre']))
            self.tabla.setItem(fila, 2, QTableWidgetItem(datos['tipo']))
        
        self.id_hipotesis.setValue(self.modelo.get_siguiente_id(self.modelo.hipotesis_de_carga))
        self.nombre_hipotesis.clear()
        self.tipo_carga_combo.setCurrentIndex(0)
            
class PestañaCombinaciones(PestañaBase):
    def __init__(self, modelo, gestor_visualizacion, ventana_principal):
        super().__init__(modelo, gestor_visualizacion, ventana_principal)
        
        layout = QVBoxLayout(self)
        grupo_form = QGroupBox("Añadir Combinación de Usuario"); layout.addWidget(grupo_form)
        
        layout_form = QFormLayout(grupo_form)
        layout_form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapAllRows)
        
        self.nombre_combo = QLineEdit("Usuario 1")
        layout_form.addRow("Nombre:", self.nombre_combo)

        
        self.filas_factores = []
        tipos_disponibles = ['Ninguno', 'D', 'L', 'Lr', 'W', 'E', 'S', 'R', 'H']
        
        for i in range(6):
            combo_tipo = QComboBox()
            combo_tipo.addItems(tipos_disponibles)
            
            spin_factor = QDoubleSpinBox(decimals=2, minimum=-10, maximum=10, value=0.0, singleStep=0.1)
            
            hbox = QHBoxLayout()
            hbox.addWidget(combo_tipo)
            hbox.addWidget(QLabel("Factor:"))
            hbox.addWidget(spin_factor)
            
            self.filas_factores.append((combo_tipo, spin_factor))
            layout_form.addRow(f"Término {i+1}:", hbox)

        self.btn_agregar = QPushButton("Añadir Combinación")
        layout_form.addRow(self.btn_agregar)
        
        botones_tabla_layout = QHBoxLayout()
        self.btn_eliminar = QPushButton("Eliminar Seleccionada")
        botones_tabla_layout.addWidget(self.btn_eliminar)
        layout.addLayout(botones_tabla_layout)

        self.btn_guardar_tabla = QPushButton("Guardar Cambios en Tabla")
        self.btn_guardar_tabla.setEnabled(False)
        layout.addWidget(self.btn_guardar_tabla)
        
        self.tabla = QTableWidget(columnCount=3); layout.addWidget(self.tabla)
        self.tabla.setHorizontalHeaderLabels(["Nombre", "Factores", "Tipo"])
        header = self.tabla.horizontalHeader()
        for i in range(self.tabla.columnCount()):
            header.setSectionResizeMode(i, QHeaderView.ResizeToContents)
        
        self.btn_agregar.clicked.connect(self.agregar)
        self.btn_eliminar.clicked.connect(self.eliminar)
        self.btn_guardar_tabla.clicked.connect(self._guardar_cambios_de_tabla)
        self.tabla.itemChanged.connect(self._marcar_cambios_en_tabla)
        
    def agregar(self):
        nombre = self.nombre_combo.text()
        if not nombre: 
            QMessageBox.warning(self, "Error", "El nombre no puede estar vacío.")
            return
            
        nombres_existentes = [c.nombre for c in self.modelo.combinaciones]
        if nombre in nombres_existentes: 
            QMessageBox.warning(self, "Error", f"La combinación '{nombre}' ya existe.")
            return

        factores = {}
        for combo, spin in self.filas_factores:
            tipo = combo.currentText()
            valor = spin.value()
            if tipo != 'Ninguno' and valor != 0.0:
                factores[tipo] = factores.get(tipo, 0.0) + valor
                
        if not factores: 
            QMessageBox.warning(self, "Error", "La combinación debe tener al menos un factor distinto de cero asociado a un tipo de carga.")
            return
            
        nueva_combo = CombinacionCarga(nombre, factores, 'Usuario')
        self.modelo.combinaciones.append(nueva_combo)
        self.modelo.modificado = True
        self.refrescar()

    def eliminar(self):
        fila_seleccionada = self.tabla.currentRow()
        if fila_seleccionada < 0: QMessageBox.information(self, "Información", "Seleccione una combinación para eliminar."); return
        nombre_a_eliminar = self.tabla.item(fila_seleccionada, 0).text()
        self.modelo.combinaciones = [c for c in self.modelo.combinaciones if c.nombre != nombre_a_eliminar]
        self.modelo.modificado = True
        self.refrescar()

    def _marcar_cambios_en_tabla(self): self.btn_guardar_tabla.setEnabled(True)

    def _guardar_cambios_de_tabla(self):
        try:
            nueva_lista_combinaciones = []
            nombres_vistos = set()
            for fila in range(self.tabla.rowCount()):
                nombre = self.tabla.item(fila, 0).text()
                factores_str = self.tabla.item(fila, 1).text()
                tipo = self.tabla.item(fila, 2).text()
                if not nombre: raise ValueError(f"El nombre en la fila {fila + 1} no puede estar vacío.")
                if nombre in nombres_vistos: raise ValueError(f"El nombre '{nombre}' está duplicado.")
                nombres_vistos.add(nombre)
                try:
                    factores = ast.literal_eval(factores_str)
                    if not isinstance(factores, dict): raise TypeError()
                except Exception: raise ValueError(f"Formato de factores en la fila {fila + 1} es inválido.")
                if tipo != 'Usuario':
                    combo_original = next((c for c in self.modelo.combinaciones if c.nombre == nombre), None)
                    if combo_original: nueva_lista_combinaciones.append(combo_original)
                    continue
                nueva_combo = CombinacionCarga(nombre, factores, tipo)
                nueva_lista_combinaciones.append(nueva_combo)
            combos_de_norma = [c for c in self.modelo.combinaciones if c.tipo != 'Usuario']
            combos_de_usuario_actualizadas = [c for c in nueva_lista_combinaciones if c.tipo == 'Usuario']
            self.modelo.combinaciones = combos_de_norma + combos_de_usuario_actualizadas
            self.modelo.modificado = True
            self.btn_guardar_tabla.setEnabled(False)
            self.refrescar()
            QMessageBox.information(self, "Éxito", "Cambios guardados correctamente.")
        except (ValueError, TypeError) as e:
            QMessageBox.critical(self, "Error de Datos", f"No se pudieron guardar los cambios.\n\nDetalle: {e}")
            self.refrescar()

    def refrescar(self):
        self.tabla.blockSignals(True)
        self.tabla.setRowCount(0)
        combos_norma = [c for c in self.modelo.combinaciones if c.tipo != 'Usuario']
        combos_usuario = [c for c in self.modelo.combinaciones if c.tipo == 'Usuario']
        for combo in combos_norma + combos_usuario:
            row = self.tabla.rowCount()
            self.tabla.insertRow(row)
            item_nombre = QTableWidgetItem(combo.nombre)
            item_factores = QTableWidgetItem(str(combo.factores))
            item_tipo = QTableWidgetItem(combo.tipo)
            if combo.tipo != 'Usuario':
                flags = item_nombre.flags() & ~Qt.ItemIsEditable
                item_nombre.setFlags(flags); item_factores.setFlags(flags); item_tipo.setFlags(flags)
            self.tabla.setItem(row, 0, item_nombre)
            self.tabla.setItem(row, 1, item_factores)
            self.tabla.setItem(row, 2, item_tipo)
        self.tabla.blockSignals(False)
        self.btn_guardar_tabla.setEnabled(False)

class PestañaCargas(PestañaBase):
    def __init__(self, modelo, gestor_visualizacion, ventana_principal):
        super().__init__(modelo, gestor_visualizacion, ventana_principal)
        
        layout = QVBoxLayout(self)
        grupo_form = QGroupBox("Definición de Cargas"); layout.addWidget(grupo_form)
        layout_form = QVBoxLayout(grupo_form)
        
        self.combo_tipo = QComboBox()
        self.combo_tipo.addItem("Carga Nodal", "nodal")
        self.combo_tipo.addItem("Carga en Elemento", "elemento")
        self.combo_tipo.addItem("Carga en Losa", "losa")
        layout_form.addWidget(self.combo_tipo)
        
        self.pila_formularios = QStackedWidget()
        self.form_nodal = self.crear_form_nodal()
        self.form_elemento = self.crear_form_elemento()
        self.form_losa = self.crear_form_losa()
        self.pila_formularios.addWidget(self.form_nodal)
        self.pila_formularios.addWidget(self.form_elemento)
        self.pila_formularios.addWidget(self.form_losa)
        layout_form.addWidget(self.pila_formularios)

        botones_layout = QHBoxLayout()
        self.btn_agregar = QPushButton("Añadir Carga")
        self.btn_eliminar = QPushButton("Eliminar Seleccionada")
        botones_layout.addWidget(self.btn_agregar)
        botones_layout.addWidget(self.btn_eliminar)
        layout_form.addLayout(botones_layout)
        
        self.tabla = QTableWidget(columnCount=4); layout.addWidget(self.tabla)
        self.tabla.setHorizontalHeaderLabels(["ID Carga", "Hipótesis", "Ubicación", "Valores"])
        header = self.tabla.horizontalHeader()
        for i in range(self.tabla.columnCount()):
            header.setSectionResizeMode(i, QHeaderView.ResizeToContents)
        self.tabla.setEditTriggers(QAbstractItemView.NoEditTriggers)
        
        self.combo_tipo.currentIndexChanged.connect(self.pila_formularios.setCurrentIndex)
        self.btn_agregar.clicked.connect(self.agregar)
        self.btn_eliminar.clicked.connect(self.eliminar)

    def crear_form_nodal(self):
        widget = QWidget(); layout = QFormLayout(widget)
        layout.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapAllRows)
        self.carga_nodo_id = QLineEdit(); self.carga_nodo_id.setPlaceholderText("Ej: 1, 3, 5")
        self.combo_hipotesis_nodal = QComboBox()
        
        controles_superiores = QHBoxLayout()
        controles_superiores.addWidget(QLabel("Nodo(s) ID:"))
        controles_superiores.addWidget(self.carga_nodo_id)
        controles_superiores.addWidget(QLabel("Asignar a Hipótesis:"))
        controles_superiores.addWidget(self.combo_hipotesis_nodal)
        layout.addRow(controles_superiores)

        self.fuerzas = [QDoubleSpinBox(decimals=3, minimum=-1e9, maximum=1e9) for _ in range(6)]
        labels = ["Fx", "Fy", "Fz", "Mx", "My", "Mz"]
        grid_fuerzas = QGridLayout()
        for i, (label, spinbox) in enumerate(zip(labels, self.fuerzas)):
            grid_fuerzas.addWidget(QLabel(label), i // 2, (i % 2) * 2)
            grid_fuerzas.addWidget(spinbox, i // 2, (i % 2) * 2 + 1)
        layout.addRow(grid_fuerzas)
        return widget
    
    def crear_form_elemento(self):
        widget = QWidget(); layout = QFormLayout(widget)
        layout.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapAllRows)
        self.carga_elem_id = QLineEdit(); self.carga_elem_id.setPlaceholderText("Ej: 2, 4, 6")
        self.combo_hipotesis_elem = QComboBox()

        controles_superiores = QHBoxLayout()
        controles_superiores.addWidget(QLabel("Elemento(s) ID:"))
        controles_superiores.addWidget(self.carga_elem_id)
        controles_superiores.addWidget(QLabel("Asignar a Hipótesis:"))
        controles_superiores.addWidget(self.combo_hipotesis_elem)
        layout.addRow(controles_superiores)

        self.cargas_dist = [QDoubleSpinBox(decimals=3, minimum=-1e9, maximum=1e9) for _ in range(4)]
        labels = ["wx", "wy", "wz", "mt"]
        for label, spinbox in zip(labels, self.cargas_dist):
            layout.addRow(label, spinbox)
        return widget
    
    def crear_form_losa(self):
        """Crea el widget del formulario para definir cargas superficiales en losas."""
        widget = QWidget()
        layout = QFormLayout(widget)
        layout.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapAllRows)

        self.combo_hipotesis_losa = QComboBox()
        self.id_losa_input = QLineEdit() 
        self.id_losa_input.setPlaceholderText("Ej: 1, 2, 4")

        
        self.wz_losa_input = QDoubleSpinBox(decimals=3, minimum=-1e9, maximum=1e9)
        self.wz_losa_input.setToolTip("Carga superficial en Z global (kN/m²). Un valor negativo es hacia abajo.")

        layout.addRow("Asignar a Hipótesis:", self.combo_hipotesis_losa)
        layout.addRow("ID(s) de Losa:", self.id_losa_input) 
        layout.addRow("Carga Superficial (wz) [kN/m²]:", self.wz_losa_input)

        advertencia = QLabel("Nota: La distribución es ideal para losas rectangulares/convexas\nsoportadas por vigas en su perímetro.")
        advertencia.setStyleSheet("font-style: italic; color: gray;")
        layout.addRow(advertencia)

        return widget

    def agregar(self):
        errores = []
        try:
            tipo_carga = self.combo_tipo.currentData()
            if tipo_carga == "nodal":
                id_hipotesis = self.combo_hipotesis_nodal.currentData()
                if id_hipotesis is None: raise ValueError("Debe seleccionar una hipótesis válida.")
                vector = [s.value() for s in self.fuerzas]
                ids_a_cargar = self._parsear_ids(self.carga_nodo_id.text())
                if not ids_a_cargar: raise ValueError("Entrada de IDs de nodo no válida.")
                for id_nodo in ids_a_cargar:
                    self.modelo.agregar_carga_nodal(id_nodo, id_hipotesis, vector)
            elif tipo_carga == "elemento":
                id_hipotesis = self.combo_hipotesis_elem.currentData()
                if id_hipotesis is None: raise ValueError("Debe seleccionar una hipótesis válida.")
                datos_carga = ("uniforme",) + tuple(s.value() for s in self.cargas_dist) 
                ids_a_cargar = self._parsear_ids(self.carga_elem_id.text())
                if not ids_a_cargar: raise ValueError("Entrada de IDs de elemento no válida.")
                for id_elem in ids_a_cargar:
                    self.modelo.agregar_carga_elemento(id_elem, id_hipotesis, datos_carga)
            elif tipo_carga == "losa":
                id_hipotesis = self.combo_hipotesis_losa.currentData()
                if id_hipotesis is None:
                    raise ValueError("Debe seleccionar una hipótesis válida.")

                wz = self.wz_losa_input.value()
                if abs(wz) < 1e-9:
                    raise ValueError("El valor de la carga no puede ser cero.")
                
                ids_losas_a_cargar = self._parsear_ids(self.id_losa_input.text())
                if not ids_losas_a_cargar:
                    raise ValueError("Entrada de IDs de losa no válida.")

                for id_losa in ids_losas_a_cargar:
                    self.modelo.agregar_o_actualizar_carga_superficial(
                        None,
                        id_losa, 
                        id_hipotesis, 
                        wz
                    )
            
            self.datos_modificados.emit()
            self.refrescar()
        except (ValueError, KeyError) as e:
             QMessageBox.warning(self, "Error de Entrada", str(e))
            
    def eliminar(self):
        filas_seleccionadas = sorted(list(set(item.row() for item in self.tabla.selectedItems())), reverse=True)
        
        if not filas_seleccionadas:
            QMessageBox.information(self, "Aviso", "Seleccione una o más cargas de la tabla para eliminar.")
            return

        # Pedimos confirmación al usuario
        respuesta = QMessageBox.question(self, "Confirmar Eliminación", 
                                         f"¿Está seguro de que desea eliminar {len(filas_seleccionadas)} carga(s) seleccionada(s)?",
                                         QMessageBox.Yes | QMessageBox.No)
        
        if respuesta == QMessageBox.Yes:
            for fila in filas_seleccionadas:
                datos_carga = self.tabla.item(fila, 0).data(Qt.UserRole)
                if not datos_carga: continue

                id_carga, tipo_carga = datos_carga 

                if tipo_carga == 'nodal' or tipo_carga == 'elemento':
                    self.modelo.eliminar_carga(id_carga) 
                elif tipo_carga == 'losa':
                    self.modelo.eliminar_carga_superficial(id_carga) 
            
            self.datos_modificados.emit()
            self.refrescar()

    def refrescar(self):
        hip_nodal_sel = self.combo_hipotesis_nodal.currentData()
        hip_elem_sel = self.combo_hipotesis_elem.currentData()
        hip_losa_sel = self.combo_hipotesis_losa.currentData()

        self.combo_hipotesis_nodal.clear()
        self.combo_hipotesis_elem.clear()
        if not self.modelo.hipotesis_de_carga:
            self.combo_hipotesis_nodal.addItem("Cree una hipótesis primero", None)
            self.combo_hipotesis_elem.addItem("Cree una hipótesis primero", None)
        else:
            for id_hip, datos in sorted(self.modelo.hipotesis_de_carga.items()):
                texto = f"{datos['nombre']} (Tipo: {datos['tipo']})"
                self.combo_hipotesis_nodal.addItem(texto, id_hip)
                self.combo_hipotesis_elem.addItem(texto, id_hip)

        if hip_nodal_sel is not None:
            idx_nodal = self.combo_hipotesis_nodal.findData(hip_nodal_sel)
            if idx_nodal >= 0: self.combo_hipotesis_nodal.setCurrentIndex(idx_nodal)
            
        if hip_elem_sel is not None:
            idx_elem = self.combo_hipotesis_elem.findData(hip_elem_sel)
            if idx_elem >= 0: self.combo_hipotesis_elem.setCurrentIndex(idx_elem)

        self.tabla.blockSignals(True)
        self.tabla.setRowCount(0)
        self.tabla.setHorizontalHeaderLabels(["ID Carga", "Hipótesis", "Ubicación", "Valores"])
        
        def formatear_vector(vector, prefijos):
            return ", ".join([f"{p}: {v:.2f}" for p, v in zip(prefijos, vector) if abs(v) > 1e-6])

        for carga in self.modelo.cargas_nodales:
            fila = self.tabla.rowCount()
            self.tabla.insertRow(fila)
            
            id_carga_item = QTableWidgetItem(str(carga['id_carga']))
            id_carga_item.setData(Qt.UserRole, (carga['id_carga'], 'nodal'))
            
            nombre_hipotesis = self.modelo.hipotesis_de_carga.get(carga['id_hipotesis'], {}).get('nombre', 'DESCONOCIDA')
            
            prefijos_nodal = ["Fx", "Fy", "Fz", "Mx", "My", "Mz"]
            valores_str = formatear_vector(carga['vector'], prefijos_nodal)

            self.tabla.setItem(fila, 0, id_carga_item)
            self.tabla.setItem(fila, 1, QTableWidgetItem(nombre_hipotesis))
            self.tabla.setItem(fila, 2, QTableWidgetItem(f"Nodo {carga['id_nodo']}"))
            self.tabla.setItem(fila, 3, QTableWidgetItem(valores_str))

        for carga in self.modelo.cargas_elementos:
            fila = self.tabla.rowCount()
            self.tabla.insertRow(fila)

            id_carga_item = QTableWidgetItem(str(carga['id_carga']))
            id_carga_item.setData(Qt.UserRole, (carga['id_carga'], 'elemento'))

            nombre_hipotesis = self.modelo.hipotesis_de_carga.get(carga['id_hipotesis'], {}).get('nombre', 'DESCONOCIDA')
            
            prefijos_dist = ["wx", "wy", "wz", "mt"]
            valores_str = formatear_vector(carga['datos_carga'][1:], prefijos_dist)

            self.tabla.setItem(fila, 0, id_carga_item)
            self.tabla.setItem(fila, 1, QTableWidgetItem(nombre_hipotesis))
            self.tabla.setItem(fila, 2, QTableWidgetItem(f"Elem {carga['id_elemento']}"))
            self.tabla.setItem(fila, 3, QTableWidgetItem(valores_str))

        for id_carga_sup, carga in self.modelo.cargas_superficiales.items():
            fila = self.tabla.rowCount()
            self.tabla.insertRow(fila)

            id_carga_item = QTableWidgetItem(str(id_carga_sup))
            id_carga_item.setData(Qt.UserRole, (id_carga_sup, 'losa')) # <-- Almacenar tupla

            nombre_hipotesis = self.modelo.hipotesis_de_carga.get(carga['id_hipotesis'], {}).get('nombre', 'DESCONOCIDA')
            valores_str = f"wz: {carga['magnitud']:.2f} kN/m²"

            self.tabla.setItem(fila, 0, id_carga_item)
            self.tabla.setItem(fila, 1, QTableWidgetItem(nombre_hipotesis))
            self.tabla.setItem(fila, 2, QTableWidgetItem(f"Losa {carga['id_losa']}"))
            self.tabla.setItem(fila, 3, QTableWidgetItem(valores_str))

        self.combo_hipotesis_losa.clear()
        if not self.modelo.hipotesis_de_carga:
            self.combo_hipotesis_losa.addItem("Cree una hipótesis primero", None)
        else:
            for id_hip, datos in sorted(self.modelo.hipotesis_de_carga.items()):
                texto = f"{datos['nombre']} (Tipo: {datos['tipo']})"
                self.combo_hipotesis_losa.addItem(texto, id_hip)

        if hip_losa_sel is not None:
            idx_losa = self.combo_hipotesis_losa.findData(hip_losa_sel)
            if idx_losa >= 0: self.combo_hipotesis_losa.setCurrentIndex(idx_losa)

        self.tabla.resizeColumnsToContents()
        self.tabla.blockSignals(False)
        
class PestañaApoyos(PestañaBase):
    def __init__(self, modelo, gestor_visualizacion, ventana_principal):
        super().__init__(modelo, gestor_visualizacion, ventana_principal)
        
        layout = QVBoxLayout(self)
        grupo_form = QGroupBox("Definición de Apoyos"); layout.addWidget(grupo_form)
        layout_form = QFormLayout(grupo_form)
        layout_form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapAllRows)

        self.nodo_apoyo = QLineEdit(); self.nodo_apoyo.setPlaceholderText("Ej: 1, 3, 5")
        layout_form.addRow("Nodo(s):", self.nodo_apoyo)

        grid_checks = QGridLayout()
        self.checks = [QCheckBox(f"Restringir {axis}") for axis in ["X", "Y", "Z", "RX", "RY", "RZ"]]
        for i, check in enumerate(self.checks):
            grid_checks.addWidget(check, i // 2, i % 2)
        layout_form.addRow(grid_checks)

        botones_layout = QHBoxLayout()
        self.btn_agregar = QPushButton("Añadir/Actualizar")
        self.btn_eliminar = QPushButton("Eliminar Apoyo")
        botones_layout.addWidget(self.btn_agregar); botones_layout.addWidget(self.btn_eliminar)
        layout_form.addRow(botones_layout)
        
        self.btn_guardar_tabla = QPushButton("Guardar Cambios en Tabla")
        self.btn_guardar_tabla.setEnabled(False)
        layout.addWidget(self.btn_guardar_tabla)

        self.tabla = QTableWidget(columnCount=7); layout.addWidget(self.tabla)
        self.tabla.setHorizontalHeaderLabels(["Nodo", "Tx", "Ty", "Tz", "Rx", "Ry", "Rz"])
        self.tabla.setSelectionBehavior(QAbstractItemView.SelectRows)
        header = self.tabla.horizontalHeader()
        for i in range(self.tabla.columnCount()):
            header.setSectionResizeMode(i, QHeaderView.ResizeToContents)
        
        self.btn_agregar.clicked.connect(self.agregar)
        self.btn_eliminar.clicked.connect(self.eliminar)
        self.btn_guardar_tabla.clicked.connect(self._guardar_cambios_de_tabla)
        self.tabla.itemClicked.connect(self.seleccionar_desde_tabla)

    def agregar(self):
        errores = []
        try:
            ids_a_apoyar = self._parsear_ids(self.nodo_apoyo.text())
            if not ids_a_apoyar: raise ValueError("Entrada de IDs de nodo no válida.")
            restricciones = [check.isChecked() for check in self.checks]
            for id_nodo in ids_a_apoyar:
                try: self.modelo.agregar_o_actualizar_apoyo(id_nodo, restricciones)
                except ValueError as e: errores.append(str(e))
            if errores: QMessageBox.warning(self, "Errores al Agregar", "\n".join(errores))
            self.datos_modificados.emit()
            self.refrescar()
        except ValueError as e: QMessageBox.warning(self, "Error de Entrada", str(e))
    
    def eliminar(self):
        rows = sorted(list({item.row() for item in self.tabla.selectedItems()}), reverse=True)
        if not rows: return
        if QMessageBox.question(self, "Confirmar", f"¿Eliminar {len(rows)} apoyos?") == QMessageBox.Yes:
            for row in rows:
                id_nodo = int(self.tabla.item(row, 0).text())
                self.modelo.eliminar_apoyo(id_nodo)
            self.datos_modificados.emit()
            self.refrescar()

    def seleccionar_desde_tabla(self, item):
        row = item.row()
        id_nodo = int(self.tabla.item(row, 0).text())
        if id_nodo in self.modelo.apoyos:
            self.nodo_apoyo.setText(str(id_nodo))
            restricciones = self.modelo.apoyos[id_nodo]
            for check, is_checked in zip(self.checks, restricciones):
                check.setChecked(is_checked)

    def _guardar_cambios_de_tabla(self):
        try:
            for row in range(self.tabla.rowCount()):
                id_nodo = int(self.tabla.item(row, 0).text())
                restricciones = []
                for col in range(1, 7):
                    container_widget = self.tabla.cellWidget(row, col)
                    if container_widget:              
                        checkbox = container_widget.findChild(QCheckBox)
                        if checkbox: restricciones.append(checkbox.isChecked())
                        else: restricciones.append(False) 
                self.modelo.agregar_o_actualizar_apoyo(id_nodo, restricciones)
            self.btn_guardar_tabla.setEnabled(False)
            self.datos_modificados.emit()
            self.refrescar_visualizacion()
        except Exception as e: QMessageBox.critical(self, "Error Inesperado", f"Ocurrió un error al guardar: {e}")

    def refrescar(self):
        self.tabla.blockSignals(True)
        self.tabla.setRowCount(len(self.modelo.apoyos))
        for i, (id_nodo, restr) in enumerate(sorted(self.modelo.apoyos.items())):
            id_item = QTableWidgetItem(str(id_nodo)); id_item.setFlags(id_item.flags() & ~Qt.ItemIsEditable)
            self.tabla.setItem(i, 0, id_item)
            for j, es_restringido in enumerate(restr):
                checkbox = QCheckBox(); checkbox.setChecked(es_restringido)
                cell_widget = QWidget(); layout = QHBoxLayout(cell_widget)
                layout.addWidget(checkbox); layout.setAlignment(Qt.AlignCenter); layout.setContentsMargins(0,0,0,0)
                checkbox.stateChanged.connect(lambda: self.btn_guardar_tabla.setEnabled(True))
                self.tabla.setCellWidget(i, j + 1, cell_widget)
        self.tabla.blockSignals(False)
        self.btn_guardar_tabla.setEnabled(False)

class DialogoConfiguracionCortes(QDialog):
    """
    Diálogo modal para configurar los límites de visualización (Cortes) en los ejes X, Y y Z.
    """
    def __init__(self, limites_actuales, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configuración de Cortes de Vista")
        self.setMinimumWidth(300)
        
        layout = QVBoxLayout(self)
        
        # Grupo de controles
        grupo = QGroupBox("Límites de Visualización")
        layout_form = QFormLayout(grupo)
        
        # Rango grande por defecto para no limitar innecesariamente
        RANGO_MIN = -1e6
        RANGO_MAX = 1e6
        
        # --- Eje X ---
        self.spin_x_min = QDoubleSpinBox(); self.spin_x_min.setRange(RANGO_MIN, RANGO_MAX)
        self.spin_x_max = QDoubleSpinBox(); self.spin_x_max.setRange(RANGO_MIN, RANGO_MAX)
        self.spin_x_min.setValue(limites_actuales.get('x_min', -100.0))
        self.spin_x_max.setValue(limites_actuales.get('x_max', 100.0))
        
        layout_x = QHBoxLayout()
        layout_x.addWidget(QLabel("Min:")); layout_x.addWidget(self.spin_x_min)
        layout_x.addWidget(QLabel("Max:")); layout_x.addWidget(self.spin_x_max)
        layout_form.addRow("Corte en X:", layout_x)
        
        # --- Eje Y ---
        self.spin_y_min = QDoubleSpinBox(); self.spin_y_min.setRange(RANGO_MIN, RANGO_MAX)
        self.spin_y_max = QDoubleSpinBox(); self.spin_y_max.setRange(RANGO_MIN, RANGO_MAX)
        self.spin_y_min.setValue(limites_actuales.get('y_min', -100.0))
        self.spin_y_max.setValue(limites_actuales.get('y_max', 100.0))
        
        layout_y = QHBoxLayout()
        layout_y.addWidget(QLabel("Min:")); layout_y.addWidget(self.spin_y_min)
        layout_y.addWidget(QLabel("Max:")); layout_y.addWidget(self.spin_y_max)
        layout_form.addRow("Corte en Y:", layout_y)
        
        # --- Eje Z ---
        self.spin_z_min = QDoubleSpinBox(); self.spin_z_min.setRange(RANGO_MIN, RANGO_MAX)
        self.spin_z_max = QDoubleSpinBox(); self.spin_z_max.setRange(RANGO_MIN, RANGO_MAX)
        self.spin_z_min.setValue(limites_actuales.get('z_min', 0.0))
        self.spin_z_max.setValue(limites_actuales.get('z_max', 1000.0))
        
        layout_z = QHBoxLayout()
        layout_z.addWidget(QLabel("Min:")); layout_z.addWidget(self.spin_z_min)
        layout_z.addWidget(QLabel("Max:")); layout_z.addWidget(self.spin_z_max)
        layout_form.addRow("Corte en Z:", layout_z)
        
        layout.addWidget(grupo)
        
        # Botones estándar
        botones = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        botones.accepted.connect(self.accept)
        botones.rejected.connect(self.reject)
        layout.addWidget(botones)
        
    def obtener_limites(self):
        """Devuelve un diccionario con los nuevos límites configurados."""
        return {
            'x_min': self.spin_x_min.value(), 'x_max': self.spin_x_max.value(),
            'y_min': self.spin_y_min.value(), 'y_max': self.spin_y_max.value(),
            'z_min': self.spin_z_min.value(), 'z_max': self.spin_z_max.value()
        }

class PestañaResultados(QWidget):
    def __init__(self):
        super().__init__()
        self.modelo = None
        self.resultados_completos = None
        
        layout_principal = QVBoxLayout(self)
        splitter = QSplitter(Qt.Vertical)
        layout_principal.addWidget(splitter)

        # --- Panel Superior: Desplazamientos y Reacciones ---
        panel_superior = QWidget()
        layout_superior = QVBoxLayout(panel_superior)
        
        controles_layout = QGridLayout()
        controles_layout.addWidget(QLabel("Combinación:"), 0, 0)
        self.combo_combinaciones = QComboBox()
        controles_layout.addWidget(self.combo_combinaciones, 0, 1)
        
        controles_layout.addWidget(QLabel("Caso de Análisis:"), 1, 0)
        self.combo_sub_casos = QComboBox()
        controles_layout.addWidget(self.combo_sub_casos, 1, 1)
        
        layout_superior.addLayout(controles_layout)

        self.texto_resultados_nodales = QTextEdit()
        self.texto_resultados_nodales.setReadOnly(True)
        self.texto_resultados_nodales.setFont(QFont("Consolas, Courier New, monospace", 9))
        self.texto_resultados_nodales.setLineWrapMode(QTextEdit.NoWrap)
        layout_superior.addWidget(self.texto_resultados_nodales)
        
        splitter.addWidget(panel_superior)

        # --- Panel Inferior: Fuerzas Internas ---
        panel_inferior = QWidget()
        layout_inferior = QVBoxLayout(panel_inferior)
        
        controles_fuerzas_layout = QHBoxLayout()
        controles_fuerzas_layout.addWidget(QLabel("Fuerzas internas para el elemento:"))
        self.combo_elementos = QComboBox()
        controles_fuerzas_layout.addWidget(self.combo_elementos)
        layout_inferior.addLayout(controles_fuerzas_layout)
        
        self.texto_fuerzas_internas = QTextEdit()
        self.texto_fuerzas_internas.setReadOnly(True)
        self.texto_fuerzas_internas.setFont(QFont("Consolas, Courier New, monospace", 9))
        self.texto_fuerzas_internas.setLineWrapMode(QTextEdit.NoWrap)
        layout_inferior.addWidget(self.texto_fuerzas_internas)
        
        splitter.addWidget(panel_inferior)
        splitter.setSizes([400, 300]) 

        # --- Conexiones de Señales ---
        self.combo_combinaciones.currentIndexChanged.connect(self._actualizar_combo_sub_casos)
        self.combo_sub_casos.currentIndexChanged.connect(self.actualizar_tablas_resultados)
        self.combo_elementos.currentIndexChanged.connect(self.actualizar_tablas_resultados)

    def actualizar(self, modelo, resultados_por_combinacion):
        """Punto de entrada para actualizar la pestaña con nuevos resultados."""
        self.modelo = modelo
        self.resultados_completos = resultados_por_combinacion
        
        self.combo_elementos.blockSignals(True)
        self.combo_elementos.clear()
        if self.modelo and self.modelo.elementos:
            for id_elem in sorted(self.modelo.elementos.keys()):
                self.combo_elementos.addItem(f"Elemento {id_elem}", id_elem)
        self.combo_elementos.blockSignals(False)

        self.combo_combinaciones.blockSignals(True)
        self.combo_combinaciones.clear()
        if self.resultados_completos:
            todas_las_claves = self.resultados_completos.keys()
            nombres_combos = sorted(todas_las_claves, 
                                    key=lambda nombre: (nombre != 'Cálculo Simple', nombre))
            self.combo_combinaciones.addItems(nombres_combos)
        self.combo_combinaciones.blockSignals(False)
        
        self._actualizar_combo_sub_casos()

    def _actualizar_combo_sub_casos(self):
        """Puebla el segundo ComboBox basado en la selección del primero."""
        self.combo_sub_casos.blockSignals(True)
        self.combo_sub_casos.clear()
        
        nombre_combo_sel = self.combo_combinaciones.currentText()
        if not nombre_combo_sel or not self.resultados_completos:
            self.combo_sub_casos.blockSignals(False)
            self.actualizar_tablas_resultados()
            return

        sub_resultados = self.resultados_completos.get(nombre_combo_sel, {})
        
        nombres_sub_casos = sorted(sub_resultados.keys())
        for nombre in nombres_sub_casos:
            self.combo_sub_casos.addItem(nombre, nombre)
            
        self.combo_sub_casos.blockSignals(False)
        if self.combo_sub_casos.count() > 0:
            self.actualizar_tablas_resultados()

    def actualizar_tablas_resultados(self):
        """Muestra los resultados para el caso de análisis específico seleccionado."""
        if not self.modelo or not self.resultados_completos:
            self.texto_resultados_nodales.clear()
            self.texto_fuerzas_internas.clear()
            return

        nombre_combo = self.combo_combinaciones.currentText()
        clave_sub_caso = self.combo_sub_casos.currentData()
        
        if not nombre_combo or not clave_sub_caso:
            self.texto_resultados_nodales.clear()
            self.texto_fuerzas_internas.clear()
            return

        sub_resultados = self.resultados_completos.get(nombre_combo, {})
        resultados_caso = sub_resultados.get(clave_sub_caso)

        if not resultados_caso:
            self.texto_resultados_nodales.clear()
            self.texto_fuerzas_internas.clear()
            return

        texto_nodal = []
        desplazamientos = resultados_caso.get('desplazamientos')
        reacciones = resultados_caso.get('reacciones')

        texto_nodal.append(f"--- Desplazamientos (Globales) para '{clave_sub_caso}' ---")
        texto_nodal.append(f"{'Nodo':<6}{'Ux':>12}{'Uy':>12}{'Uz':>12}{'Rx':>12}{'Ry':>12}{'Rz':>12}")
        texto_nodal.append("-" * 78)
        if desplazamientos is not None:
            for id_nodo in sorted(self.modelo.nodos.keys()):
                idx = (id_nodo - 1) * 6
                d = desplazamientos[idx:idx+6]
                if np.any(np.abs(d) > 1e-9):
                    texto_nodal.append(f"{id_nodo:<6}{d[0]:>12.4e}{d[1]:>12.4e}{d[2]:>12.4e}{d[3]:>12.4e}{d[4]:>12.4e}{d[5]:>12.4e}")
        
        texto_nodal.append("\n\n--- Reacciones en Apoyos (Globales) ---")
        texto_nodal.append(f"{'Nodo':<6}{'Fx':>12}{'Fy':>12}{'Fz':>12}{'Mx':>12}{'My':>12}{'Mz':>12}")
        texto_nodal.append("-" * 78)
        if reacciones is not None:
             for id_nodo in sorted(self.modelo.apoyos.keys()):
                idx = (id_nodo - 1) * 6
                r = reacciones[idx:idx+6]
                if np.any(np.abs(r) > 1e-9): 
                    texto_nodal.append(f"{id_nodo:<6}{r[0]:>12.4f}{r[1]:>12.4f}{r[2]:>12.4f}{r[3]:>12.4f}{r[4]:>12.4f}{r[5]:>12.4f}")
        
        self.texto_resultados_nodales.setText("\n".join(texto_nodal))

        texto_fuerzas = []
        fuerzas_internas = resultados_caso.get('fuerzas_internas')
        id_elem_seleccionado = self.combo_elementos.currentData()

        if fuerzas_internas and id_elem_seleccionado in fuerzas_internas:
            f_local = fuerzas_internas[id_elem_seleccionado]
            texto_fuerzas.append(f"Fuerzas Internas para Elemento {id_elem_seleccionado} (Locales)")
            texto_fuerzas.append("-" * 60)
            texto_fuerzas.append(f"{'Componente':<15}{'Nodo I (Inicio)':>20}{'Nodo J (Fin)':>20}")
            texto_fuerzas.append("-" * 60)
            labels = ["Px (Axial)", "Py (Cortante)", "Pz (Cortante)", "Mx (Torsión)", "My (Momento)", "Mz (Momento)"]
            for i, label in enumerate(labels):
                texto_fuerzas.append(f"{label:<15}{f_local[i]:>20.4f}{f_local[i+6]:>20.4f}")
        else:
            texto_fuerzas.append("Seleccione un elemento para ver sus fuerzas internas.")
        
        self.texto_fuerzas_internas.setText("\n".join(texto_fuerzas))

class DialogoOpcionesAvanzadasReporte(QDialog):
    def __init__(self, config_actual=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Opciones Avanzadas del Reporte")
        self.setMinimumWidth(400)
        
        self.opciones = config_actual if config_actual else self._get_defaults()

        layout_principal = QVBoxLayout(self)

        # --- Grupo Detalles de Cálculo ---
        grupo_detalles = QGroupBox("Detalles del Proceso de Cálculo")
        layout_detalles = QGridLayout(grupo_detalles)
        
        self.cb_logs_ensamblaje = QCheckBox("Mostrar Logs de Ensamblaje")
        self.cb_matrices_locales = QCheckBox("Mostrar Matrices Locales/Transformación")
        self.cb_k_reducida_completa = QCheckBox("Mostrar K_reducida y F_reducido Completos")
        
        layout_detalles.addWidget(self.cb_logs_ensamblaje, 0, 0)
        layout_detalles.addWidget(self.cb_matrices_locales, 1, 0)
        layout_detalles.addWidget(self.cb_k_reducida_completa, 2, 0)
        
        layout_principal.addWidget(grupo_detalles)

        # --- Grupo Vectores de Resultados ---
        grupo_vectores = QGroupBox("Vectores de Resultados Completos (Datos Crudos)")
        layout_vectores = QGridLayout(grupo_vectores)
        
        self.cb_vectores_desplazamiento = QCheckBox("Mostrar Vectores de Desplazamiento Completos")
        self.cb_vectores_reacciones = QCheckBox("Mostrar Vectores de Reacciones Completos")
        self.cb_detalle_fuerzas_todas = QCheckBox("Mostrar Detalle Fuerzas Internas (Todos Elementos/Casos)")

        layout_vectores.addWidget(self.cb_vectores_desplazamiento, 0, 0)
        layout_vectores.addWidget(self.cb_vectores_reacciones, 1, 0)
        layout_vectores.addWidget(self.cb_detalle_fuerzas_todas, 2, 0)
        
        layout_principal.addWidget(grupo_vectores)
        
        # --- Grupo Matrices Globales ---
        grupo_matrices_globales = QGroupBox("Visualización de Matrices Globales")
        layout_matrices = QVBoxLayout(grupo_matrices_globales)
        
        self.rb_kglobal_no = QRadioButton("No mostrar K_global")
        self.rb_kglobal_diag = QRadioButton("Mostrar Resumen Diagonal K_global")
        self.rb_kglobal_completa = QRadioButton("Mostrar K_global Completa (¡Advertencia: Grande!)")
        
        layout_matrices.addWidget(self.rb_kglobal_no)
        layout_matrices.addWidget(self.rb_kglobal_diag)
        layout_matrices.addWidget(self.rb_kglobal_completa)
        
        self.rb_kglobal_diag.setChecked(True)
        
        layout_principal.addWidget(grupo_matrices_globales)
        
        # --- Recordar añadir un Filtro por Elementos ---
        # Este mostrará los detalles completos solo de los elementos seleccionados.
        # Considerar métodos de entrada eficientes para seleccionar varios elementos
        # de la misma forma en la que se seleccionan las páginas para imprimir
        # Ejemplo: 1-10, 15, 17-19 (del elemento 1 al 10, el 15 y del 17 al 19)

        botones = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        botones.accepted.connect(self._guardar_opciones)
        botones.rejected.connect(self.reject)
        layout_principal.addWidget(botones)

        self._cargar_opciones_actuales()

    def _get_defaults(self):
        # Define los valores por defecto si no se pasa config_actual
        return {
            'mostrar_logs_ensamblaje': False,
            'mostrar_matrices_locales': False,
            'mostrar_k_reducida_completa': False,
            'mostrar_vectores_desplazamiento': False,
            'mostrar_vectores_reacciones': False,
            'mostrar_detalle_fuerzas_todas': False,
            'mostrar_kglobal': 'diagonal', 
            # añadir 'filtro_elementos_ids'
        }

    def _cargar_opciones_actuales(self):
        # Carga el estado de los checkboxes/radiobuttons desde self.opciones
        self.cb_logs_ensamblaje.setChecked(self.opciones.get('mostrar_logs_ensamblaje', False))
        self.cb_matrices_locales.setChecked(self.opciones.get('mostrar_matrices_locales', False))
        self.cb_k_reducida_completa.setChecked(self.opciones.get('mostrar_k_reducida_completa', False))
        self.cb_vectores_desplazamiento.setChecked(self.opciones.get('mostrar_vectores_desplazamiento', False))
        self.cb_vectores_reacciones.setChecked(self.opciones.get('mostrar_vectores_reacciones', False))
        self.cb_detalle_fuerzas_todas.setChecked(self.opciones.get('mostrar_detalle_fuerzas_todas', False))
        
        kglobal_opt = self.opciones.get('mostrar_kglobal', 'diagonal')
        if kglobal_opt == 'no': self.rb_kglobal_no.setChecked(True)
        elif kglobal_opt == 'completa': self.rb_kglobal_completa.setChecked(True)
        else: self.rb_kglobal_diag.setChecked(True) # Default a diagonal
        
        # Cargar filtro de elementos

    def _guardar_opciones(self):
        # Guarda el estado actual de los controles en self.opciones
        self.opciones['mostrar_logs_ensamblaje'] = self.cb_logs_ensamblaje.isChecked()
        self.opciones['mostrar_matrices_locales'] = self.cb_matrices_locales.isChecked()
        self.opciones['mostrar_k_reducida_completa'] = self.cb_k_reducida_completa.isChecked()
        self.opciones['mostrar_vectores_desplazamiento'] = self.cb_vectores_desplazamiento.isChecked()
        self.opciones['mostrar_vectores_reacciones'] = self.cb_vectores_reacciones.isChecked()
        self.opciones['mostrar_detalle_fuerzas_todas'] = self.cb_detalle_fuerzas_todas.isChecked()
        
        if self.rb_kglobal_no.isChecked(): self.opciones['mostrar_kglobal'] = 'no'
        elif self.rb_kglobal_completa.isChecked(): self.opciones['mostrar_kglobal'] = 'completa'
        else: self.opciones['mostrar_kglobal'] = 'diagonal'

        self.accept()

    def get_opciones_avanzadas(self):
        return self.opciones

class DialogoConfigReporte(QDialog):
    def __init__(self, resultados_calculo, config_avanzada_actual=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configurar Reporte de Cálculo")
        self.setMinimumSize(600, 500)
        
        self.resultados = resultados_calculo if resultados_calculo else {}
        self.config_avanzada = config_avanzada_actual if config_avanzada_actual else {} # Guardará las opciones del otro diálogo

        layout_principal = QVBoxLayout(self)

        # --- Grupo Selección Combinaciones/Casos ---
        grupo_combos = QGroupBox("Seleccionar Combinaciones y Casos a Incluir")
        layout_combos = QVBoxLayout(grupo_combos)
        layout_botones_sel = QHBoxLayout()
        self.btn_sel_todo = QPushButton("Seleccionar Todo")
        self.btn_sel_ninguno = QPushButton("Ninguno")
        
        layout_botones_sel.addWidget(self.btn_sel_todo)
        layout_botones_sel.addWidget(self.btn_sel_ninguno)
        layout_botones_sel.addStretch() 
        layout_combos.addLayout(layout_botones_sel)

        self.arbol_combos = QTreeWidget()
        
        self.btn_sel_todo.clicked.connect(self._seleccionar_todo_arbol)
        self.btn_sel_ninguno.clicked.connect(self._deseleccionar_todo_arbol)

        self.arbol_combos.setHeaderLabel("Combinaciones / Casos")
        self.arbol_combos.header().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.poblar_arbol_combinaciones()
        
        layout_combos.addWidget(self.arbol_combos)
        layout_principal.addWidget(grupo_combos)

        # --- Grupo Elementos Específicos ---
        self.grupo_elementos = QGroupBox("Seleccionar Elementos de Interés")
        layout_elem = QVBoxLayout(self.grupo_elementos)

        self.check_todos_elem = QCheckBox("Todos")
        self.check_todos_elem.setChecked(True)

        layout_input_elem = QHBoxLayout()
        self.label_elem = QLabel("Elementos:")
        self.input_elem = QLineEdit()
        self.input_elem.setPlaceholderText("Ej: 1-5,9,12-17")
        self.input_elem.setEnabled(False) # Desactivado por defecto, ya que "Todos" inicia activado

        layout_input_elem.addWidget(self.label_elem)
        layout_input_elem.addWidget(self.input_elem)

        layout_elem.addWidget(self.check_todos_elem)
        layout_elem.addLayout(layout_input_elem)

        self.check_todos_elem.stateChanged.connect(
            lambda state: self.input_elem.setEnabled(not bool(state))
        )
        
        layout_principal.addWidget(self.grupo_elementos)

        # --- Grupo Secciones Principales ---
        grupo_secciones = QGroupBox("Secciones Principales del Reporte")
        layout_secciones = QGridLayout(grupo_secciones)
        
        # Defaults 
        self.cb_datos_entrada = QCheckBox("Datos de Entrada (Nodos, Elem, Mat, etc.)")
        self.cb_datos_entrada.setChecked(True); self.cb_datos_entrada.setEnabled(False) # Siempre incluido
        self.cb_proc_losas = QCheckBox("Procesamiento Cargas de Losa")
        self.cb_proc_losas.setChecked(True)
        self.cb_analisis_mat = QCheckBox("Análisis Matricial (Resumen Ensamblaje)")
        self.cb_analisis_mat.setChecked(True)
        self.cb_resolucion = QCheckBox("Resolución (Desplazamientos y Reacciones)")
        self.cb_resolucion.setChecked(True)
        self.cb_fuerzas_int = QCheckBox("Fuerzas Internas (Envolventes por Elemento)")
        self.cb_fuerzas_int.setChecked(True)
        self.cb_resumen_max = QCheckBox("Resumen de Máximos Globales (Envolvente)")
        self.cb_resumen_max.setChecked(True)

        layout_secciones.addWidget(self.cb_datos_entrada, 0, 0)
        layout_secciones.addWidget(self.cb_proc_losas, 1, 0)
        layout_secciones.addWidget(self.cb_analisis_mat, 2, 0)
        layout_secciones.addWidget(self.cb_resolucion, 0, 1)
        layout_secciones.addWidget(self.cb_fuerzas_int, 1, 1)
        layout_secciones.addWidget(self.cb_resumen_max, 2, 1)
        
        layout_principal.addWidget(grupo_secciones)

        # --- Botón Opciones Avanzadas ---
        self.btn_opciones_avanzadas = QPushButton("Opciones Avanzadas...")
        self.btn_opciones_avanzadas.clicked.connect(self._abrir_dialogo_avanzado)
        layout_principal.addWidget(self.btn_opciones_avanzadas, alignment=Qt.AlignLeft)

        # --- Botones Generar/Cancelar ---
        botones = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        botones.button(QDialogButtonBox.Ok).setText("Generar Reporte")
        botones.accepted.connect(self.accept)
        botones.rejected.connect(self.reject)
        layout_principal.addWidget(botones)

    def poblar_arbol_combinaciones(self):
        self.arbol_combos.clear()
        claves_combos = sorted([k for k in self.resultados.keys() if k != 'reporte_global_data'])

        for nombre_combo in claves_combos:
            item_combo = QTreeWidgetItem(self.arbol_combos, [nombre_combo])
            item_combo.setFlags(item_combo.flags() | Qt.ItemIsUserCheckable)
            item_combo.setCheckState(0, Qt.Checked) # Marcado por defecto

            sub_casos = self.resultados.get(nombre_combo, {})
            nombres_sub_casos = sorted(sub_casos.keys())
            
            for nombre_caso in nombres_sub_casos:
                item_caso = QTreeWidgetItem(item_combo, [nombre_caso])
                item_caso.setFlags(item_caso.flags() | Qt.ItemIsUserCheckable)
                item_caso.setCheckState(0, Qt.Checked)
                item_caso.setData(0, Qt.UserRole, (nombre_combo, nombre_caso))
    def _seleccionar_todo_arbol(self):
        """Marca todos los elementos del árbol."""
        self._cambiar_estado_hijos_arbol(Qt.CheckState.Checked)

    def _deseleccionar_todo_arbol(self):
        """Desmarca todos los elementos del árbol."""
        self._cambiar_estado_hijos_arbol(Qt.CheckState.Unchecked)

    def _cambiar_estado_hijos_arbol(self, estado):
        """
        Recorre el árbol de combinaciones y casos para cambiar su estado.
        Funciona para padres (combinaciones) e hijos (casos).
        """
        root = self.arbol_combos.invisibleRootItem()
        for i in range(root.childCount()):
            item_padre = root.child(i)
            item_padre.setCheckState(0, estado)
            # También marcar/desmarcar a los hijos (casos)
            for j in range(item_padre.childCount()):
                item_hijo = item_padre.child(j)
                item_hijo.setCheckState(0, estado)

        self.arbol_combos.expandAll()
        self.arbol_combos.header().setSectionResizeMode(QHeaderView.ResizeToContents)

    def _parsear_string_elementos(self, texto):
        """
        Convierte un string estilo '1-5,9,12-17' en una lista de enteros únicos [1,2,3,4,5,9,12,13,14,15,16,17]
        """
        elementos_seleccionados = set()
        if not texto.strip():
            return list(elementos_seleccionados)
            
        partes = texto.split(',')
        for parte in partes:
            parte = parte.strip()
            if not parte: continue
            if '-' in parte:
                try:
                    inicio_str, fin_str = parte.split('-')
                    inicio = int(inicio_str)
                    fin = int(fin_str)
                    if inicio <= fin:
                        elementos_seleccionados.update(range(inicio, fin + 1))
                except ValueError:
                    pass # Ignoramos silenciosamente si el usuario teclea letras en el rango
            else:
                try:
                    elementos_seleccionados.add(int(parte))
                except ValueError:
                    pass # Ignoramos silenciosamente si hay caracteres extraños
        return list(elementos_seleccionados)

    def _abrir_dialogo_avanzado(self):
        dialogo_avz = DialogoOpcionesAvanzadasReporte(self.config_avanzada, self)
        if dialogo_avz.exec():
            self.config_avanzada = dialogo_avz.get_opciones_avanzadas()
            print("[DEBUG] Opciones avanzadas actualizadas:", self.config_avanzada) # Para depuración

    def get_configuracion(self):
        # Recopila todas las selecciones en un diccionario
        config = {}

        # 1. Combinaciones/Casos seleccionados
        config['casos_seleccionados'] = []
        root = self.arbol_combos.invisibleRootItem()
        for i in range(root.childCount()):
            item_combo = root.child(i)
            if item_combo.checkState(0) == Qt.Checked:
                for j in range(item_combo.childCount()):
                    item_caso = item_combo.child(j)
                    if item_caso.checkState(0) == Qt.Checked:
                        combo_caso_tuple = item_caso.data(0, Qt.UserRole)
                        if combo_caso_tuple:
                            config['casos_seleccionados'].append(combo_caso_tuple)

        # 2. Secciones Principales
        config['mostrar_proc_losas'] = self.cb_proc_losas.isChecked()
        config['mostrar_analisis_mat'] = self.cb_analisis_mat.isChecked()
        config['mostrar_resolucion'] = self.cb_resolucion.isChecked()
        config['mostrar_fuerzas_int'] = self.cb_fuerzas_int.isChecked()
        config['mostrar_resumen_max'] = self.cb_resumen_max.isChecked()

        # 3. Opciones Avanzadas 
        config.update(self.config_avanzada) # Añade/sobrescribe con las opciones avanzadas

        # 4. Filtro de Elementos Específicos
        if self.check_todos_elem.isChecked():
            config['elementos_especificos'] = 'todos'
        else:
            texto_ingresado = self.input_elem.text()
            elementos_filtrados = self._parsear_string_elementos(texto_ingresado)
            
            # Si el usuario desmarca "Todos" pero deja el cuadro vacío o con formato inválido, 
            # devolvemos una lista vacía para no procesar elementos al azar.
            if not elementos_filtrados:
                config['elementos_especificos'] = [] 
            else:
                config['elementos_especificos'] = elementos_filtrados

        return config

class PestañaReporte(QWidget):
    enviar_mensaje_statusbar = Signal(str, int)

    def __init__(self, modelo): 
        super().__init__()
        self.modelo = modelo 
        self.ultima_config_avanzada = {} 

        layout = QVBoxLayout(self)

        self.btn_configurar_generar = QPushButton("Configurar y Generar Reporte")
        self.btn_configurar_generar.clicked.connect(self._abrir_dialogo_config_reporte)
        self.btn_configurar_generar.setEnabled(False)

        layout.addWidget(self.btn_configurar_generar, alignment=Qt.AlignLeft)

        self.reporte_texto = QTextEdit()
        self.reporte_texto.setReadOnly(True)
        self.reporte_texto.setFont(QFont("Consolas, Courier New, monospace", 9))
        self.reporte_texto.setLineWrapMode(QTextEdit.NoWrap)
        self.reporte_texto.setPlaceholderText("Realice un cálculo y luego configure y genere un reporte...")

        layout.addWidget(self.reporte_texto)

    def _abrir_dialogo_config_reporte(self):
        if not self.modelo or not self.modelo.resultados_calculo:
            QMessageBox.warning(self, "Sin Resultados", "Primero debe realizar un cálculo exitoso.")
            return

        dialogo_cfg = DialogoConfigReporte(self.modelo.resultados_calculo, self.ultima_config_avanzada, self)
        if dialogo_cfg.exec():
            config = dialogo_cfg.get_configuracion()
            self.ultima_config_avanzada = {k: v for k, v in config.items() if k not in [
                'casos_seleccionados', 'mostrar_proc_losas', 'mostrar_analisis_mat',
                'mostrar_resolucion', 'mostrar_fuerzas_int', 'mostrar_resumen_max'
            ]}
            self._generar_reporte_configurado(config)

    def _generar_reporte_configurado(self, config):
        if not self.modelo: return

        self.enviar_mensaje_statusbar.emit("Generando reporte configurado...", 0)
        self.reporte_texto.setText("Generando reporte, por favor espere...")
        QApplication.processEvents() 

        try:
            from generador_reporte import GeneradorReporte
            generador = GeneradorReporte(self.modelo)
        
            texto_reporte = generador.generar_reporte_personalizado(config)
            
            self.actualizar(texto_reporte) # Llama al método existente para mostrar el texto
            self.enviar_mensaje_statusbar.emit("Reporte generado con éxito.", 5000)
        except Exception as e:
            error_msg = f"Error al generar el reporte:\n\n{e}\n\n{traceback.format_exc()}"
            self.actualizar(error_msg)
            self.enviar_mensaje_statusbar.emit("Error al generar el reporte.", 5000)
            QMessageBox.critical(self, "Error de Reporte", f"Ocurrió un error: {e}")

    def actualizar(self, texto):
        """Actualiza el contenido del QTextEdit y habilita/deshabilita el botón."""
        self.reporte_texto.setText(texto)
        self.btn_configurar_generar.setEnabled(bool(self.modelo and self.modelo.resultados_calculo))
        if not (self.modelo and self.modelo.resultados_calculo):
             self.reporte_texto.setPlaceholderText("Realice un cálculo para poder generar un reporte...")


class MatplotlibWidget(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.figura = Figure(figsize=(5, 4), dpi=100)
        self.lienzo = FigureCanvas(self.figura)
        
        self.ejes = self.figura.add_subplot(111)
        
        self.barra_herramientas = NavigationToolbar(self.lienzo, self)
        
        layout = QVBoxLayout()
        layout.addWidget(self.barra_herramientas)
        layout.addWidget(self.lienzo)
        self.setLayout(layout)

class PestañaDiseño(QWidget):
    def __init__(self, modelo):
        super().__init__()
        self.modelo = modelo
        layout_principal = QVBoxLayout(self)
        self.sub_pestanas = QTabWidget()
        layout_principal.addWidget(self.sub_pestanas)
        self.pagina_vigas = PaginaVigas(self.modelo)
        self.pagina_columnas = PaginaColumnas(self.modelo)
        self.sub_pestanas.addTab(self.pagina_vigas, "Vigas")
        self.sub_pestanas.addTab(self.pagina_columnas, "Columnas")

    def actualizar(self, modelo):
        self.pagina_vigas.actualizar(modelo)
        self.pagina_columnas.actualizar(modelo)

class PaginaVigas(QWidget):
    enviar_mensaje_statusbar = Signal(str, int)

    def __init__(self, modelo):
        super().__init__()
        
        self.modelo = modelo
        self.generador_diagramas = None
        self.ultima_memoria_calculo = None 

        self._cache_colores_usuario = {}
        self.click_annotation = None
        self.current_x = None
        self.current_y = None
        self.search_annotations = []
        self.current_envelope_max = None
        self.current_envelope_min = None

        layout_principal = QHBoxLayout(self)
        
        contenedor_izquierdo = QWidget()
        contenedor_izquierdo.setMinimumWidth(380) 
        contenedor_izquierdo.setMaximumWidth(550)
        layout_izquierdo = QVBoxLayout(contenedor_izquierdo)
        layout_izquierdo.setContentsMargins(0, 0, 0, 0)
        panel_entradas = self._crear_panel_entradas_viga()
        layout_izquierdo.addWidget(panel_entradas, stretch=1)
        
        self.boton_calcular = QPushButton("Calcular Diseño")
        self.boton_calcular.setCursor(Qt.CursorShape.PointingHandCursor)
        self.boton_calcular.setMinimumHeight(50)
        self.boton_calcular.setStyleSheet("""
            QPushButton {
                font-size: 16px; 
                padding: 10px; 
                background-color: #2E7D32; 
                color: white; 
                font-weight: bold;
                border-radius: 4px;
                border: 1px solid #1B5E20;
            }
            QPushButton:hover { background-color: #388E3C; }
            QPushButton:pressed { background-color: #1B5E20; }
            QPushButton:disabled { background-color: #cccccc; color: #666666; border: 1px solid #999; }
        """)
        self.boton_calcular.clicked.connect(self._ejecutar_calculo_viga)
        layout_izquierdo.addWidget(self.boton_calcular)

        panel_resumen = self._crear_grupo_resultados_rapidos()
        layout_izquierdo.addWidget(panel_resumen)

        self.tabs_derecha = QTabWidget()
        self.tabs_derecha.setStyleSheet("""
            QTabBar::tab { height: 30px; min-width: 120px; font-weight: bold; }
        """)

        self.tab_diagramas = self._crear_panel_diagramas()
        self.tabs_derecha.addTab(self.tab_diagramas, "Diagramas")

        self.tab_reporte = QWidget()
        layout_reporte = QVBoxLayout(self.tab_reporte)
        self.scroll_reporte = QScrollArea()
        self.scroll_reporte.setWidgetResizable(True)
        self.scroll_reporte.setFrameShape(QFrame.Shape.NoFrame)
        
        self.contenedor_contenido_reporte = QWidget()
        self.contenedor_contenido_reporte.setStyleSheet("background-color: white; color: black;")
        self.layout_contenido_reporte = QVBoxLayout(self.contenedor_contenido_reporte)
        self.layout_contenido_reporte.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.layout_contenido_reporte.setSpacing(5)
        self.layout_contenido_reporte.setContentsMargins(20, 20, 20, 20)
        
        self.scroll_reporte.setWidget(self.contenedor_contenido_reporte)
        layout_reporte.addWidget(self.scroll_reporte)
        
        self.tabs_derecha.addTab(self.tab_reporte, "Reporte de Cálculo")

        self.tab_armado = self._crear_panel_registro_armado()
        self.tabs_derecha.addTab(self.tab_armado, "Registro de Armado")

        layout_principal.addWidget(contenedor_izquierdo)
        layout_principal.addWidget(self.tabs_derecha)

        self.setEnabled(False) 

    def _crear_panel_entradas_viga(self):
        """Crea el área de inputs con scroll."""
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        
        grupo_entradas = self._crear_grupo_datos_entrada_contenido()
        scroll_area.setWidget(grupo_entradas)
        return scroll_area

    def _crear_grupo_datos_entrada_contenido(self):
        """Contenido del formulario de datos de la viga."""
        widget_contenido = QWidget()
        layout_formulario = QFormLayout(widget_contenido)
        layout_formulario.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapAllRows)
        layout_formulario.setVerticalSpacing(8)
        layout_formulario.setHorizontalSpacing(10)

        def create_separator(text):
            label = QLabel(text)
            label.setStyleSheet("font-weight: bold; font-size: 10pt; margin-top: 15px; border-bottom: 2px solid #4CAF50; padding-bottom: 2px;")
            layout_formulario.addRow(label)

        self.fc_input = QLineEdit("25"); self.fc_input.setPlaceholderText("MPa")
        self.fy_input = QLineEdit("420"); self.fy_input.setPlaceholderText("MPa")
        create_separator("1. Materiales")
        layout_formulario.addRow("f'c (Hormigón) [MPa]:", self.fc_input)
        layout_formulario.addRow("fy (Acero) [MPa]:", self.fy_input)
        
        self.mu_input = QLineEdit("120"); self.mu_input.setPlaceholderText("kN·m")
        self.vu_input = QLineEdit("80"); self.vu_input.setPlaceholderText("kN")
        create_separator("2. Solicitaciones de Diseño")
        layout_formulario.addRow("Momento Último Mu [kN·m]:", self.mu_input)
        layout_formulario.addRow("Cortante Último Vu [kN]:", self.vu_input) 

        self.b_input = QLineEdit("25"); self.b_input.setPlaceholderText("cm")
        self.h_input = QLineEdit("50"); self.h_input.setPlaceholderText("cm")
        self.rec_input = QLineEdit("3"); self.rec_input.setPlaceholderText("cm")
        create_separator("3. Geometría de la Sección")
        layout_formulario.addRow("Base (b) [cm]:", self.b_input)
        layout_formulario.addRow("Altura (h) [cm]:", self.h_input)
        layout_formulario.addRow("Recubrimiento (r) [cm]:", self.rec_input)
        
        self.diam_long_input = QComboBox()
        self.diam_est_corte_input = QComboBox()
        lista_diametros = [f"{d:g}" for d in sorted(BARRAS_COMERCIALES.keys())]
        self.diam_long_input.addItems(lista_diametros); self.diam_long_input.setCurrentText("16")
        self.diam_est_corte_input.addItems(lista_diametros); self.diam_est_corte_input.setCurrentText("8")

        create_separator("4. Parámetros de Armado") 
        layout_formulario.addRow("Ø Barra Longitudinal [mm]:", self.diam_long_input)
        layout_formulario.addRow("Ø Estribo Corte [mm]:", self.diam_est_corte_input)
        
        diagrama_label = crear_diagrama_d() 
        self.combo_armado_previo = QComboBox()
        
        layout_extra = QHBoxLayout()
        layout_extra.addWidget(diagrama_label)
        
        layout_previo = QVBoxLayout()
        layout_previo.addWidget(QLabel("Armado Previo (Flexión):"))
        layout_previo.addWidget(self.combo_armado_previo)
        layout_previo.addStretch()
        layout_extra.addLayout(layout_previo)
        
        layout_formulario.addRow(layout_extra)
        
        return widget_contenido

    def _crear_grupo_resultados_rapidos(self):
        """Panel de resumen al pie izquierdo."""
        grupo = QGroupBox("Resultados Principales")
        grupo.setStyleSheet("QGroupBox { font-weight: bold; border: 1px solid #999; border-radius: 4px; margin-top: 10px; } QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 3px; }")
        layout = QFormLayout(grupo)

        font_res = QFont(); font_res.setPointSize(11); font_res.setBold(True)

        self.resultado_as_traccion = QLabel("---")
        self.resultado_as_traccion.setFont(font_res); self.resultado_as_traccion.setStyleSheet("color: #2196F3;")
        
        self.resultado_as_compresion = QLabel("---")
        self.resultado_as_compresion.setFont(font_res); self.resultado_as_compresion.setStyleSheet("color: #2196F3;")
        
        self.resultado_corte = QLabel("---")
        self.resultado_corte.setFont(font_res); self.resultado_corte.setStyleSheet("color: #EF5350;")

        layout.addRow("As Tracción:", self.resultado_as_traccion)
        layout.addRow("A's Compresión:", self.resultado_as_compresion)
        layout.addRow("Estribos:", self.resultado_corte)
        
        return grupo

    def _crear_panel_diagramas(self):
        """Panel para la Pestaña 1: Gráfico de Diagramas."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        grupo_controles = QGroupBox()
        grupo_controles.setStyleSheet("QGroupBox { border: none; }") 
        layout_controles = QGridLayout(grupo_controles)
        layout_controles.setContentsMargins(5, 5, 5, 5)
        
        self.combo_elementos = QComboBox()
        self.combo_combinaciones = QComboBox()
        self.combo_casos_hipotesis = QComboBox()
        self.combo_efectos = QComboBox()
        self.combo_efectos.addItems(['Axial (Px)', 'Cortante (Py)', 'Momento (Mz)', 'Cortante (Pz)', 'Momento (My)', 'Torsión (Mx)'])
        
        layout_controles.addWidget(QLabel("Elem:"), 0, 0)
        layout_controles.addWidget(self.combo_elementos, 0, 1)
        layout_controles.addWidget(QLabel("Combo:"), 0, 2)
        layout_controles.addWidget(self.combo_combinaciones, 0, 3)
        layout_controles.addWidget(QLabel("Caso:"), 0, 4)
        layout_controles.addWidget(self.combo_casos_hipotesis, 0, 5)
        
        layout_controles.addWidget(QLabel("Efecto:"), 1, 0)
        layout_controles.addWidget(self.combo_efectos, 1, 1)
        
        self.check_mostrar_armado = QCheckBox("Ver Armado")
        self.check_envolvente = QCheckBox("Envolvente")
        self.check_combinaciones = QCheckBox("Todas")
        self.check_combinaciones.setEnabled(False)
        
        hbox_checks = QHBoxLayout()
        hbox_checks.addWidget(self.check_mostrar_armado)
        hbox_checks.addWidget(self.check_envolvente)
        hbox_checks.addWidget(self.check_combinaciones)
        
        layout_controles.addLayout(hbox_checks, 1, 2, 1, 4)
        layout.addWidget(grupo_controles)

        layout_busqueda = QHBoxLayout()
        self.entrada_x = QLineEdit(); self.entrada_x.setPlaceholderText("X (m)"); self.entrada_x.setFixedWidth(60)
        self.btn_mostrar_valor = QPushButton("Ir a X")
        self.entrada_valor_y = QLineEdit(); self.entrada_valor_y.setPlaceholderText("Y"); self.entrada_valor_y.setFixedWidth(60)
        self.btn_buscar_por_valor = QPushButton("Buscar Y")
        
        layout_busqueda.addWidget(QLabel("Coord X:"))
        layout_busqueda.addWidget(self.entrada_x)
        layout_busqueda.addWidget(self.btn_mostrar_valor)
        layout_busqueda.addWidget(QFrame(frameShape=QFrame.Shape.VLine))
        layout_busqueda.addWidget(QLabel("Valor Y:"))
        layout_busqueda.addWidget(self.entrada_valor_y)
        layout_busqueda.addWidget(self.btn_buscar_por_valor)
        layout_busqueda.addStretch()
        layout.addLayout(layout_busqueda)

        contenedor_grafico = QWidget()
        contenedor_grafico.setStyleSheet("background-color: white; color: black;") 
        layout_grafico = QVBoxLayout(contenedor_grafico)
        layout_grafico.setContentsMargins(0,0,0,0)
        
        self.grafico_widget = MatplotlibWidget()
        layout_grafico.addWidget(self.grafico_widget)
        
        layout.addWidget(contenedor_grafico, stretch=1)
        
        self.combo_elementos.currentIndexChanged.connect(self.refrescar_diagrama)
        self.combo_combinaciones.currentIndexChanged.connect(self._actualizar_combo_casos_hipotesis)
        self.combo_casos_hipotesis.currentIndexChanged.connect(self.refrescar_diagrama)
        self.combo_combinaciones.currentIndexChanged.connect(self.refrescar_diagrama)
        self.combo_efectos.currentIndexChanged.connect(self.refrescar_diagrama)
        self.check_envolvente.stateChanged.connect(self.refrescar_diagrama)
        self.check_combinaciones.stateChanged.connect(self.refrescar_diagrama)
        self.check_mostrar_armado.stateChanged.connect(self.refrescar_diagrama)
        self.grafico_widget.lienzo.mpl_connect('button_press_event', self.on_diagram_click)
        self.btn_mostrar_valor.clicked.connect(self._on_mostrar_valor_click)
        self.btn_buscar_por_valor.clicked.connect(self._on_buscar_por_valor_click)
        
        return panel

    def _crear_panel_registro_armado(self):
        """Panel para la Pestaña 3: Tabla de armados manuales."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        grupo_entrada = QGroupBox("Añadir Armado Manual")
        l_entrada = QGridLayout(grupo_entrada)
        
        self.descripcion_armado_input = QLineEdit(); self.descripcion_armado_input.setPlaceholderText("Etiqueta (ej: Refuerzo Centro)")
        self.tipo_armado_combo = QComboBox(); self.tipo_armado_combo.addItems(["Flexión", "Corte"])
        self.cantidad_armado_input = QSpinBox(minimum=1); self.cantidad_armado_input.setValue(2)
        self.diametro_armado_combo = QComboBox()
        self.diametro_armado_combo.addItems(["6", "8", "10", "12", "16", "20", "25", "32"])
        self.diametro_armado_combo.setCurrentText("12")
        self.desde_armado_input = QDoubleSpinBox(decimals=2, maximum=100); self.desde_armado_input.setPrefix("De: ")
        self.hasta_armado_input = QDoubleSpinBox(decimals=2, maximum=100); self.hasta_armado_input.setPrefix("A: ")
        self.posicion_armado_combo = QComboBox(); self.posicion_armado_combo.addItems(["Superior", "Inferior"])
        self.separacion_armado_input = QDoubleSpinBox(decimals=2, maximum=100); self.separacion_armado_input.setPrefix("Sep: ")
        
        l_entrada.addWidget(QLabel("Desc:"), 0, 0)
        l_entrada.addWidget(self.descripcion_armado_input, 0, 1, 1, 3)
        l_entrada.addWidget(QLabel("Tipo:"), 0, 4)
        l_entrada.addWidget(self.tipo_armado_combo, 0, 5)
        
        l_entrada.addWidget(QLabel("Cant:"), 1, 0)
        l_entrada.addWidget(self.cantidad_armado_input, 1, 1)
        l_entrada.addWidget(QLabel("Ø:"), 1, 2)
        l_entrada.addWidget(self.diametro_armado_combo, 1, 3)
        l_entrada.addWidget(self.desde_armado_input, 1, 4)
        l_entrada.addWidget(self.hasta_armado_input, 1, 5)
        
        self.stack_pos_sep = QStackedWidget()
        w_pos = QWidget(); l_pos = QHBoxLayout(w_pos); l_pos.setContentsMargins(0,0,0,0)
        l_pos.addWidget(QLabel("Posición:")); l_pos.addWidget(self.posicion_armado_combo)
        w_sep = QWidget(); l_sep = QHBoxLayout(w_sep); l_sep.setContentsMargins(0,0,0,0)
        l_sep.addWidget(QLabel("Separación (cm):")); l_sep.addWidget(self.separacion_armado_input)
        
        self.stack_pos_sep.addWidget(w_pos) # Index 0 (Flexión)
        self.stack_pos_sep.addWidget(w_sep) # Index 1 (Corte)
        l_entrada.addWidget(self.stack_pos_sep, 2, 0, 1, 4)
        
        self.btn_guardar_armado = QPushButton("Añadir a Tabla")
        l_entrada.addWidget(self.btn_guardar_armado, 2, 4, 1, 2)
        
        layout.addWidget(grupo_entrada)
        
        self.tabla_armado = QTableWidget(0, 7)
        self.tabla_armado.setHorizontalHeaderLabels(["Desc", "Tipo", "Armado", "De", "A", "Pos", "Sep(cm)"])
        self.tabla_armado.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.tabla_armado.horizontalHeader().setStretchLastSection(True)
        self.tabla_armado.setSelectionBehavior(QAbstractItemView.SelectRows)
        layout.addWidget(self.tabla_armado)
        
        hbox_btns = QHBoxLayout()
        self.btn_eliminar_armado = QPushButton("Eliminar Selección")
        self.btn_guardar_cambios_tabla_armado = QPushButton("Guardar Cambios Editados")
        self.btn_guardar_cambios_tabla_armado.setEnabled(False)
        hbox_btns.addWidget(self.btn_eliminar_armado)
        hbox_btns.addWidget(self.btn_guardar_cambios_tabla_armado)
        layout.addLayout(hbox_btns)
        
        self.tipo_armado_combo.currentIndexChanged.connect(lambda i: self.stack_pos_sep.setCurrentIndex(i))
        self.btn_guardar_armado.clicked.connect(self._guardar_armado_manual)
        self.btn_eliminar_armado.clicked.connect(self._eliminar_armado_seleccionado)
        self.tabla_armado.itemChanged.connect(self._marcar_cambios_tabla_armado)
        self.btn_guardar_cambios_tabla_armado.clicked.connect(self._guardar_cambios_de_tabla_armado)
        
        return widget

    def _ejecutar_calculo_viga(self):
        """Ejecuta el cálculo usando el motor y actualiza la UI."""
        self.enviar_mensaje_statusbar.emit("Realizando diseño de viga...", 0)
        self.boton_calcular.setEnabled(False)
        self.boton_calcular.setText("Calculando...")
        QApplication.processEvents()

        try:
            f_c = float(self.fc_input.text())
            f_y = float(self.fy_input.text())
            mu_knm = float(self.mu_input.text())
            Vu_kN = float(self.vu_input.text())
            b_cm = float(self.b_input.text())
            h_cm = float(self.h_input.text())
            r_min_cm = float(self.rec_input.text())
            diametro_longitudinal = float(self.diam_long_input.currentText())
            diametro_estribo_corte = float(self.diam_est_corte_input.currentText())

            datos_previos = self.combo_armado_previo.currentData()
            area_previa_cm2 = datos_previos['area_cm2'] if datos_previos else 0.0
            reporte = vigas.realizar_diseno_viga(
                f_c, f_y, mu_knm, Vu_kN, b_cm, h_cm, r_min_cm, 
                diametro_longitudinal, 
                diametro_estribo_corte, 
                area_acero_previo_cm2=area_previa_cm2,
                armado_previo_info=datos_previos
            )

            resultados = reporte.get('resultados', {})
            self.resultado_as_traccion.setText(f"{resultados.get('As_traccion_cm2', 0):.2f} cm²")
            self.resultado_as_compresion.setText(f"{resultados.get('As_compresion_cm2', 0):.2f} cm²")
            
            separacion = resultados.get('separacion_cm', "N/A")
            if isinstance(separacion, (int, float)):
                self.resultado_corte.setText(f"Ø{int(diametro_estribo_corte)} c/ {separacion:.1f} cm")
            else:
                self.resultado_corte.setText(f"{separacion}")

            self._poblar_reporte_incrustado(reporte['memoria'])
            
            self.tabs_derecha.setCurrentIndex(1)

            id_elem_actual = self.combo_elementos.currentText()
            self.enviar_mensaje_statusbar.emit(f"Diseño para viga {id_elem_actual} completado.", 5000)

        except ValueError:
            QMessageBox.warning(self, "Error de Datos", "Por favor, ingrese valores numéricos válidos en los campos de entrada.")
        except Exception as e:
            QMessageBox.critical(self, "Error de Cálculo", f"No se pudo completar el diseño: {e}")
            print(traceback.format_exc())
        finally:
            self.boton_calcular.setEnabled(True)
            self.boton_calcular.setText("Calcular Diseño")

    def _poblar_reporte_incrustado(self, lineas_memoria):
        """Limpia y rellena la pestaña de reporte con el contenido HTML/LaTeX."""
        while self.layout_contenido_reporte.count():
            child = self.layout_contenido_reporte.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
    
        for linea in lineas_memoria:
            if linea.startswith('$'):
                widget_linea = render_latex(linea) 
            else:
                widget_linea = QLabel(linea)
                widget_linea.setWordWrap(True)
                widget_linea.setTextFormat(Qt.TextFormat.RichText)
                widget_linea.setStyleSheet("font-size: 10pt; padding: 2px;")
                if "<h2>" in linea or "<h3>" in linea:
                    widget_linea.setStyleSheet("color: #2E7D32; margin-top: 10px; margin-bottom: 5px;")
                elif "ERROR" in linea or "ALERTA" in linea:
                     widget_linea.setStyleSheet("color: #C62828; font-weight: bold;")
            
            self.layout_contenido_reporte.addWidget(widget_linea)
        
        self.layout_contenido_reporte.addStretch() 

    def actualizar(self, modelo):
        """Actualiza la página con nuevos resultados, poblando los combos de selección."""
        self.modelo = modelo
        if not modelo.resultados_calculo:
            self.setEnabled(False)
            return
            
        self.generador_diagramas = GeneradorDiagramas(self.modelo)
        
        self.combo_elementos.blockSignals(True)
        self.combo_combinaciones.blockSignals(True)
        
        self.combo_elementos.clear()
        ids_vigas = []
        for id_elem, (ni, nj, _) in self.modelo.elementos.items():
            z1 = self.modelo.nodos[ni][2]
            z2 = self.modelo.nodos[nj][2]
            if abs(z1 - z2) < 1e-6:
                ids_vigas.append(id_elem)
        
        if ids_vigas:
            self.combo_elementos.addItems([str(eid) for eid in sorted(ids_vigas)])
        else:
            self.combo_elementos.addItem("No hay vigas")

        self.combo_combinaciones.clear()
        if self.modelo.resultados_calculo:
            claves_filtradas = [k for k in self.modelo.resultados_calculo.keys() if k != 'reporte_global_data']
            self.combo_combinaciones.addItems(claves_filtradas)
        
        self.combo_elementos.blockSignals(False)
        self.combo_combinaciones.blockSignals(False)
        
        self.setEnabled(True)
        self._actualizar_combo_casos_hipotesis()

    def _actualizar_combo_casos_hipotesis(self):
        self.combo_casos_hipotesis.blockSignals(True)
        self.combo_casos_hipotesis.clear()
        
        nombre_combo_sel = self.combo_combinaciones.currentText()
        if not nombre_combo_sel or not self.modelo.resultados_calculo:
            self.combo_casos_hipotesis.blockSignals(False)
            self.refrescar_diagrama()
            return

        sub_resultados = self.modelo.resultados_calculo.get(nombre_combo_sel, {})
        nombres_sub_casos = sorted(sub_resultados.keys())
        if nombres_sub_casos:
            self.combo_casos_hipotesis.addItems(nombres_sub_casos)
        
        self.combo_casos_hipotesis.blockSignals(False)
        self.refrescar_diagrama()

    def _refrescar_combo_armado_previo(self):
        """Llena el ComboBox de armado previo SÓLO con los datos de flexión."""
        self.combo_armado_previo.clear()
        self.combo_armado_previo.addItem("Ninguno", userData=None) 

        id_elem_str = self.combo_elementos.currentText()
        if not id_elem_str or "No hay" in id_elem_str: return

        id_elem = int(id_elem_str)
        lista_armados = self.modelo.armados_diseno.get(id_elem, [])
        areas_barras_cm2 = {6: 0.28, 8: 0.50, 9.5: 0.709, 12: 1.13, 16: 2.01, 20: 3.14, 25: 4.91, 32: 8.04}

        for i, armado in enumerate(lista_armados):
            if armado.get('tipo', 'Flexión') != 'Flexión': continue 
            texto_display = f"{armado['descripcion']}: {armado['cantidad']}Ø{armado['diametro']}; {armado['posicion']}"
            area_cm2 = armado['cantidad'] * areas_barras_cm2.get(armado['diametro'], 0)
            datos_armado = {'area_cm2': area_cm2, 'cantidad': armado['cantidad'], 'diametro': armado['diametro'], 'posicion': armado['posicion']}
            self.combo_armado_previo.addItem(texto_display, userData=datos_armado)

    def refrescar_diagrama(self):
        """Redibuja el diagrama de esfuerzos en el widget Matplotlib."""
        for ann in self.search_annotations: 
            try: ann.remove()
            except Exception: pass
        self.search_annotations.clear()

        self._refrescar_tabla_armado()
        self._refrescar_combo_armado_previo()
        
        if not self.isEnabled() or not self.generador_diagramas or self.combo_elementos.count() == 0:
            return

        id_elem_str = self.combo_elementos.currentText()
        if not id_elem_str or "No hay" in id_elem_str: return
        id_elem = int(id_elem_str)
        tipo_efecto = self.combo_efectos.currentText()

        envolvente_activa = self.check_envolvente.isChecked()
        ver_combinaciones = self.check_combinaciones.isChecked()

        self.combo_combinaciones.setEnabled(not envolvente_activa)
        self.combo_casos_hipotesis.setEnabled(not envolvente_activa)
        self.check_combinaciones.setEnabled(envolvente_activa)

        self.current_y = None
        self.current_envelope_max = None
        self.current_envelope_min = None
        self.click_annotation = None
        
        ax = self.grafico_widget.ejes
        ax.clear()
        color_fondo = 'white'; color_texto = 'black'
        ax.set_facecolor(color_fondo); self.grafico_widget.figura.set_facecolor(color_fondo)
        ax.tick_params(axis='both', colors=color_texto)
        for spine in ax.spines.values(): spine.set_color(color_texto)
        ax.yaxis.label.set_color(color_texto); ax.xaxis.label.set_color(color_texto); ax.title.set_color(color_texto)

        PUNTOS_DIAGRAMA = 51
        ax.set_xlabel('Longitud (m)'); ax.set_ylabel(tipo_efecto)
        ax.grid(True, linestyle='--', color='gray', alpha=0.4)
        
        longitud = self.generador_diagramas.get_longitud_elemento(id_elem)
        if longitud > 0: ax.axhline(0, color='black', linestyle='-', linewidth=1.5, zorder=1)

        if tipo_efecto in ['Momento (My)', 'Momento (Mz)']: ax.invert_yaxis()

        if not self.modelo.resultados_calculo: return

        claves_combos_validas = [k for k in self.modelo.resultados_calculo.keys() if k != 'reporte_global_data']
        if not claves_combos_validas:
            ax.set_title("No hay resultados de cálculo válidos.")
            self.grafico_widget.lienzo.draw()
            return 
        primer_combo = claves_combos_validas[0]
        primer_caso = list(self.modelo.resultados_calculo[primer_combo].keys())[0]
        resultados_base = self.modelo.resultados_calculo[primer_combo][primer_caso]
        self.current_x, _ = self.generador_diagramas.get_diagrama(id_elem, resultados_base, tipo_efecto, n_puntos=PUNTOS_DIAGRAMA)

        if envolvente_activa:
            lista_casos = []
            for nombre_combo, sub_resultados in self.modelo.resultados_calculo.items():
                if nombre_combo == 'reporte_global_data': continue
                for sub_caso, resultados in sub_resultados.items():
                    nombre_completo = f"{nombre_combo}: {sub_caso}"
                    lista_casos.append((nombre_completo, resultados))
            
            if not lista_casos: self.grafico_widget.lienzo.draw(); return

            diagramas_raw = []; todos_los_x = set()
            x_base_linspace = np.linspace(0, longitud, PUNTOS_DIAGRAMA)
            for x_val in x_base_linspace: todos_los_x.add(x_val)

            for nombre_completo, res in lista_casos:
                x_diag, y_diag = self.generador_diagramas.get_diagrama(id_elem, res, tipo_efecto, n_puntos=PUNTOS_DIAGRAMA)
                diagramas_raw.append({'x': x_diag, 'y': y_diag, 'nombre': nombre_completo})
                for x_val in x_diag: todos_los_x.add(x_val)
            
            x_unificado = np.sort(list(todos_los_x))
            lista_diagramas_y_unificados = []
            for diag in diagramas_raw:
                y_interpolado = np.interp(x_unificado, diag['x'], diag['y'])
                lista_diagramas_y_unificados.append(y_interpolado)
            
            self.current_x = x_unificado
            
            if ver_combinaciones:
                ax.set_title(f"Elemento {id_elem} - {tipo_efecto} (Todos los Casos)")
                for i, diag in enumerate(diagramas_raw):
                    color = self._get_color_por_nombre(diag['nombre'])
                    ax.plot(self.current_x, lista_diagramas_y_unificados[i], color=color, linewidth=2.0, alpha=0.8, label=diag['nombre'])
                leyenda = ax.legend(facecolor='white', edgecolor='black')
                for texto in leyenda.get_texts(): texto.set_color('black')
            else:
                ax.set_title(f"Elemento {id_elem} - {tipo_efecto} (Envolvente)")
                matriz_y = np.array(lista_diagramas_y_unificados)
                envolvente_positiva = np.max(matriz_y, axis=0); envolvente_positiva = np.where(envolvente_positiva > 0, envolvente_positiva, 0)
                envolvente_negativa = np.min(matriz_y, axis=0); envolvente_negativa = np.where(envolvente_negativa < 0, envolvente_negativa, 0)
                self.current_envelope_max = envolvente_positiva; self.current_envelope_min = envolvente_negativa
                
                y_max_env = np.max(envolvente_positiva)
                if abs(y_max_env) > 1e-9: 
                    idx_max = np.argmax(envolvente_positiva); x_max = self.current_x[idx_max]
                    ax.scatter(x_max, y_max_env, color='blue', zorder=4, s=30)
                    ax.text(x_max, y_max_env, f"Máx[+] {self._format_value(y_max_env)}", color='black', ha='center', va='bottom', fontsize=9, weight='bold')

                y_min_env = np.min(envolvente_negativa)
                if abs(y_min_env) > 1e-9: 
                    idx_min = np.argmin(envolvente_negativa); x_min = self.current_x[idx_min]
                    ax.scatter(x_min, y_min_env, color='red', zorder=4, s=30)
                    ax.text(x_min, y_min_env, f"Máx[-] {self._format_value(y_min_env)}", color='black', ha='center', va='top', fontsize=9, weight='bold')

                for y_actual_unificado in lista_diagramas_y_unificados:
                    ax.plot(self.current_x, y_actual_unificado, color='gray', linewidth=1.0, alpha=0.5)
                
                ax.plot(self.current_x, envolvente_positiva, color='red', linewidth=2.0)
                ax.plot(self.current_x, envolvente_negativa, color='blue', linewidth=2.0)

        else: # Caso Individual
            nombre_combo = self.combo_combinaciones.currentText()
            nombre_sub_caso = self.combo_casos_hipotesis.currentText()
            if not nombre_combo or not nombre_sub_caso or not self.modelo.resultados_calculo or nombre_combo not in self.modelo.resultados_calculo or nombre_sub_caso not in self.modelo.resultados_calculo[nombre_combo]:
                ax.clear(); ax.set_title("Seleccione combinación y caso válidos"); self.grafico_widget.lienzo.draw(); return

            ax.set_title(f"Elem {id_elem} - {nombre_sub_caso} - {tipo_efecto}")
            resultados_especificos = self.modelo.resultados_calculo[nombre_combo][nombre_sub_caso]
            
            x, y = self.generador_diagramas.get_diagrama(id_elem, resultados_especificos, tipo_efecto, n_puntos=PUNTOS_DIAGRAMA)
            self.current_x, self.current_y = x, y
            
            color = self._get_color_por_nombre(nombre_sub_caso)
            ax.plot(self.current_x, y, color=color, linewidth=2.5, zorder=2)
            ax.fill_between(self.current_x, y, 0, color=color, alpha=0.2, zorder=2, interpolate=True)
            
            ni, nj, _ = self.modelo.elementos[id_elem]
            ax.scatter([0, longitud], [y[0], y[-1]], color='red', zorder=5, s=50)
            
            y_lims = ax.get_ylim(); y_offset_barra = (y_lims[1] - y_lims[0]) * 0.05 if y_lims[1] > y_lims[0] else 0.1
            ax.text(0, -y_offset_barra, f" ni={ni}", color='black', ha='left', va='top')
            ax.text(longitud, -y_offset_barra, f" nj={nj} ", color='black', ha='right', va='top')
            ax.text(longitud / 2, -y_offset_barra, f"E{id_elem}", color='#000080', ha='center', va='top', weight='bold')

            y_inicio, y_fin = y[0], y[-1]
            ax.text(x[0], y_inicio, f" {self._format_value(y_inicio)}", color="black", ha='left', va='center')
            ax.text(x[-1], y_fin, f"{self._format_value(y_fin)} ", color="black", ha='right', va='center')

            idx_max, y_max = np.argmax(y), np.max(y)
            idx_min, y_min = np.argmin(y), np.min(y)
            puntos_extremos_indices = {0, len(y) - 1}
            
            if idx_max not in puntos_extremos_indices and abs(y_max) > 1e-9:
                ax.scatter(x[idx_max], y_max, color='black', zorder=4, s=30)
                ax.text(x[idx_max], y_max, f" {self._format_value(y_max)}", color='black', ha='center', va='bottom')
                
            if idx_min not in puntos_extremos_indices and abs(y_min) > 1e-9:
                ax.scatter(x[idx_min], y_min, color='magenta', zorder=4, s=30)
                ax.text(x[idx_min], y_min, f" {self._format_value(y_min)}", color='magenta', ha='center', va='top')

        if self.check_mostrar_armado.isChecked():  
            lista_armados = self.modelo.armados_diseno.get(id_elem, [])
            if lista_armados:
                armados_superiores = [a for a in lista_armados if a['posicion'] == 'Superior']
                armados_inferiores = [a for a in lista_armados if a['posicion'] == 'Inferior']
                
                y_min, y_max = ax.get_ylim()
                rango_y = y_max - y_min
                offset_vertical = rango_y * 0.05 

                nivel_y_actual = y_max - offset_vertical * 1.5
                for armado in armados_superiores:
                    x_ini, x_fin = armado['desde'], armado['hasta']
                    texto_armado = f"{armado['cantidad']}Ø{armado['diametro']}"
                    
                    ax.plot([x_ini, x_fin], [nivel_y_actual, nivel_y_actual], color='#D32F2F', linewidth=2.5, solid_capstyle='butt', zorder=20)
                    
                    ax.text((x_ini + x_fin) / 2, nivel_y_actual, texto_armado, 
                            color='black', ha='center', va='bottom', fontsize=9, weight='bold', zorder=21, 
                            bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="#D32F2F", lw=1.5, alpha=0.9))
                    
                    nivel_y_actual -= offset_vertical

                nivel_y_actual = y_min + offset_vertical * 1.5 
                for armado in armados_inferiores:
                    x_ini, x_fin = armado['desde'], armado['hasta']
                    texto_armado = f"{armado['cantidad']}Ø{armado['diametro']}"
                    
                    ax.plot([x_ini, x_fin], [nivel_y_actual, nivel_y_actual], color='#D32F2F', linewidth=2.5, solid_capstyle='butt', zorder=20)
                    
                    ax.text((x_ini + x_fin) / 2, nivel_y_actual, texto_armado, 
                            color='black', ha='center', va='top', fontsize=9, weight='bold', zorder=21, 
                            bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="#D32F2F", lw=1.5, alpha=0.9))
                    
                    nivel_y_actual += offset_vertical
        
        ax.set_xlim(0, longitud)
        ax.margins(x=0.05, y=0.15)
        self.grafico_widget.lienzo.draw()

    def _get_color_por_nombre(self, nombre_combo):
        colores_fijos = {"Cálculo Simple": "#33B2FF", "1.4D": "#FFB000", "1.2D + 1.6L + 0.5Lr": "#2ECC71", "1.2D + 1.6Lr + 1.0L": "#27AE60", "1.2D + 1.0W + 1.0L + 0.5Lr": "#E74C3C", "0.9D + 1.0W": "#8E44AD"}
        if nombre_combo in colores_fijos: return colores_fijos[nombre_combo]
        if nombre_combo not in self._cache_colores_usuario:
            paleta_reserva = ["#F39C12", "#D35400", "#C0392B", "#BDC3C7", "#7F8C8D", "#16A085", "#2980B9", "#8E44AD", "#2C3E50", "#E67E22"]
            self._cache_colores_usuario[nombre_combo] = paleta_reserva[sum(ord(c) for c in nombre_combo) % len(paleta_reserva)]
        return self._cache_colores_usuario[nombre_combo]
    
    def _format_value(self, value, precision=2):
        if abs(value) < 1e-9: return f"0.{'0'*precision}"
        return f"{value:.{precision}f}"

    def on_diagram_click(self, event):
        if event.inaxes != self.grafico_widget.ejes or self.current_x is None: return
        self._mostrar_etiqueta_en_coordenada_x(event.xdata)
        if self.click_annotation: self.click_annotation.remove()
        x_click = event.xdata
        longitud_total = self.current_x[-1]
        if self.current_y is not None:
            if 0 <= x_click <= longitud_total:
                y_interpolado = np.interp(x_click, self.current_x, self.current_y)
                efecto_nombre = self.combo_efectos.currentText().split(' ')[0]
                texto_etiqueta = (f"x={self._format_value(x_click)}, {efecto_nombre}={self._format_value(y_interpolado)}")
                self.click_annotation = self.grafico_widget.ejes.annotate(texto_etiqueta, xy=(x_click, y_interpolado), xytext=(5, 15), textcoords="offset points", ha='left', va='bottom', bbox=dict(boxstyle='round,pad=0.5', fc='white', ec="#ff0000", lw=1), arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0.1', color='red'), color='black', zorder=10)
        elif self.current_envelope_max is not None:
            if 0 <= x_click <= longitud_total:
                y_max_interp = np.interp(x_click, self.current_x, self.current_envelope_max)
                y_min_interp = np.interp(x_click, self.current_x, self.current_envelope_min)
                texto_etiqueta = (f"x={self._format_value(x_click)}\nMáx[+]={self._format_value(y_max_interp)}\nMáx[-]={self._format_value(y_min_interp)}")
                self.click_annotation = self.grafico_widget.ejes.annotate(texto_etiqueta, xy=(x_click, 0), xytext=(5, 15), textcoords="offset points", ha='left', va='bottom', bbox=dict(boxstyle='round,pad=0.5', fc='white', ec="#ff0000", lw=1), arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0.1', color='red'), color='black', zorder=10)
        self.grafico_widget.lienzo.draw()

    def _mostrar_etiqueta_en_coordenada_x(self, x_coord):
        if self.current_x is None: return
        if self.click_annotation: self.click_annotation.remove(); self.click_annotation = None
        longitud_total = self.current_x[-1]
        if not (0 <= x_coord <= longitud_total): QMessageBox.warning(self, "Valor fuera de rango", f"La coordenada x debe estar entre 0 y {longitud_total:.2f} m."); self.grafico_widget.lienzo.draw(); return
        texto_etiqueta = ""; y_pos_etiqueta = 0
        if self.current_y is not None:
            y_interpolado = np.interp(x_coord, self.current_x, self.current_y)
            efecto_nombre = self.combo_efectos.currentText().split(' ')[0]
            texto_etiqueta = f"x={self._format_value(x_coord)}\n{efecto_nombre}={self._format_value(y_interpolado)}"; y_pos_etiqueta = y_interpolado
        elif self.current_envelope_max is not None:
            y_max_interp = np.interp(x_coord, self.current_x, self.current_envelope_max)
            y_min_interp = np.interp(x_coord, self.current_x, self.current_envelope_min)
            texto_etiqueta = f"x={self._format_value(x_coord)}\nMáx[+]={self._format_value(y_max_interp)}\nMáx[-]={self._format_value(y_min_interp)}"; y_pos_etiqueta = 0
        if not texto_etiqueta: return
        self.click_annotation = self.grafico_widget.ejes.annotate(texto_etiqueta, xy=(x_coord, y_pos_etiqueta), xytext=(5, 15), textcoords="offset points", ha='left', va='bottom', bbox=dict(boxstyle='round,pad=0.5', fc='white', ec="#ff0000", lw=1), arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0.1', color='red'), color='black', zorder=10)
        self.grafico_widget.lienzo.draw()

    def _on_buscar_por_valor_click(self):
        for ann in self.search_annotations: ann.remove()
        self.search_annotations.clear()
        if self.current_x is None or (self.current_y is None and self.current_envelope_max is None): self.grafico_widget.lienzo.draw(); return
        try: valor_buscado = float(self.entrada_valor_y.text())
        except (ValueError, TypeError): QMessageBox.warning(self, "Entrada no válida", "Introduce un valor numérico para el esfuerzo."); return
        puntos_encontrados_x = []
        def buscar_en_curva(y_data, valor_y):
            puntos_x = []
            for i in range(len(y_data) - 1):
                y1, y2 = y_data[i], y_data[i+1]
                if (y1 <= valor_y <= y2) or (y2 <= valor_y <= y1):
                    if abs(y2 - y1) < 1e-9:
                        if abs(valor_y - y1) < 1e-9: puntos_x.append(self.current_x[i])
                    else:
                        x1, x2 = self.current_x[i], self.current_x[i+1]; x_interp = x1 + (x2 - x1) * (valor_y - y1) / (y2 - y1); puntos_x.append(x_interp)
            return puntos_x
        if self.current_y is not None: puntos_encontrados_x.extend(buscar_en_curva(self.current_y, valor_buscado))
        elif self.current_envelope_max is not None:
            if valor_buscado >= 0: puntos_encontrados_x.extend(buscar_en_curva(self.current_envelope_max, valor_buscado))
            if valor_buscado <= 0: puntos_encontrados_x.extend(buscar_en_curva(self.current_envelope_min, valor_buscado))
        if not puntos_encontrados_x: QMessageBox.information(self, "Búsqueda", f"No se encontraron puntos con el valor {valor_buscado:.2f}.")
        else:
            for x_encontrado in puntos_encontrados_x:
                y_real = np.interp(x_encontrado, self.current_x, self.current_y) if self.current_y is not None else valor_buscado
                etiqueta = self.grafico_widget.ejes.annotate(f"x={x_encontrado:.2f}", xy=(x_encontrado, y_real), xytext=(0, -25), textcoords="offset points", ha='center', va='top', bbox=dict(boxstyle='round,pad=0.3', fc='white', ec="#0077ff", lw=1), arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0.1', color='#0077ff'), color='black', zorder=11)
                self.search_annotations.append(etiqueta)
        self.grafico_widget.lienzo.draw()

    def _on_mostrar_valor_click(self):
        texto_x = self.entrada_x.text().replace(',', '.')
        try: x_coord = float(texto_x); self._mostrar_etiqueta_en_coordenada_x(x_coord)
        except ValueError: QMessageBox.warning(self, "Entrada no válida", "Por favor, ingrese un valor numérico para la coordenada x.")

    def _guardar_armado_manual(self):
        id_elem_str = self.combo_elementos.currentText()
        if not id_elem_str or "No hay" in id_elem_str: QMessageBox.warning(self, "Error", "Seleccione un elemento de viga válido primero."); return
        id_elem = int(id_elem_str); tipo_armado = self.tipo_armado_combo.currentText()
        nuevo_armado = {"descripcion": self.descripcion_armado_input.text() or "Armado", "tipo": tipo_armado, "cantidad": self.cantidad_armado_input.value(), "diametro": int(self.diametro_armado_combo.currentText()), "desde": self.desde_armado_input.value(), "hasta": self.hasta_armado_input.value()}
        if tipo_armado == "Flexión": nuevo_armado["posicion"] = self.posicion_armado_combo.currentText(); nuevo_armado["separacion"] = None
        else: nuevo_armado["posicion"] = "N/A"; nuevo_armado["separacion"] = self.separacion_armado_input.value()
        if id_elem not in self.modelo.armados_diseno: self.modelo.armados_diseno[id_elem] = []
        self.modelo.armados_diseno[id_elem].append(nuevo_armado); self.modelo.modificado = True
        self.enviar_mensaje_statusbar.emit(f"Armado de {tipo_armado.lower()} guardado para el elemento {id_elem}.", 3000)
        self._refrescar_tabla_armado(); self._refrescar_combo_armado_previo()

    def _eliminar_armado_seleccionado(self):
        id_elem_str = self.combo_elementos.currentText()
        if not id_elem_str or "No hay" in id_elem_str: return
        id_elem = int(id_elem_str); fila_seleccionada = self.tabla_armado.currentRow()
        if fila_seleccionada < 0: QMessageBox.information(self, "Aviso", "Seleccione una fila de la tabla para eliminar."); return
        if id_elem in self.modelo.armados_diseno and len(self.modelo.armados_diseno[id_elem]) > fila_seleccionada:
            self.modelo.armados_diseno[id_elem].pop(fila_seleccionada); self.modelo.modificado = True
            self.enviar_mensaje_statusbar.emit("Armado eliminado.", 3000); self._refrescar_tabla_armado()

    def _refrescar_tabla_armado(self):
        self.tabla_armado.blockSignals(True); self.tabla_armado.setRowCount(0) 
        id_elem_str = self.combo_elementos.currentText()
        if not id_elem_str or "No hay" in id_elem_str: self.tabla_armado.blockSignals(False); return
        id_elem = int(id_elem_str); lista_armados = self.modelo.armados_diseno.get(id_elem, [])
        for armado in lista_armados:
            fila = self.tabla_armado.rowCount(); self.tabla_armado.insertRow(fila)
            tipo = armado.get('tipo', 'Flexión'); posicion = armado.get('posicion', 'N/A'); separacion = armado.get('separacion')
            texto_armado = f"{armado['cantidad']}Ø{armado['diametro']}"; texto_separacion = f"{separacion:.1f}" if tipo == "Corte" and separacion is not None else ""; texto_posicion = posicion if tipo == "Flexión" else ""
            self.tabla_armado.setItem(fila, 0, QTableWidgetItem(armado['descripcion']))
            self.tabla_armado.setItem(fila, 1, QTableWidgetItem(tipo))
            self.tabla_armado.setItem(fila, 2, QTableWidgetItem(texto_armado))
            self.tabla_armado.setItem(fila, 3, QTableWidgetItem(f"{armado['desde']:.2f}"))
            self.tabla_armado.setItem(fila, 4, QTableWidgetItem(f"{armado['hasta']:.2f}"))
            self.tabla_armado.setItem(fila, 5, QTableWidgetItem(texto_posicion))
            self.tabla_armado.setItem(fila, 6, QTableWidgetItem(texto_separacion))
        self.tabla_armado.blockSignals(False); self.btn_guardar_cambios_tabla_armado.setEnabled(False)

    def _marcar_cambios_tabla_armado(self, item): self.btn_guardar_cambios_tabla_armado.setEnabled(True)

    def _guardar_cambios_de_tabla_armado(self):
        id_elem_str = self.combo_elementos.currentText()
        if not id_elem_str or "No hay" in id_elem_str: return
        id_elem = int(id_elem_str); nuevos_armados_para_elemento = []
        try:
            for fila in range(self.tabla_armado.rowCount()):
                descripcion = self.tabla_armado.item(fila, 0).text()
                tipo = self.tabla_armado.item(fila, 1).text()
                armado_str = self.tabla_armado.item(fila, 2).text().upper()
                desde_str = self.tabla_armado.item(fila, 3).text().replace(',', '.')
                hasta_str = self.tabla_armado.item(fila, 4).text().replace(',', '.')
                posicion = self.tabla_armado.item(fila, 5).text()
                separacion_str = self.tabla_armado.item(fila, 6).text().replace(',', '.')
                if 'Ø' not in armado_str: raise ValueError(f"Fila {fila + 1}: El formato del armado debe ser 'CantØDiam'.")
                partes_armado = armado_str.split('Ø'); cantidad = int(partes_armado[0]); diametro = int(partes_armado[1])
                armado_dict = {"descripcion": descripcion, "tipo": tipo, "cantidad": cantidad, "diametro": diametro, "desde": float(desde_str), "hasta": float(hasta_str)}
                if tipo == "Flexión":
                    if posicion not in ["Superior", "Inferior"]: raise ValueError(f"Fila {fila + 1}: La posición para flexión debe ser 'Superior' o 'Inferior'.")
                    armado_dict["posicion"] = posicion; armado_dict["separacion"] = None
                elif tipo == "Corte": armado_dict["posicion"] = "N/A"; armado_dict["separacion"] = float(separacion_str)
                else: raise ValueError(f"Fila {fila + 1}: El tipo debe ser 'Flexión' o 'Corte'.")
                nuevos_armados_para_elemento.append(armado_dict)
            self.modelo.armados_diseno[id_elem] = nuevos_armados_para_elemento; self.modelo.modificado = True
            self.enviar_mensaje_statusbar.emit(f"Cambios de armado para viga {id_elem} guardados.", 4000); self.refrescar_diagrama()
        except (ValueError, IndexError, TypeError) as e:
            QMessageBox.critical(self, "Error de Datos", f"No se pudieron guardar los cambios.\n\nError: {e}"); self._refrescar_tabla_armado()

class ColumnCanvas(QWidget):
    """Lienzo para dibujar la sección transversal de la columna (Siempre fondo blanco)."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(300)
        self.column_data = {}
        self.setStyleSheet("background-color: white; border: 1px solid #ccc;")

    def update_data(self, data):
        self.column_data = data
        self.update() 

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        painter.fillRect(self.rect(), Qt.white)
        
        if not self.column_data or self.column_data.get('b', 0) == 0: return

        b, h = self.column_data['b'], self.column_data['h']
        eje = self.column_data.get('eje', 'fuerte')
        
        margin = 40
        canvas_w, canvas_h = self.width() - 2*margin, self.height() - 2*margin
        scale = min(canvas_w / b, canvas_h / h)
        
        draw_b, draw_h = b * scale, h * scale
        start_x = (self.width() - draw_b) / 2
        start_y = (self.height() - draw_h) / 2

        # Dibujar Sección de Concreto
        painter.setBrush(QBrush(QColor("#e0e0e0"))) # Gris claro concreto
        pen_columna = QPen(Qt.black, 2)
        painter.setPen(pen_columna)
        painter.drawRect(start_x, start_y, draw_b, draw_h)
        
        # Dibujar Estribo
        rec = self.column_data.get('rec', 40)
        est_x, est_y = start_x + rec * scale, start_y + rec * scale
        est_b, est_h = draw_b - 2 * rec * scale, draw_h - 2 * rec * scale
        
        painter.setBrush(Qt.NoBrush)
        pen_estribo = QPen(QColor("#c62828"), 2) # Rojo oscuro
        painter.setPen(pen_estribo)
        painter.drawRect(est_x, est_y, est_b, est_h)
        
        # Dibujar Barras Longitudinales
        acero = self.column_data.get('acero', [])
        d_barra = self.column_data.get('d_barra', 0)
        radius = (d_barra / 2) * scale
        
        painter.setPen(Qt.black)
        painter.setBrush(QBrush(Qt.black)) # Barras negras
        
        for barra in acero:
            cx = start_x + barra['x'] * scale
            cy = start_y + barra['y'] * scale
            painter.drawEllipse(QPointF(cx, cy), radius, radius)
            
        # Cotas y Ejes (Texto Negro)
        painter.setPen(Qt.black)
        painter.setFont(QFont("Arial", 9))
        painter.drawText(int(start_x + draw_b/2 - 20), int(start_y + draw_h + 20), f"b={b:.0f}")
        painter.drawText(int(start_x - 35), int(start_y + draw_h/2), f"h={h:.0f}")
        
        # Eje de Flexión
        pen_eje = QPen(QColor("blue"), 1, Qt.DashLine)
        painter.setPen(pen_eje)
        if eje == 'fuerte': # Momento alrededor de X (Eje horizontal dibujado)
            mid_y = start_y + draw_h/2
            painter.drawLine(start_x - 10, mid_y, start_x + draw_b + 10, mid_y)
            painter.drawText(int(start_x + draw_b + 15), int(mid_y + 5), "X (Fuerte)")
        else: # Momento alrededor de Y
            mid_x = start_x + draw_b/2
            painter.drawLine(mid_x, start_y - 10, mid_x, start_y + draw_h + 10)
            painter.drawText(int(mid_x - 10), int(start_y - 15), "Y (Débil)")


class PaginaColumnas(QWidget):
    enviar_mensaje_statusbar = Signal(str, int)

    def __init__(self, modelo):
        super().__init__()
        self.modelo = modelo
        self.generador_diagramas = None
        self.puntos_demanda = [] 
        self.ventana_3d = None
        self.puntos_nom_fuerte = []
        self.puntos_dis_fuerte = []
        self.puntos_nom_debil = []
        self.puntos_dis_debil = []
        layout_principal = QHBoxLayout(self)
        contenedor_izq = QWidget()
        contenedor_izq.setMinimumWidth(350)
        contenedor_izq.setMaximumWidth(500)
        layout_izq = QVBoxLayout(contenedor_izq)
        layout_izq.setContentsMargins(0, 0, 0, 0)
        scroll_izq = QScrollArea()
        scroll_izq.setWidgetResizable(True)
        scroll_izq.setFrameShape(QFrame.Shape.NoFrame)
        widget_contenido_scroll = QWidget()
        layout_contenido_scroll = QVBoxLayout(widget_contenido_scroll)
        layout_contenido_scroll.setContentsMargins(0,0,5,0) 

        self.tabs_inputs = QTabWidget()
        self._crear_tabs_inputs()
        layout_contenido_scroll.addWidget(self.tabs_inputs)

        self.canvas_columna = ColumnCanvas()
        layout_contenido_scroll.addWidget(self.canvas_columna)
        
        layout_contenido_scroll.addStretch()

        scroll_izq.setWidget(widget_contenido_scroll)
        
        layout_izq.addWidget(scroll_izq)
        
        layout_principal.addWidget(contenedor_izq)

        contenedor_der = QWidget()
        layout_der = QVBoxLayout(contenedor_der)
        layout_der.setContentsMargins(0, 0, 0, 0)

        # 1. Tabla de Puntos (Zona Superior)
        grupo_puntos = QGroupBox("Puntos de Diseño (Demandas)")
        layout_puntos = QVBoxLayout(grupo_puntos)
        
        self.tabla_puntos = QTableWidget(0, 6)
        self.tabla_puntos.setHorizontalHeaderLabels(["Caso", "Pu (kN)", "Mux (kN·m)", "Muy (kN·m)", "Estado", "Ratio D/C"])
        self.tabla_puntos.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tabla_puntos.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tabla_puntos.setMinimumHeight(150)
        self.tabla_puntos.setMaximumHeight(200)
        layout_puntos.addWidget(self.tabla_puntos)

        hbox_btns_puntos = QHBoxLayout()
        self.btn_importar_esfuerzos = QPushButton("Importar del Análisis")
        self.btn_agregar_manual = QPushButton("Añadir Manual")
        self.btn_borrar_puntos = QPushButton("Borrar Selec.")
        
        hbox_btns_puntos.addWidget(self.btn_importar_esfuerzos)
        hbox_btns_puntos.addWidget(self.btn_agregar_manual)
        hbox_btns_puntos.addWidget(self.btn_borrar_puntos)
        layout_puntos.addLayout(hbox_btns_puntos)
        
        layout_der.addWidget(grupo_puntos)

        # 2. Pestañas de Resultados
        self.tabs_resultados = QTabWidget()
        
        # --- TAB 1: Interacción (CON CHECKBOX) ---
        self.tab_interaccion = QWidget()
        l_inter = QVBoxLayout(self.tab_interaccion)
        
        hbox_opciones_grafico = QHBoxLayout()
        self.check_mostrar_valores = QCheckBox("Mostrar valores extremos en el diagrama")
        self.check_mostrar_valores.setChecked(True) # Activado por defecto
        hbox_opciones_grafico.addWidget(self.check_mostrar_valores)
        hbox_opciones_grafico.addStretch()
        l_inter.addLayout(hbox_opciones_grafico)
        
        contenedor_plot_inter = QWidget()
        contenedor_plot_inter.setStyleSheet("background-color: white; color: black; border-radius: 4px;")
        l_plot_inter = QVBoxLayout(contenedor_plot_inter)
        
        self.plot_canvas_interaccion = FigureCanvas(Figure())
        self.ax_interaccion = self.plot_canvas_interaccion.figure.subplots()
        l_plot_inter.addWidget(self.plot_canvas_interaccion)
        
        l_inter.addWidget(contenedor_plot_inter)
        self.tabs_resultados.addTab(self.tab_interaccion, "Diagrama de Interacción")

        # --- TAB 2: Esfuerzos ---
        self.tab_esfuerzos = self._crear_panel_diagramas_vortex()
        self.tabs_resultados.addTab(self.tab_esfuerzos, "Diagramas de Esfuerzos")

        # --- TAB 3: Reporte ---
        self.tab_reporte = QWidget()
        l_rep = QVBoxLayout(self.tab_reporte)
        self.scroll_reporte = QScrollArea()
        self.scroll_reporte.setWidgetResizable(True)
        self.scroll_reporte.setFrameShape(QFrame.Shape.NoFrame)
        self.contenedor_reporte = QWidget()
        self.contenedor_reporte.setStyleSheet("background-color: white; color: black;")
        self.layout_reporte_contenido = QVBoxLayout(self.contenedor_reporte)
        self.layout_reporte_contenido.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.scroll_reporte.setWidget(self.contenedor_reporte)
        l_rep.addWidget(self.scroll_reporte)
        
        self.tabs_resultados.addTab(self.tab_reporte, "Memoria de Cálculo")

        layout_der.addWidget(self.tabs_resultados)
        layout_principal.addWidget(contenedor_der)

        self._conectar_senales()
        self.setEnabled(False)
        self._actualizar_preview_seccion()

    def _crear_tabs_inputs(self):
        # --- TAB FLEXO-COMPRESIÓN ---
        w_flex = QWidget()
        l_flex = QVBoxLayout(w_flex)
        
        # Grupo Materiales
        g_mat = QGroupBox("Materiales"); l_mat = QFormLayout(g_mat)
        self.fc_input = QLineEdit("25"); l_mat.addRow("f'c [MPa]:", self.fc_input)
        self.fy_input = QLineEdit("420"); l_mat.addRow("fy [MPa]:", self.fy_input)
        l_flex.addWidget(g_mat)

        # Grupo Geometría
        g_geo = QGroupBox("Geometría"); l_geo = QFormLayout(g_geo)
        self.b_input = QLineEdit("30"); l_geo.addRow("Base (b) [cm]:", self.b_input)
        self.h_input = QLineEdit("30"); l_geo.addRow("Altura (h) [cm]:", self.h_input)
        self.rec_input = QLineEdit("3"); l_geo.addRow("Recubrimiento [cm]:", self.rec_input)
        
        self.radio_eje_fuerte = QRadioButton("Eje Fuerte (Mx)")
        self.radio_eje_debil = QRadioButton("Eje Débil (My)")
        self.radio_eje_fuerte.setChecked(True)
        hbox_ejes = QHBoxLayout(); hbox_ejes.addWidget(self.radio_eje_fuerte); hbox_ejes.addWidget(self.radio_eje_debil)
        l_geo.addRow("Eje de Análisis:", hbox_ejes)
        l_flex.addWidget(g_geo)

        # Grupo Refuerzo
        g_ref = QGroupBox("Refuerzo"); l_ref = QFormLayout(g_ref)
        self.d_barra_input = QLineEdit("16"); l_ref.addRow("Ø Long [mm]:", self.d_barra_input)
        self.d_est_input = QLineEdit("8"); l_ref.addRow("Ø Estribo [mm]:", self.d_est_input)
        self.nh_input = QLineEdit("3"); l_ref.addRow("Barras en H:", self.nh_input)
        self.nb_input = QLineEdit("3"); l_ref.addRow("Barras en B:", self.nb_input)
        l_flex.addWidget(g_ref)

        # Botones Acción
        hbox_btns = QHBoxLayout()
        self.btn_calc_diagramas = QPushButton("Calcular Diagramas")
        self.btn_calc_diagramas.setStyleSheet("background-color: #1976D2; color: white; font-weight: bold; padding: 5px;")
        self.btn_ver_3d = QPushButton("Ver 3D")
        hbox_btns.addWidget(self.btn_calc_diagramas); hbox_btns.addWidget(self.btn_ver_3d)
        l_flex.addLayout(hbox_btns)
        
        self.tabs_inputs.addTab(w_flex, "Flexo-Compresión")

        # --- TAB CORTE ---
        w_cort = QWidget()
        l_cort = QFormLayout(w_cort)
        l_cort.addRow(QLabel("<i>Usa geometría definida en Flexión.</i>"))
        self.vu_input = QLineEdit("50"); l_cort.addRow("Vu [kN]:", self.vu_input)
        self.nu_input = QLineEdit("100"); l_cort.addRow("Nu [kN]:", self.nu_input)
        
        self.btn_calc_corte = QPushButton("Diseñar a Corte")
        self.btn_calc_corte.setStyleSheet("background-color: #388E3C; color: white; font-weight: bold; padding: 5px;")
        l_cort.addRow(self.btn_calc_corte)
        
        self.tabs_inputs.addTab(w_cort, "Corte")

    def _crear_panel_diagramas_vortex(self):
        """Crea el panel de diagramas de fuerzas (Axial, Momento, Corte) estilo Vortex."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # Controles
        hbox = QHBoxLayout()
        self.combo_elementos_vortex = QComboBox() # Solo columnas
        self.combo_combos_vortex = QComboBox()
        self.combo_casos_vortex = QComboBox()
        self.combo_efecto_vortex = QComboBox()
        self.combo_efecto_vortex.addItems(['Axial (Px)', 'Momento (Mz)', 'Momento (My)', 'Cortante (Py)', 'Cortante (Pz)'])
        
        hbox.addWidget(QLabel("Columna:")); hbox.addWidget(self.combo_elementos_vortex)
        hbox.addWidget(QLabel("Combo:")); hbox.addWidget(self.combo_combos_vortex)
        hbox.addWidget(QLabel("Caso:")); hbox.addWidget(self.combo_casos_vortex)
        hbox.addWidget(QLabel("Efecto:")); hbox.addWidget(self.combo_efecto_vortex)
        layout.addLayout(hbox)

        # Gráfico (Hardcoded Light Mode)
        contenedor_graf = QWidget()
        contenedor_graf.setStyleSheet("background-color: white; color: black;")
        l_graf = QVBoxLayout(contenedor_graf); l_graf.setContentsMargins(0,0,0,0)
        
        self.grafico_vortex = MatplotlibWidget() 
        l_graf.addWidget(self.grafico_vortex)
        layout.addWidget(contenedor_graf)
        
        return panel

    def _conectar_senales(self):
        # Inputs -> Preview
        for w in [self.b_input, self.h_input, self.rec_input, self.nh_input, self.nb_input, self.d_barra_input, self.d_est_input]:
            w.textChanged.connect(self._actualizar_preview_seccion)
        self.radio_eje_fuerte.toggled.connect(self._actualizar_preview_seccion)
        self.radio_eje_fuerte.toggled.connect(self._actualizar_grafico_interaccion)

        # Botones Principales
        self.btn_calc_diagramas.clicked.connect(self._calcular_diagramas_interaccion)
        self.btn_ver_3d.clicked.connect(self._abrir_visor_3d)
        self.btn_calc_corte.clicked.connect(self._calcular_diseno_corte)
        
        # Botones Puntos
        self.btn_importar_esfuerzos.clicked.connect(self._importar_esfuerzos)
        self.btn_agregar_manual.clicked.connect(self._agregar_punto_manual)
        self.btn_borrar_puntos.clicked.connect(self._borrar_puntos_seleccionados)

        # Combos Vortex
        self.combo_elementos_vortex.currentIndexChanged.connect(self._refrescar_diagrama_vortex)
        self.combo_combos_vortex.currentIndexChanged.connect(self._actualizar_casos_vortex)
        self.combo_casos_vortex.currentIndexChanged.connect(self._refrescar_diagrama_vortex)
        self.combo_efecto_vortex.currentIndexChanged.connect(self._refrescar_diagrama_vortex)
        
        self.check_mostrar_valores.toggled.connect(self._actualizar_grafico_interaccion)

    def actualizar(self, modelo):
        """Se llama al cargar/calcular el modelo principal."""
        self.modelo = modelo
        self.generador_diagramas = GeneradorDiagramas(modelo)
        
        # Habilitar si hay resultados
        tiene_res = bool(modelo.resultados_calculo)
        self.setEnabled(True) # Permitir editar geometría siempre
        self.btn_importar_esfuerzos.setEnabled(tiene_res)
        
        # Poblar Combos de Columnas (Elementos verticales)
        self.combo_elementos_vortex.clear()
        ids_cols = []
        for id_elem, (ni, nj, _) in modelo.elementos.items():
            # Criterio simple: nodos con casi misma X e Y
            n1 = modelo.nodos[ni]; n2 = modelo.nodos[nj]
            if abs(n1[0]-n2[0]) < 0.01 and abs(n1[1]-n2[1]) < 0.01:
                ids_cols.append(id_elem)
        
        if ids_cols:
            self.combo_elementos_vortex.addItems([str(i) for i in sorted(ids_cols)])
        else:
            self.combo_elementos_vortex.addItem("N/A")

        # Poblar Combos de Carga
        self.combo_combos_vortex.blockSignals(True) 
        self.combo_combos_vortex.clear()
        
        if tiene_res:
            claves = [k for k in modelo.resultados_calculo.keys() if k != 'reporte_global_data']
            self.combo_combos_vortex.addItems(claves)
            self._actualizar_casos_vortex()
            
        self.combo_combos_vortex.blockSignals(False)

    def _recolectar_datos_seccion(self):
        try:
            b = float(self.b_input.text()) * 10 # cm -> mm
            h = float(self.h_input.text()) * 10
            rec = float(self.rec_input.text()) * 10
            d_barra = float(self.d_barra_input.text())
            d_est = float(self.d_est_input.text())
            nh = int(self.nh_input.text())
            nb = int(self.nb_input.text())
            fc = float(self.fc_input.text())
            fy = float(self.fy_input.text())
            
            acero = generar_acero_automatico(b, h, rec, d_est, d_barra, nh, nb)
            
            return {
                'b': b, 'h': h, 'rec': rec, 'd_barra': d_barra, 'd_est': d_est,
                'nh': nh, 'nb': nb, 'fc': fc, 'fy': fy, 'acero': acero
            }
        except ValueError:
            return None

    def _actualizar_preview_seccion(self):
        datos = self._recolectar_datos_seccion()
        if datos:
            datos['eje'] = 'fuerte' if self.radio_eje_fuerte.isChecked() else 'debil'
            self.canvas_columna.update_data(datos)

    def _calcular_diagramas_interaccion(self):
        if not MODULES_COLUMNAS_LOADED: return
        datos = self._recolectar_datos_seccion()
        if not datos: 
            QMessageBox.warning(self, "Error", "Revise los datos numéricos.")
            return

        self.enviar_mensaje_statusbar.emit("Calculando diagramas de interacción...", 0)
        QApplication.processEvents()

        # Calcular ambos ejes
        self.puntos_nom_fuerte, self.puntos_dis_fuerte = generar_diagrama_interaccion(
            datos['fc'], datos['fy'], datos['b'], datos['h'], datos['acero'], 'fuerte')
        self.puntos_nom_debil, self.puntos_dis_debil = generar_diagrama_interaccion(
            datos['fc'], datos['fy'], datos['b'], datos['h'], datos['acero'], 'debil')
        
        self._actualizar_grafico_interaccion()
        self.enviar_mensaje_statusbar.emit("Diagramas calculados.", 3000)
        self.tabs_resultados.setCurrentIndex(0) 

    def _actualizar_grafico_interaccion(self):
        """Dibuja el diagrama de interacción Pn-Mn replicando el estilo original."""
        self.ax_interaccion.clear()
        
        # Configuración "Hardcoded Light"
        self.plot_canvas_interaccion.figure.set_facecolor('white')
        self.ax_interaccion.set_facecolor('white')
        self.ax_interaccion.tick_params(colors='black')
        self.ax_interaccion.xaxis.label.set_color('black')
        self.ax_interaccion.yaxis.label.set_color('black')
        self.ax_interaccion.title.set_color('black')
        for spine in self.ax_interaccion.spines.values(): 
            spine.set_edgecolor('black')

        eje = 'fuerte' if self.radio_eje_fuerte.isChecked() else 'debil'
        nom = self.puntos_nom_fuerte if eje == 'fuerte' else self.puntos_nom_debil
        dis = self.puntos_dis_fuerte if eje == 'fuerte' else self.puntos_dis_debil
        
        if not nom: 
            self.plot_canvas_interaccion.draw()
            return

        # 1. Dibujar Curvas
        self.ax_interaccion.plot([p[0]/1e6 for p in nom], [p[1]/1000 for p in nom], 
                                 label='Nominal', color='royalblue', linewidth=2)
        self.ax_interaccion.plot([p[0]/1e6 for p in dis], [p[1]/1000 for p in dis], 
                                 label='Diseño', color='red', linestyle='--', linewidth=2)
        
        # 2. Dibujar Puntos Críticos (Estilo Original con BBOX)
        if self.check_mostrar_valores.isChecked():
            # --- Puntos Nominales ---
            if nom:
                # Pn Max (Compresión)
                p_max_comp = nom[0]
                mx_c, pn_c = p_max_comp[0] / 1e6, p_max_comp[1] / 1000
                self.ax_interaccion.plot(mx_c, pn_c, 'o', color='darkorange', markersize=8)
                self.ax_interaccion.text(mx_c + 5, pn_c, f" Pn={pn_c:.1f} kN",
                                         va='center', color='darkorange', fontweight='bold',
                                         bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="darkorange", lw=1, alpha=0.8))

                # Pn Min (Tracción)
                p_max_trac = nom[-1]
                mx_t, pn_t = p_max_trac[0] / 1e6, p_max_trac[1] / 1000
                self.ax_interaccion.plot(mx_t, pn_t, 'o', color='purple', markersize=8)
                self.ax_interaccion.text(mx_t + 5, pn_t - 10, f" Pn={pn_t:.1f} kN",
                                         va='top', color='purple', fontweight='bold',
                                         bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="purple", lw=1, alpha=0.8))

                # Mn Max (Balanceado)
                p_max_mom = max(nom, key=lambda item: item[0])
                mx_m, pn_m = p_max_mom[0] / 1e6, p_max_mom[1] / 1000
                self.ax_interaccion.plot(mx_m, pn_m, 'o', color='green', markersize=8)
                self.ax_interaccion.text(mx_m - 3, pn_m, f"Mn={mx_m:.1f} kN·m\nPn={pn_m:.1f} kN",
                                         ha='right', va='center', color='green', fontweight='bold',
                                         bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="green", lw=1, alpha=0.8))

            # --- Puntos de Diseño ---
            if dis:
                # Phi Pn Max
                p_d_comp = dis[0]
                mx_dc, pn_dc = p_d_comp[0] / 1e6, p_d_comp[1] / 1000
                self.ax_interaccion.plot(mx_dc, pn_dc, 'X', color='maroon', markersize=8)
                self.ax_interaccion.text(mx_dc + 5, pn_dc, f" ΦPn={pn_dc:.1f} kN",
                                         va='center', color='maroon', fontweight='bold',
                                         bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="maroon", lw=1, alpha=0.8))
                
                # Phi Pn Min
                p_d_trac = dis[-1]
                mx_dt, pn_dt = p_d_trac[0] / 1e6, p_d_trac[1] / 1000
                self.ax_interaccion.plot(mx_dt, pn_dt, 'X', color='maroon', markersize=8)
                self.ax_interaccion.text(mx_dt + 5, pn_dt + 10, f" ΦPn={pn_dt:.1f} kN",
                                         va='bottom', color='maroon', fontweight='bold',
                                         bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="maroon", lw=1, alpha=0.8))

                # Phi Mn Max
                p_d_mom = max(dis, key=lambda item: item[0])
                mx_dm, pn_dm = p_d_mom[0] / 1e6, p_d_mom[1] / 1000
                self.ax_interaccion.plot(mx_dm, pn_dm, 'X', color='maroon', markersize=8)
                self.ax_interaccion.text(mx_dm + 3, pn_dm, f"ΦMn={mx_dm:.1f} kN·m\nΦPn={pn_dm:.1f} kN",
                                         ha='left', va='center', color='maroon', fontweight='bold',
                                         bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="maroon", lw=1, alpha=0.8))

        # 3. Dibujar Puntos de Demanda
        for pt in self.puntos_demanda:
            mu = abs(pt['mx']) if eje == 'fuerte' else abs(pt['my'])
            pu = pt['p']
            estado = pt['estado']
            
            marcador = 'o' if estado == 'Seguro' else 'X'
            color_pt = 'green' if estado == 'Seguro' else 'red'
            
            self.ax_interaccion.plot(mu, pu, marker=marcador, color=color_pt, markersize=8, markeredgecolor='black')
            self.ax_interaccion.text(mu + 1, pu + 1, pt['label'], fontsize=8, color='black', alpha=0.7)

        # 4. Etiquetas y Formato
        cuantia = sum(b['area'] for b in self._recolectar_datos_seccion()['acero']) / (self._recolectar_datos_seccion()['b'] * self._recolectar_datos_seccion()['h'])
        self.ax_interaccion.set_title(f"Columna (ρ={cuantia*100:.2f}%) - Eje {eje.capitalize()}")
        self.ax_interaccion.set_xlabel(f"Momento M{'x' if eje=='fuerte' else 'y'} (kN·m)")
        self.ax_interaccion.set_ylabel("Carga Axial (kN)")
        self.ax_interaccion.grid(True, linestyle='--', alpha=0.7)
        self.ax_interaccion.legend(loc='upper right')
        self.ax_interaccion.axhline(0, color='black', linewidth=0.5)
        self.ax_interaccion.axvline(0, color='black', linewidth=0.5)
        
        self.plot_canvas_interaccion.draw()

    def _importar_esfuerzos(self):
        """Extrae Pu, M2, M3 de los resultados para la columna seleccionada."""
        id_elem_str = self.combo_elementos_vortex.currentText()
        if not id_elem_str or "N/A" in id_elem_str: return
        id_elem = int(id_elem_str)
        
        res_globales = self.modelo.resultados_calculo
        if not res_globales: return

        count_added = 0
        self.puntos_demanda.clear() 

        # Recorrer todas las combinaciones y casos
        for nombre_combo, subcasos in res_globales.items():
            if nombre_combo == 'reporte_global_data': continue
            for sub_caso, res in subcasos.items():
                f_int = res['fuerzas_internas'].get(id_elem) 
                if f_int is None: continue
                
                # Extraer esfuerzos en extremos (Nodos i y j)
                # Nodo i
                Pu_i = -f_int[0] # Compresión positiva (convención interna)
                Muy_i = f_int[4] # Momento alrededor de Y local
                Muz_i = f_int[5] # Momento alrededor de Z local
                
                # Nodo j
                Pu_j = f_int[6]  # Axial en j
                Muy_j = -f_int[10]
                Muz_j = -f_int[11]
                
                # Añadir el más crítico (o ambos)
                # Por simplicidad, añadimos el que tenga mayor magnitud de momento resultante
                M_res_i = math.sqrt(Muy_i**2 + Muz_i**2)
                M_res_j = math.sqrt(Muy_j**2 + Muz_j**2)
                
                if M_res_i > M_res_j:
                    # Aplicamos abs() a todo para importar solo magnitudes positivas
                    Pu, Mux, Muy, loc = abs(Pu_i), abs(Muz_i), abs(Muy_i), "Top"
                else:
                    Pu, Mux, Muy, loc = abs(Pu_j), abs(Muz_j), abs(Muy_j), "Bot"
                
                # Verificar contra diagrama si existe
                estado, ratio = "N/A", 0.0
                if self.puntos_dis_fuerte:
                    punto_dict = {'p': Pu, 'mx': Mux, 'my': Muy}
                    estado, ratio = verificar_punto_numericamente(punto_dict, self.puntos_dis_fuerte, self.puntos_dis_debil)

                self.puntos_demanda.append({
                    'label': f"{nombre_combo[:10]}..({loc})",
                    'p': Pu, 'mx': Mux, 'my': Muy,
                    'estado': estado, 'ratio': ratio
                })
                count_added += 1
        
        self._actualizar_tabla_puntos()
        self._actualizar_grafico_interaccion()
        self.enviar_mensaje_statusbar.emit(f"Importados {count_added} puntos de carga del análisis.", 4000)

    def _actualizar_tabla_puntos(self):
        self.tabla_puntos.setRowCount(0)
        for i, p in enumerate(self.puntos_demanda):
            self.tabla_puntos.insertRow(i)
            self.tabla_puntos.setItem(i, 0, QTableWidgetItem(p['label']))
            self.tabla_puntos.setItem(i, 1, QTableWidgetItem(f"{p['p']:.2f}"))
            self.tabla_puntos.setItem(i, 2, QTableWidgetItem(f"{p['mx']:.2f}"))
            self.tabla_puntos.setItem(i, 3, QTableWidgetItem(f"{p['my']:.2f}"))
            
            item_est = QTableWidgetItem(p['estado'])
            if p['estado'] == 'Seguro': item_est.setBackground(QColor("#C8E6C9")); item_est.setForeground(Qt.black)
            elif p['estado'] == 'Falla': item_est.setBackground(QColor("#FFCDD2")); item_est.setForeground(Qt.black)
            self.tabla_puntos.setItem(i, 4, item_est)
            
            self.tabla_puntos.setItem(i, 5, QTableWidgetItem(f"{p['ratio']:.3f}"))

    def _agregar_punto_manual(self):
        if not MODULES_COLUMNAS_LOADED: return
        dlg = PuntoDialog(self)
        if dlg.exec():
            data = dlg.get_data()
            if data:
                # Verificar
                estado, ratio = "N/A", 0.0
                if self.puntos_dis_fuerte:
                    estado, ratio = verificar_punto_numericamente(data, self.puntos_dis_fuerte, self.puntos_dis_debil)
                
                data['estado'] = estado; data['ratio'] = ratio
                self.puntos_demanda.append(data)
                self._actualizar_tabla_puntos()
                self._actualizar_grafico_interaccion()

    def _borrar_puntos_seleccionados(self):
        rows = sorted(list(set(i.row() for i in self.tabla_puntos.selectedItems())), reverse=True)
        for r in rows:
            del self.puntos_demanda[r]
        self._actualizar_tabla_puntos()
        self._actualizar_grafico_interaccion()

    # --- DIAGRAMAS VORTEX ---
    def _actualizar_casos_vortex(self):
        self.combo_casos_vortex.clear()
        combo = self.combo_combos_vortex.currentText()
        if combo and self.modelo.resultados_calculo:
            sub = self.modelo.resultados_calculo.get(combo, {})
            self.combo_casos_vortex.addItems(sorted(sub.keys()))

    def _refrescar_diagrama_vortex(self):
        """
        Dibuja el diagrama de la columna seleccionada (Resultados VORTEX).
        Implementa etiquetas Ni, Nj y valores extremos con estilo unificado.
        """
        id_str = self.combo_elementos_vortex.currentText()
        if not id_str or "N/A" in id_str: return
        id_elem = int(id_str)
        
        combo = self.combo_combos_vortex.currentText()
        caso = self.combo_casos_vortex.currentText()
        efecto = self.combo_efecto_vortex.currentText()
        
        if not (combo and caso): return
        if combo not in self.modelo.resultados_calculo: return
        if caso not in self.modelo.resultados_calculo[combo]: return
            
        res = self.modelo.resultados_calculo[combo][caso]
        
        x_altura, y_valor = self.generador_diagramas.get_diagrama(id_elem, res, efecto, n_puntos=50)
        
        # --- Preparación del Gráfico ---
        ax = self.grafico_vortex.ejes
        ax.clear()
        
        # Estilo Claro (Unificado con Vigas)
        ax.set_facecolor('white')
        self.grafico_vortex.figura.set_facecolor('white')
        ax.tick_params(colors='black')
        for sp in ax.spines.values(): sp.set_color('black')
        ax.xaxis.label.set_color('black'); ax.yaxis.label.set_color('black')
        ax.title.set_color('black')

        # --- Dibujado del Diagrama (Rotado) ---
        # Eje Vertical (Y del plot) = Altura de la columna
        # Eje Horizontal (X del plot) = Valor del efecto
        
        color_linea = '#1565C0' # Azul estándar
        
        # Plot principal: ax.plot(valor, altura)
        ax.plot(y_valor, x_altura, color=color_linea, linewidth=2, zorder=2)
        
        # Relleno hacia el eje central (x=0 en el plot)
        ax.fill_betweenx(x_altura, y_valor, 0, color=color_linea, alpha=0.2, zorder=2)
        
        # Línea central de la columna (Eje neutro)
        ax.axvline(0, color='black', linewidth=1, linestyle='-', zorder=1)
        ax.grid(True, linestyle=':', alpha=0.5)

        # --- Etiquetas y Decoración (Estilo Vigas adaptado) ---
        
        # Obtener datos del elemento
        ni, nj, _ = self.modelo.elementos[id_elem]
        longitud = x_altura[-1]
        
        # Puntos rojos en los extremos (Inicio y Fin)
        # Coordenadas plot: (Valor, Altura)
        val_ini, val_fin = y_valor[0], y_valor[-1]
        ax.scatter([val_ini, val_fin], [0, longitud], color='red', zorder=5, s=40)

        def fmt(val):
            return f"{val:.2f}" if abs(val) > 1e-3 else "0.00"

        # Calcular offsets para textos basados en los límites actuales
        x_lims = ax.get_xlim() # Límites del valor (horizontal)
        rango_x = x_lims[1] - x_lims[0] if (x_lims[1] - x_lims[0]) > 0 else 1.0
        offset_txt_x = rango_x * 0.05 # Margen horizontal para textos
        
        # --- Etiquetas de Nodos (Ni, Nj) y Elemento ---
        y_lims = ax.get_ylim()
        offset_vert = longitud * 0.05
        
        # Ni (Abajo)
        ax.text(0, -offset_vert, f" ni={ni}", color='black', ha='center', va='top', weight='bold')
        
        # Nj (Arriba)
        ax.text(0, longitud + offset_vert, f" nj={nj}", color='black', ha='center', va='bottom', weight='bold')
        
        # Etiqueta del Elemento (E{id}) en el centro geométrico
        ax.text(0, longitud / 2, f" E{id_elem} ", color='#000080', ha='right', va='center', weight='bold',
                bbox=dict(facecolor='white', edgecolor='none', alpha=0.6, pad=0.5))

        # --- Etiquetas de Valores en los extremos ---
        # Valor Inicio (Altura 0)
        ha_ini = 'left' if val_ini >= 0 else 'right'
        ax.text(val_ini, 0, f" {fmt(val_ini)} ", color='black', ha=ha_ini, va='center', fontsize=9, zorder=6)
        
        # Valor Fin (Altura L)
        ha_fin = 'left' if val_fin >= 0 else 'right'
        ax.text(val_fin, longitud, f" {fmt(val_fin)} ", color='black', ha=ha_fin, va='center', fontsize=9, zorder=6)

        # Máximos y Mínimos locales (Opcional, similar a vigas)
        idx_max = np.argmax(y_valor)
        val_max = y_valor[idx_max]
        h_max = x_altura[idx_max]
        
        if 0 < idx_max < len(y_valor) - 1 and abs(val_max) > 1e-3:
            ax.scatter(val_max, h_max, color='black', zorder=4, s=25)
            ax.text(val_max, h_max, f" {fmt(val_max)}", color='black', ha='left', va='bottom', fontsize=8)

        # --- Configuración Final de Ejes ---
        ax.set_ylabel("Altura Columna (m)")
        ax.set_xlabel(f"{efecto}")
        ax.set_title(f"Columna {id_elem} - {caso}")
        
        # Ajustar márgenes para que entren las etiquetas verticales
        ax.margins(y=0.15, x=0.1)
        
        self.grafico_vortex.lienzo.draw()

    # --- 3D y CORTE ---
    def _abrir_visor_3d(self):
        if not MODULES_COLUMNAS_LOADED: return
        if not self.puntos_dis_fuerte:
            QMessageBox.warning(self, "Aviso", "Primero calcule los diagramas 2D.")
            return
            
        datos = self._recolectar_datos_seccion()
        self.btn_ver_3d.setText("Generando..."); QApplication.processEvents()
        
        malla, _, _, _, _ = generar_superficie_interaccion_3d(
            datos['fc'], datos['fy'], datos['b'], datos['h'], datos['acero']
        )
        
        self.ventana_3d = Ventana3DMatplotlib(malla, self.puntos_dis_fuerte, self.puntos_dis_debil)
        self.ventana_3d.dibujar_puntos_3d(self.puntos_demanda) # Pasar los puntos actuales
        self.ventana_3d.show()
        self.btn_ver_3d.setText("Ver 3D")

    def _calcular_diseno_corte(self):
        if not MODULES_COLUMNAS_LOADED: return
        while self.layout_reporte_contenido.count():
            child = self.layout_reporte_contenido.takeAt(0)
            if child.widget(): child.widget().deleteLater()
            
        try:
            datos = self._recolectar_datos_seccion()
            vu = float(self.vu_input.text())
            nu = float(self.nu_input.text())
            
            res = realizar_diseno_columna_corte(
                datos['fc'], datos['fy'], vu, nu, 
                datos['b']/10, datos['h']/10, datos['rec']/10, 
                datos['d_est'], datos['d_barra']
            )
            
            # Renderizar HTML/LaTeX en reporte
            from widgets_gui import render_latex
            for linea in res['memoria']:
                if linea.startswith('$'): w = render_latex(linea)
                else:
                    w = QLabel(linea); w.setWordWrap(True); w.setTextFormat(Qt.RichText)
                    w.setStyleSheet("color: black; font-size: 10pt;")
                self.layout_reporte_contenido.addWidget(w)
            
            self.layout_reporte_contenido.addStretch()
            self.tabs_resultados.setCurrentIndex(2) # Ir a reporte
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error en cálculo de corte: {e}")