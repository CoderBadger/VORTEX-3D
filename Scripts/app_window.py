"""
Módulo: app_window.py
Descripción: Define la clase principal de la ventana (MainWindow). Gestiona
las interacciones del usuario, menús, barras de herramientas y coordina la 
comunicación entre la vista 3D y el modelo de datos estructural.
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

version = "1.0" 
import sys
from PySide6.QtWidgets import (QMainWindow, QTabWidget, QWidget, QVBoxLayout, QSplitter, QPushButton,
                             QMessageBox, QFileDialog, QToolBar, QStatusBar, QCheckBox, QFormLayout,
                             QHBoxLayout, QLabel, QDoubleSpinBox, QComboBox, QMenu, QGroupBox, QFrame,
                             QGridLayout, QLayout, QSizePolicy, QScrollArea, QDialog, QDialogButtonBox, QApplication)
from PySide6.QtCore import Qt, QSettings, QFileInfo, QDateTime, QRect, QSize, QPoint, QTimer
from PySide6.QtGui import QAction, QIcon, QActionGroup, QPalette, QColor
import numpy as np
import traceback
from modelo_estructura import Estructura
from visualizacion import GLViewer, GestorVisualizacion
from widgets_gui import (PestañaNodos, PestañaApoyos, PestañaMateriales, PestañaHipotesisDeCarga,
                         PestañaElementos, PestañaCombinaciones, PestañaCargas, PestañaResultados, 
                         PestañaReporte, PestañaDiseño, PestañaDefinicionLosas, DialogoConfiguracionCortes)
from calc import Solucionador3D
from importar_dxf import importar_dxf, obtener_capas_dxf
from procesador_cargas import ProcesadorCargas
from generador_reporte import GeneradorReporte

class FlowLayout(QLayout):

    def __init__(self, parent=None, margin=0, spacing=-1):
        super().__init__(parent)
        if parent is not None:
            self.setContentsMargins(margin, margin, margin, margin)
        self.setSpacing(spacing)
        self.itemList = []

    def __del__(self):
        item = self.takeAt(0)
        while item:
            item = self.takeAt(0)

    def addItem(self, item):
        self.itemList.append(item)

    def count(self):
        return len(self.itemList)

    def itemAt(self, index):
        if 0 <= index < len(self.itemList):
            return self.itemList[index]
        return None

    def takeAt(self, index):
        if 0 <= index < len(self.itemList):
            return self.itemList.pop(index)
        return None

    def expandingDirections(self):
        return Qt.Orientation(0)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        height = self._doLayout(QRect(0, 0, width, 0), True)
        return height

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self._doLayout(rect, False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()
        for item in self.itemList:
            size = size.expandedTo(item.minimumSize())
        margin, _, _, _ = self.getContentsMargins()
        size += QSize(2 * margin, 2 * margin)
        return size

    def _doLayout(self, rect, testOnly):
        x = rect.x()
        y = rect.y()
        lineHeight = 0
        spacing = self.spacing()

        for item in self.itemList:
            wid = item.widget()
            spaceX = spacing if spacing >= 0 else wid.style().layoutSpacing(QSizePolicy.ControlType.PushButton, QSizePolicy.ControlType.PushButton, Qt.Orientation.Horizontal)
            spaceY = spacing if spacing >= 0 else wid.style().layoutSpacing(QSizePolicy.ControlType.PushButton, QSizePolicy.ControlType.PushButton, Qt.Orientation.Vertical)
            
            nextX = x + item.sizeHint().width() + spaceX
            if nextX - spaceX > rect.right() and lineHeight > 0:
                x = rect.x()
                y = y + lineHeight + spaceY
                nextX = x + item.sizeHint().width() + spaceX
                lineHeight = 0

            if not testOnly:
                item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))

            x = nextX
            lineHeight = max(lineHeight, item.sizeHint().height())

        return y + lineHeight - rect.y()
    
TEXTO_AYUDA_DXF = """
<b>SINTAXIS DE CAPAS ADMITIDA:</b><br><br>
<b>ELEMENTOS (Line):</b> EL_NOMBRE_h_b<br>
Ej: <i>EL_Viga20x40_40_20</i> (h y b en cm)<br><br>
<b>LOSAS (3DFace):</b> LO_DIST_ESP_PE<br>
Ej: <i>LO_BI_20_24</i> (Bidireccional, 20cm, 24kN/m³)<br>
Ej: <i>LO_UX_15_25</i> (Uni X, 15cm, 25kN/m³)<br><br>
<b>APOYOS (Circle):</b> AP_RESTRICCIONES<br>
Ej: <i>AP_111000</i> (Restringe X, Y, Z, Libera rotaciones)<br><br>
<b>CARGAS UNIFORMES EN ELEMENTO (Line):</b> CU_TIPO_HIP_EJE_VALOR<br>
Ej: <i>CU_D_Muro_Z_-15</i> (Carga Muerta 'Muro', Eje Z, -15 kN/m)<br>
Ej: <i>CU_W_Viento_X_5</i> (Carga Viento, Eje X, 5 kN/m)<br><br>
<b>CARGAS SUP. (3DFace):</b> CS_TIPO_HIP_VALOR<br>
Ej: <i>CS_L_Uso_-2</i> (Carga Viva 'Uso' de 2 kN/m²)<br><br>
<b>CARGAS PUNT. (Point):</b> CP_TIPO_HIP_ACCION_VALOR<br>
Ej: <i>CP_L_Eq_FX_100</i> (Carga Viva 'Eq', Fuerza X, 100 kN)
"""

class DialogoConfigImportacionDXF(QDialog):
    def __init__(self, capas, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Importación DXF - Configuración")
        self.setMinimumWidth(600)
        self.setMinimumHeight(500)

        layout_principal = QHBoxLayout(self)

        col_izq = QVBoxLayout()
        grupo_capas = QGroupBox("1. Seleccionar Capas a Importar")
        l_capas = QVBoxLayout(grupo_capas)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        w_scroll = QWidget()
        self.layout_checks = QVBoxLayout(w_scroll)
        
        self.checkboxes = []
        for capa in capas:
            cb = QCheckBox(capa)
            if capa.startswith(('EL_', 'LO_', 'AP_', 'CU_', 'CS_', 'CP_')):
                cb.setChecked(True)
            self.layout_checks.addWidget(cb)
            self.checkboxes.append(cb)
            
        scroll.setWidget(w_scroll)
        l_capas.addWidget(scroll)
        
        btn_todas = QPushButton("Seleccionar Todas")
        btn_todas.clicked.connect(self.sel_todas)
        btn_ninguna = QPushButton("Ninguna")
        btn_ninguna.clicked.connect(self.sel_ninguna)
        h_btns = QHBoxLayout()
        h_btns.addWidget(btn_todas); h_btns.addWidget(btn_ninguna)
        l_capas.addLayout(h_btns)
        
        col_izq.addWidget(grupo_capas)
        layout_principal.addLayout(col_izq, stretch=1)

        col_der = QVBoxLayout()
        
        grupo_ayuda = QGroupBox("Ayuda de Sintaxis")
        l_ayuda = QVBoxLayout(grupo_ayuda)
        lbl_ayuda = QLabel(TEXTO_AYUDA_DXF)
        lbl_ayuda.setWordWrap(True)
        lbl_ayuda.setTextFormat(Qt.TextFormat.RichText)
        
        scroll_ayuda = QScrollArea(); scroll_ayuda.setWidgetResizable(True)
        scroll_ayuda.setWidget(lbl_ayuda)
        l_ayuda.addWidget(scroll_ayuda)
        col_der.addWidget(grupo_ayuda)

        botones = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        botones.accepted.connect(self.accept)
        botones.rejected.connect(self.reject)
        botones.button(QDialogButtonBox.Ok).setText("Importar")
        col_der.addWidget(botones)
        
        layout_principal.addLayout(col_der, stretch=1)

    def obtener_capas_seleccionadas(self):
        return [cb.text() for cb in self.checkboxes if cb.isChecked()]

    def sel_todas(self):
        for cb in self.checkboxes: cb.setChecked(True)

    def sel_ninguna(self):
        for cb in self.checkboxes: cb.setChecked(False)

class VentanaPrincipalVortex(QMainWindow):
    def actualizar_titulo_ventana(self):
        ruta = self.modelo.archivo_actual
        if ruta:
            nombre = ruta
        else:
            nombre = "sin título"
        self.setWindowTitle(f"VORTEX 3D - Versión {version} [{nombre}]")

    def __init__(self):
        super().__init__()
        self.resize(1200, 800) 
        qr = self.frameGeometry()
        cp = QApplication.primaryScreen().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())
        
        self.modelo = Estructura()
        self.gestor_visualizacion = GestorVisualizacion(self.modelo)
        self.configuracion = QSettings("VortexApp", "VORTEX 3D")
        self.recent_settings = QSettings("Vortex3D_Structural", "VOTX3D")
        self.recent_files_actions = []

        self.crear_acciones()
        self.crear_menus()
        self._configurar_menu_recientes()
        self.crear_barras_herramientas()
        self.setStatusBar(QStatusBar(self))
        
        self.config_cortes = {
            'x_min': -1000.0, 'x_max': 1000.0,
            'y_min': -1000.0, 'y_max': 1000.0,
            'z_min': -100.0,  'z_max': 1000.0
        }

        self.crear_widget_central() 
        
        self.refrescar_toda_la_gui()
        self.actualizar_titulo_ventana()
        self.statusBar().showMessage("Listo")

        QTimer.singleShot(0, self._actualizar_solo_visualizacion)

        QTimer.singleShot(100, self._precalentar_motor_grafico)
        
        self.tema_guardado = self.configuracion.value("tema_visualizacion", "oscuro")
        if self.tema_guardado == "claro":
            self.accion_cambiar_tema_visor.setChecked(True)
        if hasattr(self, 'vista_preliminar'):
            self.vista_preliminar.set_tema_fondo(self.tema_guardado)
        self._actualizar_texto_accion_tema()

        self.estilo_original = QApplication.style().objectName() 
        self.paleta_original = QApplication.palette()            
        
        tema = self.configuracion.value("tema_interfaz", "sistema")
        self.cambiar_tema_interfaz(tema)

    def crear_acciones(self):
        self.accion_nuevo = QAction(QIcon.fromTheme("document-new"), "&Nuevo", self, shortcut="Ctrl+N", triggered=self.nuevo_archivo)
        self.accion_abrir = QAction(QIcon.fromTheme("document-open"), "&Abrir...", self, shortcut="Ctrl+O", triggered=self.abrir_archivo)
        self.accion_guardar = QAction(QIcon.fromTheme("document-save"), "&Guardar", self, shortcut="Ctrl+S", triggered=self.guardar_archivo)
        self.accion_guardar_como = QAction("Guardar &como...", self, triggered=self.guardar_archivo_como)
        self.accion_importar_dxf = QAction(QIcon.fromTheme("document-import"), "&Importar DXF...", self, triggered=self.importar_desde_dxf)
        self.accion_calcular = QAction(QIcon.fromTheme("media-playback-start"), "&Calcular", self, shortcut="F5", triggered=self.calcular_estructura)
        self.accion_salir = QAction(QIcon.fromTheme("application-exit"), "&Salir", self, shortcut="Ctrl+Q", triggered=self.close)
        self.accion_cambiar_tema_visor = QAction("Modo Claro (Visor)", self, checkable=True)
        self.accion_cambiar_tema_visor.triggered.connect(self.cambiar_tema_visor)
        # TEORÍA DE TIMOSHENKO
        self.accion_usar_timoshenko = QAction("Usar Timoshenko", self, checkable=True)
        self.accion_usar_timoshenko.setToolTip("Incluye deformación por cortante (Teoría de Timoshenko)")
        self.accion_usar_timoshenko.setChecked(True) # Activado por defecto
        # PESO PROPIO
        self.accion_usar_peso_propio = QAction("Peso Propio (PP)", self, checkable=True)
        self.accion_usar_peso_propio.setToolTip("Incluye automáticamente el peso propio de elementos y losas")
        self.accion_usar_peso_propio.setChecked(False) # Desactivado por defecto
        
        self.accion_acerca_de = QAction("Acerca de", self, triggered=self.mostrar_acerca_de)

    def crear_menus(self):
        self.menu_archivo = self.menuBar().addMenu("&Archivo")
        self.menu_archivo.addActions([self.accion_nuevo, self.accion_abrir, self.accion_guardar, self.accion_guardar_como])
        self.menu_archivo.addSeparator()
        self.menu_archivo.addAction(self.accion_importar_dxf)
        self.menu_archivo.addSeparator()
        self.menu_archivo.addAction(self.accion_salir)
        
        self.menu_ver = self.menuBar().addMenu("&Ver")
        self.menu_ver.addAction(self.accion_cambiar_tema_visor)
        self.menu_ver.addSeparator()
        
        self.menu_tema = self.menu_ver.addMenu("Tema Interfaz")
        self.grupo_temas = QActionGroup(self)
        
        self.accion_tema_claro = QAction("Claro", self, checkable=True)
        self.accion_tema_oscuro = QAction("Oscuro", self, checkable=True)
        self.accion_tema_sistema = QAction("Sistema", self, checkable=True)
        
        self.accion_tema_claro.triggered.connect(lambda: self.cambiar_tema_interfaz("claro"))
        self.accion_tema_oscuro.triggered.connect(lambda: self.cambiar_tema_interfaz("oscuro"))
        self.accion_tema_sistema.triggered.connect(lambda: self.cambiar_tema_interfaz("sistema"))
        
        self.grupo_temas.addAction(self.accion_tema_claro)
        self.grupo_temas.addAction(self.accion_tema_oscuro)
        self.grupo_temas.addAction(self.accion_tema_sistema)
        
        self.menu_tema.addActions(self.grupo_temas.actions())
        
        tema_actual = self.configuracion.value("tema_interfaz", "sistema")
        if tema_actual == "claro": self.accion_tema_claro.setChecked(True)
        elif tema_actual == "oscuro": self.accion_tema_oscuro.setChecked(True)
        else: self.accion_tema_sistema.setChecked(True)

        self.menu_ayuda = self.menuBar().addMenu("A&yuda")
        self.menu_ayuda.addAction(self.accion_acerca_de)

    def crear_barras_herramientas(self):
        tb = self.addToolBar("Principal")
        tb.addActions([self.accion_nuevo, self.accion_abrir, self.accion_guardar])
        tb.addSeparator()
        tb.addAction(self.accion_calcular)
        tb.addSeparator()
        tb.addAction(self.accion_usar_timoshenko)
        tb.addAction(self.accion_usar_peso_propio)

    def mostrar_acerca_de(self):
        texto = (
            "<h2 style='color: #2c3e50;'>VORTEX 3D</h2>"
            "<b>Plataforma de Análisis de Estructuras Aporticadas en 3D</b><br><br>"
            "Desarrollado sobre los principios fundamentales del <b>Método Matricial de Rigidez<b><br> "
            "<b>Equipo de Desarrollo:</b><br>"
            "<ul>"
            "<li><b>Diego Oliver Vargas Moya:</b> Arquitectura del software, interfaz gráfica (GUI) y motor de análisis estructural.</li>"
            "<li><b>Luis Alberto Ortiz Morales:</b> Módulos de diseño normativo y validación de criterios.</li>"
            "</ul><br>"
            "<b>Propósito y Visión:</b><br>"
            "VORTEX 3D nace como una herramienta de validación y aprendizaje. Su objetivo principal es ofrecer "
            "<b>completa trazabilidad</b> en el paso a paso del cálculo estructural. Está diseñado para que "
            "futuros ingenieros y profesionales puedan auditar el comportamiento de la estructura, comprender la "
            "matemática detrás de los resultados y validar modelos creados en software comercial.<br><br>"
            "<hr>"
            "<div style='font-size: 11px; color: #555;'>"
            "<b>Aviso Legal (GNU GPL v3):</b><br>"
            "Este programa es software libre: puedes redistribuirlo y/o modificarlo bajo los términos "
            "de la Licencia Pública General GNU publicada por la Free Software Foundation, ya sea "
            "la versión 3 de la Licencia, o (a tu elección) cualquier versión posterior.<br><br>"
            "Este programa se distribuye con la esperanza de que sea útil, pero <b>SIN NINGUNA GARANTÍA</b>; "
            "sin incluso la garantía implícita de MERCANTILIDAD o APTITUD PARA UN PROPÓSITO PARTICULAR. "
            "Para ver una copia completa de la licencia, visita: "
            "<a href='https://www.gnu.org/licenses/gpl-3.0.html'>https://www.gnu.org/licenses/gpl-3.0.html</a>."
            "</div>"
        )
        QMessageBox.about(self, "Acerca de", texto)

    def _crear_panel_visualizacion(self):
        contenedor_visualizacion = QWidget()
        layout_visualizacion = QVBoxLayout(contenedor_visualizacion)
        layout_visualizacion.setContentsMargins(0, 0, 0, 0)

        grupo_controles = QGroupBox("Panel de Control de Escena")
        grupo_controles.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        
        flow_layout = FlowLayout(grupo_controles, margin=10, spacing=15)

        def crear_separador():
            linea = QFrame()
            linea.setFrameShape(QFrame.VLine)
            linea.setFrameShadow(QFrame.Sunken)
            linea.setStyleSheet("color: gray;")
            return linea

        etiqueta_capas = QLabel("<b>CAPAS:</b>")
        flow_layout.addWidget(etiqueta_capas)
        
        self.check_ver_nodos = QCheckBox("Nodos"); self.check_ver_nodos.setChecked(True)
        self.check_ver_etiquetas_nodos = QCheckBox("ID Nodos"); self.check_ver_etiquetas_nodos.setChecked(True)
        self.check_ver_elementos = QCheckBox("Barras"); self.check_ver_elementos.setChecked(True)
        self.check_ver_etiquetas_elementos = QCheckBox("ID Barras"); self.check_ver_etiquetas_elementos.setChecked(True)
        self.check_ver_placas = QCheckBox("Losas"); self.check_ver_placas.setChecked(True)
        self.check_ver_etiquetas_placas = QCheckBox("ID Losas"); self.check_ver_etiquetas_placas.setChecked(True)
        self.check_ver_cargas = QCheckBox("Cargas"); self.check_ver_cargas.setChecked(True)
        self.check_ver_secciones = QCheckBox("Secciones")
        self.check_ver_ejes_locales = QCheckBox("Ejes Locales")
        self.check_mostrar_distribucion_losas = QCheckBox("Distribución Losas")

        self.selector_hipotesis_visible = QComboBox()
        self.selector_hipotesis_visible.setMinimumWidth(120)

        for w in [self.check_ver_nodos, self.check_ver_etiquetas_nodos, self.check_ver_elementos, 
                  self.check_ver_etiquetas_elementos, self.check_ver_placas, self.check_ver_etiquetas_placas,
                  self.check_ver_secciones, self.check_ver_ejes_locales, self.check_mostrar_distribucion_losas, self.check_ver_cargas]:
            flow_layout.addWidget(w)

        flow_layout.addWidget(QLabel("Hipótesis de Carga:"))
        flow_layout.addWidget(self.selector_hipotesis_visible)

        flow_layout.addWidget(crear_separador())

        etiqueta_vistas = QLabel("<b>VISTAS:</b>")
        flow_layout.addWidget(etiqueta_vistas)
        
        self.btn_configurar_cortes = QPushButton("Configurar Cortes XYZ")
        self.btn_configurar_cortes.setToolTip("Aislar partes de la estructura")
        self.btn_configurar_cortes.clicked.connect(self._abrir_dialogo_cortes)
        
        self.btn_actualizar_vista = QPushButton("Refrescar")
        
        flow_layout.addWidget(self.btn_configurar_cortes)
        flow_layout.addWidget(self.btn_actualizar_vista)

        flow_layout.addWidget(crear_separador())

        # --- RESULTADOS Y DIAGRAMAS ---
        etiqueta_resultados = QLabel("<b>RESULTADOS:</b>")
        flow_layout.addWidget(etiqueta_resultados)

        self.check_mostrar_reacciones = QCheckBox("Reacciones en Nodos")
        self.check_mostrar_reacciones.setEnabled(False) # Desactivado hasta calcular
        
        self.check_mostrar_diagramas = QCheckBox("Diagramas")
        self.combo_combinacion_diagrama = QComboBox()
        self.combo_subcaso_diagrama = QComboBox()
        self.combo_efecto_diagrama = QComboBox()
        self.combo_efecto_diagrama.addItems(['Axial (Px)', 'Cortante (Py)', 'Momento (Mz)', 'Cortante (Pz)', 'Momento (My)', 'Torsión (Mx)'])

        self.check_ver_deformada = QCheckBox("Deformada")
        self.check_ver_deformada.setEnabled(False) # Desactivado hasta calcular
        self.input_escala_deformada = QDoubleSpinBox() 
        self.input_escala_deformada.setRange(0.1, 10000.0)
        self.input_escala_deformada.setValue(100.0)
        self.input_escala_deformada.setSingleStep(100.0)
        self.input_escala_deformada.setPrefix("Escala: x")

        # Nuevos controles secundarios de la deformada
        self.check_ver_desplazamientos_nodales = QCheckBox("Desplazamientos Nodales")
        self.check_ver_flecha_maxima = QCheckBox("Flecha Máxima")
        self.check_ver_desplazamientos_nodales.setEnabled(False)
        self.check_ver_flecha_maxima.setEnabled(False)
        self.check_ver_desplazamientos_nodales.setChecked(False)
        self.check_ver_flecha_maxima.setChecked(False)
        
        # Desactivar por defecto
        self.check_mostrar_diagramas.setEnabled(False)
        self.combo_combinacion_diagrama.setEnabled(False)
        self.combo_subcaso_diagrama.setEnabled(False)
        self.combo_efecto_diagrama.setEnabled(False)

        flow_layout.addWidget(self.combo_combinacion_diagrama)
        flow_layout.addWidget(self.combo_subcaso_diagrama)
        flow_layout.addWidget(self.check_mostrar_reacciones)
        flow_layout.addWidget(self.check_mostrar_diagramas)
        flow_layout.addWidget(self.combo_efecto_diagrama)
        flow_layout.addWidget(self.check_ver_deformada)
        flow_layout.addWidget(self.input_escala_deformada)
        flow_layout.addWidget(self.check_ver_desplazamientos_nodales)
        flow_layout.addWidget(self.check_ver_flecha_maxima)
        
        layout_visualizacion.addWidget(grupo_controles, stretch=0)
        self.vista_preliminar = GLViewer()
        layout_visualizacion.addWidget(self.vista_preliminar, stretch=1)

        # Conectar señales 
        self.check_ver_nodos.stateChanged.connect(self.refrescar_pestana_actual)
        self.check_ver_elementos.stateChanged.connect(self.refrescar_pestana_actual)
        self.check_ver_placas.stateChanged.connect(self.refrescar_pestana_actual)
        self.check_ver_cargas.stateChanged.connect(self.refrescar_pestana_actual)
        self.check_ver_etiquetas_nodos.stateChanged.connect(self.refrescar_pestana_actual)
        self.check_ver_etiquetas_elementos.stateChanged.connect(self.refrescar_pestana_actual)
        self.check_ver_etiquetas_placas.stateChanged.connect(self.refrescar_pestana_actual)
        self.check_ver_secciones.stateChanged.connect(self.refrescar_pestana_actual)
        self.check_ver_ejes_locales.stateChanged.connect(self.refrescar_pestana_actual)
        self.check_mostrar_distribucion_losas.stateChanged.connect(self.refrescar_pestana_actual)
        self.selector_hipotesis_visible.currentIndexChanged.connect(self.refrescar_pestana_actual)
        self.check_mostrar_diagramas.stateChanged.connect(self._gestionar_controles_diagrama)
        self.btn_actualizar_vista.clicked.connect(self._actualizar_solo_visualizacion)
        self.check_mostrar_reacciones.stateChanged.connect(self._actualizar_solo_visualizacion)
        self.check_mostrar_reacciones.stateChanged.connect(self._gestionar_controles_diagrama)
        self.combo_combinacion_diagrama.currentIndexChanged.connect(self._actualizar_solo_visualizacion)
        self.combo_combinacion_diagrama.currentIndexChanged.connect(self._actualizar_combo_subcaso_diagrama_principal)
        self.combo_subcaso_diagrama.currentIndexChanged.connect(self._actualizar_solo_visualizacion)
        self.combo_efecto_diagrama.currentIndexChanged.connect(self._actualizar_solo_visualizacion)
        self.check_ver_deformada.stateChanged.connect(self.refrescar_pestana_actual)
        self.input_escala_deformada.valueChanged.connect(self.refrescar_pestana_actual)
        self.check_ver_deformada.stateChanged.connect(self._gestionar_controles_diagrama)
        self.check_ver_desplazamientos_nodales.stateChanged.connect(self.refrescar_pestana_actual)
        self.check_ver_flecha_maxima.stateChanged.connect(self.refrescar_pestana_actual)
        
        # Desactivar/activar submódulos de deformada al activar el original
        self.check_ver_deformada.stateChanged.connect(
            lambda state: (
                self.check_ver_desplazamientos_nodales.setEnabled(bool(state)),
                self.check_ver_flecha_maxima.setEnabled(bool(state)),
                (not state) and self.check_ver_desplazamientos_nodales.setChecked(False),
                (not state) and self.check_ver_flecha_maxima.setChecked(False)
            )
        )
        self.check_mostrar_diagramas.stateChanged.connect(self._gestionar_controles_diagrama)
        self.btn_actualizar_vista.clicked.connect(self._actualizar_solo_visualizacion)
        self.check_mostrar_reacciones.stateChanged.connect(self._actualizar_solo_visualizacion)
        self.check_mostrar_reacciones.stateChanged.connect(self._gestionar_controles_diagrama)
        self.combo_combinacion_diagrama.currentIndexChanged.connect(self._actualizar_solo_visualizacion)
        self.combo_combinacion_diagrama.currentIndexChanged.connect(self._actualizar_combo_subcaso_diagrama_principal)
        self.combo_subcaso_diagrama.currentIndexChanged.connect(self._actualizar_solo_visualizacion)
        self.combo_efecto_diagrama.currentIndexChanged.connect(self._actualizar_solo_visualizacion)
        self.check_ver_deformada.stateChanged.connect(self.refrescar_pestana_actual)
        self.input_escala_deformada.valueChanged.connect(self.refrescar_pestana_actual)
        self.check_ver_deformada.stateChanged.connect(self._gestionar_controles_diagrama)
        
        return contenedor_visualizacion

    def cambiar_tema_interfaz(self, tema):
        """Cambia el tema global de la aplicación (Claro, Oscuro, Sistema)."""
        self.configuracion.setValue("tema_interfaz", tema)
        app = QApplication.instance()
        
        if tema == "oscuro":
            app.setStyle("Fusion")
            dark_palette = QPalette()
            dark_palette.setColor(QPalette.Window, QColor(53, 53, 53))
            dark_palette.setColor(QPalette.WindowText, Qt.white)
            dark_palette.setColor(QPalette.Base, QColor(25, 25, 25))
            dark_palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
            dark_palette.setColor(QPalette.ToolTipBase, Qt.black)
            dark_palette.setColor(QPalette.ToolTipText, Qt.white)
            dark_palette.setColor(QPalette.Text, Qt.white)
            dark_palette.setColor(QPalette.Button, QColor(53, 53, 53))
            dark_palette.setColor(QPalette.ButtonText, Qt.white)
            dark_palette.setColor(QPalette.BrightText, Qt.red)
            dark_palette.setColor(QPalette.Link, QColor(42, 130, 218))
            dark_palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
            dark_palette.setColor(QPalette.HighlightedText, Qt.black)
            app.setPalette(dark_palette)
            
        elif tema == "claro":
            app.setStyle("Fusion")
            app.setPalette(app.style().standardPalette())
            
        else: 
            app.setStyle(self.estilo_original)
            app.setPalette(self.paleta_original)
    
    def _abrir_dialogo_cortes(self):
        """Abre el diálogo para configurar límites X, Y, Z y actualiza la vista si se acepta."""
        dialogo = DialogoConfiguracionCortes(self.config_cortes, self)
        if dialogo.exec():
            self.config_cortes = dialogo.obtener_limites()
            self._actualizar_solo_visualizacion()

    def _actualizar_combo_subcaso_diagrama_principal(self):
        self.combo_subcaso_diagrama.blockSignals(True)
        self.combo_subcaso_diagrama.clear()
        
        nombre_combo_sel = self.combo_combinacion_diagrama.currentText()
        if nombre_combo_sel and self.modelo.resultados_calculo:
            sub_resultados = self.modelo.resultados_calculo.get(nombre_combo_sel, {})
            nombres_sub_casos = sorted(sub_resultados.keys())
            if nombres_sub_casos:
                self.combo_subcaso_diagrama.addItems(nombres_sub_casos)
        
        self.combo_subcaso_diagrama.blockSignals(False)
        self._actualizar_solo_visualizacion() 
    
    def _actualizar_selector_hipotesis(self):
        self.selector_hipotesis_visible.blockSignals(True)
        self.selector_hipotesis_visible.clear()
        if not self.modelo.hipotesis_de_carga:
            self.selector_hipotesis_visible.addItem("No hay hipótesis", -1) 
        else:
            for id_hip, datos in sorted(self.modelo.hipotesis_de_carga.items()):
                self.selector_hipotesis_visible.addItem(datos['nombre'], id_hip)
        self.selector_hipotesis_visible.blockSignals(False)
    
    def _gestionar_controles_diagrama(self):
        """Habilita o deshabilita los combobox de resultados y refresca la vista."""
        ver_diagramas = self.check_mostrar_diagramas.isChecked()
        ver_reacciones = self.check_mostrar_reacciones.isChecked()
        ver_deformada = self.check_ver_deformada.isChecked()

        activar_seleccion_caso = ver_diagramas or ver_reacciones or ver_deformada
        
        self.combo_combinacion_diagrama.setEnabled(activar_seleccion_caso)
        self.combo_subcaso_diagrama.setEnabled(activar_seleccion_caso)
        
        self.combo_efecto_diagrama.setEnabled(ver_diagramas)
        
        self._actualizar_solo_visualizacion()

    def crear_widget_central(self):
        splitter_principal = QSplitter(Qt.Horizontal)
        self.setCentralWidget(splitter_principal)

        self.pestanas_principales = QTabWidget()

        self.subpestanas_entrada = QTabWidget()

        self.pestana_nodos = PestañaNodos(self.modelo, self.gestor_visualizacion, self)
        self.subpestanas_entrada.addTab(self.pestana_nodos, "Nodos")
        self.pestana_nodos.datos_modificados.connect(self._actualizar_solo_visualizacion)

        contenedor_porticos = QWidget()
        layout_porticos = QVBoxLayout(contenedor_porticos)
        layout_porticos.setContentsMargins(0,0,0,0)
        tabs_porticos = QTabWidget()
        self.pestana_materiales_porticos = PestañaMateriales(self.modelo, self.gestor_visualizacion, self)
        self.pestana_elementos_1d = PestañaElementos(self.modelo, self.gestor_visualizacion, self)
        tabs_porticos.addTab(self.pestana_materiales_porticos, "Materiales")
        tabs_porticos.addTab(self.pestana_elementos_1d, "Elementos 1D")
        layout_porticos.addWidget(tabs_porticos)
        self.subpestanas_entrada.addTab(contenedor_porticos, "Pórticos")
        self.pestana_materiales_porticos.datos_modificados.connect(self.pestana_elementos_1d.refrescar_formularios)
        self.pestana_materiales_porticos.datos_modificados.connect(self._actualizar_solo_visualizacion)
        self.pestana_elementos_1d.datos_modificados.connect(self._actualizar_solo_visualizacion)

        self.pestana_apoyos = PestañaApoyos(self.modelo, self.gestor_visualizacion, self)
        self.subpestanas_entrada.addTab(self.pestana_apoyos, "Apoyos")
        self.pestana_apoyos.datos_modificados.connect(self._actualizar_solo_visualizacion)

        contenedor_cargas = QWidget()
        layout_cargas = QVBoxLayout(contenedor_cargas)
        layout_cargas.setContentsMargins(0,0,0,0)
        tabs_cargas = QTabWidget()
        self.pestana_hipotesis = PestañaHipotesisDeCarga(self.modelo, self.gestor_visualizacion, self)
        self.pestana_definicion_losas = PestañaDefinicionLosas(self.modelo, self.gestor_visualizacion, self)
        self.pestana_asignacion_cargas = PestañaCargas(self.modelo, self.gestor_visualizacion, self)
        self.pestana_combinaciones = PestañaCombinaciones(self.modelo, self.gestor_visualizacion, self)
        tabs_cargas.addTab(self.pestana_hipotesis, "Hipótesis de Carga")
        tabs_cargas.addTab(self.pestana_definicion_losas, "Definición de Losas")
        tabs_cargas.addTab(self.pestana_asignacion_cargas, "Asignación de Cargas")
        tabs_cargas.addTab(self.pestana_combinaciones, "Combinaciones")
        layout_cargas.addWidget(tabs_cargas)
        self.subpestanas_entrada.addTab(contenedor_cargas, "Cargas")
        self.pestana_hipotesis.datos_modificados.connect(self.pestana_asignacion_cargas.refrescar)
        self.pestana_hipotesis.datos_modificados.connect(self._actualizar_selector_hipotesis)
        self.pestana_definicion_losas.datos_modificados.connect(self._actualizar_solo_visualizacion) 
        self.pestana_asignacion_cargas.datos_modificados.connect(self._actualizar_solo_visualizacion)
        
        self.pestanas_principales.addTab(self.subpestanas_entrada, "Definición")

        self.subpestanas_calculo = QTabWidget()
        self.pestana_resultados = PestañaResultados()
        self.pestana_reporte = PestañaReporte(self.modelo)
        self.subpestanas_calculo.addTab(self.pestana_resultados, "Resultados Numéricos")
        self.subpestanas_calculo.addTab(self.pestana_reporte, "Reporte de Cálculo")
        self.pestanas_principales.addTab(self.subpestanas_calculo, "Resultados")

        self.pestana_diseno = PestañaDiseño(self.modelo)
        self.pestanas_principales.addTab(self.pestana_diseno, "Diseño")
        self.pestana_diseno.pagina_vigas.enviar_mensaje_statusbar.connect(self.statusBar().showMessage)

        self.panel_visualizacion = self._crear_panel_visualizacion()

        splitter_principal.addWidget(self.pestanas_principales)
        splitter_principal.addWidget(self.panel_visualizacion)
        splitter_principal.setCollapsible(0, False)
        splitter_principal.setCollapsible(1, False)
        
        splitter_principal.widget(0).setMinimumWidth(400) 
        splitter_principal.widget(1).setMinimumWidth(400)

        ancho_total = self.width()
        splitter_principal.setSizes([int(ancho_total * 0.35), int(ancho_total * 0.65)])

        splitter_principal.setStretchFactor(0, 0)       
        splitter_principal.setStretchFactor(1, 1)         

        self.pestanas_principales.currentChanged.connect(self._gestionar_visibilidad_panel)
        self.subpestanas_entrada.currentChanged.connect(self.refrescar_pestana_actual)
        self.pestana_reporte.enviar_mensaje_statusbar.connect(self.statusBar().showMessage)
        self._gestionar_visibilidad_panel(0)

    def _gestionar_visibilidad_panel(self, index):
        """Muestra u oculta el panel de visualización según la pestaña seleccionada."""
        nombre_pestana = self.pestanas_principales.tabText(index)
        
        if nombre_pestana in ["Definición", "Resultados"]:
            self.panel_visualizacion.show()
            self.refrescar_pestana_actual() 
        else:
            self.panel_visualizacion.hide()

    def refrescar_pestana_actual(self, index=None):

        indice_actual = self.subpestanas_entrada.currentIndex()
        widget_actual = self.subpestanas_entrada.widget(indice_actual)
        
        if hasattr(widget_actual, 'refrescar'):
            widget_actual.refrescar()

        self._actualizar_solo_visualizacion()

    def _actualizar_solo_visualizacion(self):
        """
        Este es el método SEGURO. Solo actualiza la vista 3D
        usando el estado actual de los checkboxes. No llama a refrescar
        ninguna pestaña, evitando así el bucle infinito.
        """
        if not hasattr(self, 'check_ver_nodos'): return 
        
        resultados_activos = None
        if self.modelo.resultados_calculo:
            nombre_combo = self.combo_combinacion_diagrama.currentText()
            nombre_subcaso = self.combo_subcaso_diagrama.currentText()
            if nombre_combo and nombre_subcaso:
                resultados_activos = self.modelo.resultados_calculo.get(nombre_combo, {}).get(nombre_subcaso)

        opciones_preliminar = {
            'nodos': self.check_ver_nodos.isChecked(), 
            'elementos': self.check_ver_elementos.isChecked(), 
            'placas': self.check_ver_placas.isChecked(),
            'apoyos': True,
            'cargas': self.check_ver_cargas.isChecked(), 
            'ids_nodos': self.check_ver_etiquetas_nodos.isChecked(), 
            'ids_elementos': self.check_ver_etiquetas_elementos.isChecked(),
            'ids_placas': self.check_ver_etiquetas_placas.isChecked(),
            'ejes_locales': self.check_ver_ejes_locales.isChecked(),
            'mostrar_distribucion_losas': self.check_mostrar_distribucion_losas.isChecked(),
            'mostrar_secciones': self.check_ver_secciones.isChecked(), 
            'hipotesis_visible_id': self.selector_hipotesis_visible.currentData(),
            'mostrar_reacciones': self.check_mostrar_reacciones.isChecked(),
            'mostrar_deformada': self.check_ver_deformada.isChecked(),
            'escala_deformada': self.input_escala_deformada.value(),
            'mostrar_desplazamientos_nodales': getattr(self, 'check_ver_desplazamientos_nodales', QCheckBox()).isChecked(),
            'mostrar_flecha_maxima': getattr(self, 'check_ver_flecha_maxima', QCheckBox()).isChecked(),
            'mostrar_diagramas': self.check_mostrar_diagramas.isChecked(),
            'resultados_diagrama_especificos': resultados_activos,
            'efecto_diagrama': self.combo_efecto_diagrama.currentText(),
            'limites_corte': self.config_cortes
        }

        activar_combos = (self.check_mostrar_diagramas.isChecked() or 
                          self.check_ver_deformada.isChecked() or 
                          self.check_mostrar_reacciones.isChecked())
                          
        self.combo_combinacion_diagrama.setEnabled(activar_combos)
        self.combo_subcaso_diagrama.setEnabled(activar_combos)
        
        self.gestor_visualizacion.actualizar(self.vista_preliminar, opciones_preliminar)

    def enfocar_vistas(self):
        """Calcula el centro del modelo y enfoca las vistas 3D en él."""
        centro = self.modelo.get_centro_geometrico()
        self.vista_preliminar.set_focal_point(centro)

    def refrescar_toda_la_gui(self):

        self.pestana_nodos.refrescar()
        self.pestana_apoyos.refrescar()
        self.pestana_materiales_porticos.refrescar()
        self.pestana_elementos_1d.refrescar()
        self.pestana_definicion_losas.refrescar()
        self.pestana_combinaciones.refrescar()
        self.pestana_hipotesis.refrescar() 
        self.pestana_asignacion_cargas.refrescar()
        self._actualizar_selector_hipotesis()

        self.refrescar_pestana_actual()

    def _configurar_menu_recientes(self):
        """Crea el submenú 'Abrir Reciente' y la opción para limpiar el historial."""
        self.menu_recientes = QMenu("Abrir Reciente", self)
        
        self.menu_archivo.addSeparator()
        self.menu_archivo.addMenu(self.menu_recientes)
        
        accion_limpiar = QAction("Limpiar recientes", self)
        accion_limpiar.triggered.connect(self._clear_recent_files)
        self.menu_archivo.addAction(accion_limpiar)
        
        self._load_settings()

    def _load_settings(self):
        """Lee la clave 'recentFiles' desde QSettings."""
        rutas = self.recent_settings.value("recentFiles", [])
        if isinstance(rutas, str):
            rutas = rutas.split(";") if rutas else []
        elif not isinstance(rutas, list):
            rutas = list(rutas)
            
        self.recent_files_actions.clear()
        
        self.guardando_settings = True
        for ruta in reversed(rutas):
            if isinstance(ruta, str) and ruta.strip():
                self._add_to_recent_files(ruta)
        self.guardando_settings = False
        
        if not self.recent_files_actions:
            accion_vacio = QAction("No hay archivos recientes", self)
            accion_vacio.setEnabled(False)
            acciones = self.menu_recientes.actions()
            if acciones:
                self.menu_recientes.insertAction(acciones[0], accion_vacio)
            else:
                self.menu_recientes.addAction(accion_vacio)

    def _add_to_recent_files(self, ruta_archivo):
        if not ruta_archivo:
             return
             
        # Prevención de duplicados
        for action in self.recent_files_actions:
            if action.data() == ruta_archivo:
                self.recent_files_actions.remove(action)
                self.menu_recientes.removeAction(action)
                break
                
        # Inserción en la cima
        nombre_archivo = QFileInfo(ruta_archivo).fileName()
        accion = QAction(nombre_archivo, self)
        accion.setData(ruta_archivo)
        accion.triggered.connect(lambda checked=False, p=ruta_archivo: self.open_recent_file(p))
        
        acciones = self.menu_recientes.actions()
        if acciones and acciones[0].text() == "No hay archivos recientes":
            self.menu_recientes.removeAction(acciones[0])
            acciones = self.menu_recientes.actions()
            
        if acciones:
            self.menu_recientes.insertAction(acciones[0], accion)
        else:
            self.menu_recientes.addAction(accion)
            
        self.recent_files_actions.insert(0, accion)
        
        # Límite de historial
        while len(self.recent_files_actions) > 5:
            last_action = self.recent_files_actions.pop()
            self.menu_recientes.removeAction(last_action)
            
        # Sincronización
        if not getattr(self, 'guardando_settings', False):
            self._save_settings()

    def open_recent_file(self, ruta_archivo):
        """Apertura desde el historial verificando cambios."""
        if self.modelo.modificado:
            res = QMessageBox.question(self, "Guardar Cambios", "¿Desea guardar los cambios en el proyecto actual?", 
                                     QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel)
            if res == QMessageBox.Save:
                if not self.guardar_archivo():
                    return
            elif res == QMessageBox.Cancel:
                return
                
        self.abrir_archivo(ruta_archivo=ruta_archivo)
        
    def _clear_recent_files(self):
        """Limpieza del Historial."""
        for action in self.recent_files_actions:
            self.menu_recientes.removeAction(action)
        self.recent_files_actions.clear()
        
        accion_vacio = QAction("No hay archivos recientes", self)
        accion_vacio.setEnabled(False)
        acciones = self.menu_recientes.actions()
        if acciones:
            self.menu_recientes.insertAction(acciones[0], accion_vacio)
        else:
            self.menu_recientes.addAction(accion_vacio)
        
        self.recent_settings.setValue("recentFiles", [])
        self.statusBar().showMessage("Historial de archivos recientes limpiado.", 3000)

    def _save_settings(self):
        rutas = [action.data() for action in self.recent_files_actions]
        self.recent_settings.setValue("recentFiles", rutas)

    def nuevo_archivo(self):
        self.modelo.reiniciar()
       
        self.check_mostrar_diagramas.setChecked(False)
        self.check_mostrar_diagramas.setEnabled(False)
        self.combo_combinacion_diagrama.clear()
        self.combo_combinacion_diagrama.setEnabled(False)
        self.combo_efecto_diagrama.setEnabled(False)
        self.gestor_visualizacion.generador_diagramas = None

        self.refrescar_toda_la_gui() 
        self.actualizar_titulo_ventana()
        self.pestana_reporte.actualizar("")
        self.statusBar().showMessage("Nuevo archivo creado.")

    def abrir_archivo(self, ruta_archivo=None):
        if not ruta_archivo:
            ruta, _ = QFileDialog.getOpenFileName(self, "Abrir", "", "Archivos Vortex (*.votx)")
            if not ruta: return
            ruta_archivo = ruta
        
        if ruta_archivo:
            try:
                self.modelo.cargar_desde_archivo(ruta_archivo)
                
                self.check_mostrar_diagramas.setChecked(False)
                self.check_mostrar_diagramas.setEnabled(False)
                self.combo_combinacion_diagrama.clear()
                self.combo_combinacion_diagrama.setEnabled(False)
                self.combo_efecto_diagrama.setEnabled(False)
                self.gestor_visualizacion.generador_diagramas = None

                self.refrescar_toda_la_gui()
                self.enfocar_vistas()
                self.actualizar_titulo_ventana() 
                self.statusBar().showMessage(f"Cargado: {ruta_archivo}")
                self._add_to_recent_files(ruta_archivo)
                self.pestana_reporte.actualizar("")
            except IOError as e: 
                QMessageBox.critical(self, "Error", str(e))
    
    def guardar_archivo(self):
        if not self.modelo.archivo_actual: return self.guardar_archivo_como()
        return self.guardar_logica(self.modelo.archivo_actual)

    def guardar_archivo_como(self):
        ruta, _ = QFileDialog.getSaveFileName(self, "Guardar como", "", "Archivos Vortex (*.votx)")
        if ruta: return self.guardar_logica(ruta if ruta.endswith('.votx') else ruta + '.votx')

    def guardar_logica(self, ruta):
        try:
            self.modelo.guardar_en_archivo(ruta)
            self.actualizar_titulo_ventana()
            self.statusBar().showMessage(f"Guardado: {ruta}")
            self._add_to_recent_files(ruta)
            return True
        except IOError as e: QMessageBox.critical(self, "Error", str(e)); return False

    def importar_desde_dxf(self):
        ruta, _ = QFileDialog.getOpenFileName(self, "Importar DXF", "", "Archivos DXF (*.dxf)")
        if not ruta: return

        try:
            # 1. Leer capas disponibles
            capas_disponibles = obtener_capas_dxf(ruta)
            if not capas_disponibles:
                QMessageBox.information(self, "Información", "El archivo DXF está vacío o no tiene capas.")
                return

            # 2. Diálogo de Configuración Simplificado
            dialogo = DialogoConfigImportacionDXF(capas_disponibles, self)
            
            if dialogo.exec():
                capas_sel = dialogo.obtener_capas_seleccionadas()
                if not capas_sel: return
                
                self.statusBar().showMessage("Procesando DXF con fusión de nodos...")
                QApplication.processEvents()

                # 3. Importación con Lógica de tolerancia
                datos = importar_dxf(ruta, capas_seleccionadas=capas_sel, tolerancia_fusion=0.01) # 1cm de tolerancia
                
                # Reporte de Errores de Sintaxis
                if datos['capas_omitidas']:
                    msg = "<b>Error de sintaxis.</b> Las siguientes capas fueron omitidas:<br><ul>"
                    for c in datos['capas_omitidas']:
                        msg += f"<li>{c}</li>"
                    msg += "</ul>"
                    QMessageBox.warning(self, "Capas Omitidas", msg)

                # 4. Cargar Modelo
                self.modelo.reiniciar()
                self.modelo.nodos = datos['nodos']
                self.modelo.elementos = datos['elementos']
                self.modelo.materiales = datos['materiales']
                self.modelo.losas = datos['losas'] 

                for apoyo in datos['apoyos_importados']:
                    self.modelo.agregar_o_actualizar_apoyo(apoyo['id_nodo'], apoyo['restricciones'])

                # 6. Procesar Cargas (Lineales y Superficiales)
                
                # Mapeo rápido de línea a ID elemento para cargas lineales
                coord_linea_a_id_elem = {}
                for id_elem, (ni, nj, _) in self.modelo.elementos.items():
                    p1 = self.modelo.nodos[ni]; p2 = self.modelo.nodos[nj]
                    clave = tuple(sorted((p1, p2)))
                    coord_linea_a_id_elem[clave] = id_elem

                # Mapeo de losa (vertices) a ID losa
                coord_losa_a_id_losa = {}
                for id_losa, d in self.modelo.losas.items():
                    clave = tuple(sorted(d['coords_vertices']))
                    coord_losa_a_id_losa[clave] = id_losa

                count_cargas = 0
                
                # Cargas Lineales y Superficiales
                for carga in datos['cargas_importadas']:
                    nom_hip = carga['nombre_hipotesis']
                    tipo_hip = carga['tipo_carga_norma']
                    id_hip = next((k for k,v in self.modelo.hipotesis_de_carga.items() if v['nombre'] == nom_hip), None)
                    if id_hip is None:
                        id_hip = self.modelo.agregar_hipotesis(nom_hip, tipo_hip)

                    if carga['tipo'] == 'elemento':
                        # Buscar elemento por coordenadas
                        p1 = carga['coords_inicio']; p2 = carga['coords_fin']
                        clave = tuple(sorted((p1, p2)))
                        id_elem = coord_linea_a_id_elem.get(clave)
                        if id_elem:
            
                            eje = carga['eje_carga']
                            val = carga['magnitud']
                            
                            wx, wy, wz = 0.0, 0.0, 0.0
                            
                            if eje == 'X': wx = val
                            elif eje == 'Y': wy = val
                            elif eje == 'Z': wz = val
                            
                            # Estructura: (tipo, wx, wy, wz, mt)
                            datos_c = ('uniforme', wx, wy, wz, 0.0)
                            
                            self.modelo.agregar_carga_elemento(id_elem, id_hip, datos_c)
                            count_cargas += 1
                            
                    elif carga['tipo'] == 'superficial':
                        clave = tuple(sorted(carga['coords_vertices']))
                        id_losa = coord_losa_a_id_losa.get(clave)
                        if id_losa:
                            self.modelo.agregar_o_actualizar_carga_superficial(None, id_losa, id_hip, carga['magnitud_wz'])
                            count_cargas += 1

                # Cargas Puntuales
                for cp in datos['cargas_puntuales_importadas']:
                    nom_hip = cp['nombre_hipotesis']
                    tipo_hip = cp['tipo_carga_norma']
                    id_hip = next((k for k,v in self.modelo.hipotesis_de_carga.items() if v['nombre'] == nom_hip), None)
                    if id_hip is None: id_hip = self.modelo.agregar_hipotesis(nom_hip, tipo_hip)
                    
                    vec = [0.0]*6
                    idx = {'FX':0, 'FY':1, 'FZ':2, 'MX':3, 'MY':4, 'MZ':5}[cp['concepto_fuerza']]
                    vec[idx] = cp['magnitud']
                    
                    self.modelo.agregar_carga_nodal(cp['id_nodo'], id_hip, vec)
                    count_cargas += 1

                self.modelo.modificado = True
                self.refrescar_toda_la_gui()
                self.enfocar_vistas()
                self.statusBar().showMessage(f"DXF Importado: {len(self.modelo.nodos)} Nodos, {len(self.modelo.elementos)} Barras, {len(self.modelo.losas)} Losas.")

        except Exception as e:
            QMessageBox.critical(self, "Error Importación", f"Ocurrió un error crítico:\n{e}")
            import traceback
            traceback.print_exc()

    def calcular_estructura(self):
        self.statusBar().showMessage("Calculando...")
        try:
            self.modelo.datos_reporte_losas = []
            
            procesador = ProcesadorCargas(self.modelo)

            usar_timoshenko = self.accion_usar_timoshenko.isChecked()
            usar_pp = self.accion_usar_peso_propio.isChecked()
            
            resultados_por_combinacion = procesador.resolver_combinaciones(
                usar_timoshenko=usar_timoshenko, 
                usar_pp=usar_pp 
            )

            self.modelo.resultados_calculo = resultados_por_combinacion

            self.gestor_visualizacion.generador_diagramas = None

            self.pestana_resultados.actualizar(self.modelo, resultados_por_combinacion)
            self.pestana_diseno.actualizar(self.modelo)
            
            claves_combos = [k for k in resultados_por_combinacion.keys() if k != 'reporte_global_data']
            
            self.combo_combinacion_diagrama.clear()
            self.combo_combinacion_diagrama.addItems(claves_combos)
            self.check_mostrar_diagramas.setEnabled(True)
            self.check_mostrar_diagramas.setChecked(False) 
            self.check_mostrar_reacciones.setEnabled(True)
            self.check_mostrar_reacciones.setChecked(False)
            self.check_ver_deformada.setEnabled(True)
            self.check_ver_deformada.setChecked(False)
            self.generar_y_actualizar_reporte()
            self.pestanas_principales.setCurrentIndex(1)
            self.pestana_reporte.actualizar("")
            self.statusBar().showMessage("Cálculo completado.", 5000)
        
        except ValueError as e:
            QMessageBox.warning(self, "Advertencia de Cálculo", str(e))
            self.statusBar().showMessage(f"Cálculo abortado: {e}", 5000)
        except Exception as e:
            QMessageBox.critical(self, "Error de Cálculo", f"Ocurrió un error inesperado: {e}\n\n{traceback.format_exc()}")
            self.statusBar().showMessage("Error en el cálculo.", 5000)
    
    def generar_y_actualizar_reporte(self):
        self.pestana_reporte.actualizar("")

    def closeEvent(self, event):
        self._save_settings()
        if self.modelo.modificado:
            res = QMessageBox.question(self, "Guardar Cambios", "¿Desea guardar los cambios antes de salir?", 
                                     QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel)
            if res == QMessageBox.Save:
                if not self.guardar_archivo(): event.ignore()
            elif res == QMessageBox.Cancel:
                event.ignore()
    def cambiar_tema_visor(self):
        """
        Se activa cuando se hace clic en la acción del menú para cambiar el tema del visor.
        """
        if self.accion_cambiar_tema_visor.isChecked():
            nuevo_modo = "claro"
        else:
            nuevo_modo = "oscuro"
        
        self.configuracion.setValue("tema_visualizacion", nuevo_modo)
        
        if hasattr(self, 'vista_preliminar'):
            self.vista_preliminar.set_tema_fondo(nuevo_modo)
            
        self._actualizar_texto_accion_tema()
        
        self.statusBar().showMessage(f"Modo del visor 3D cambiado a {nuevo_modo}", 3000)

        self._actualizar_solo_visualizacion()

    def _actualizar_texto_accion_tema(self):
        """Actualiza el texto del QAction del menú."""
        if self.accion_cambiar_tema_visor.isChecked():
            self.accion_cambiar_tema_visor.setText("Modo Oscuro (Visor)")
        else:
            self.accion_cambiar_tema_visor.setText("Modo Claro (Visor)")

    def _precalentar_motor_grafico(self):
        """
        Ejecuta un ciclo completo de generación y renderizado con datos ficticios
        para inicializar cachés de Python, Numpy y OpenGL antes de que el usuario interactúe.
        """
        bloqueo_previo = self.signalsBlocked()
        self.blockSignals(True)
        
        try:
            self.modelo.reiniciar()
            self.modelo.nodos = {
                1: (0.0, 0.0, 0.0), 2: (1.0, 0.0, 0.0), 
                3: (1.0, 1.0, 0.0), 4: (0.0, 1.0, 0.0)
            }
            self.modelo.materiales = {1: {'tipo': 'rectangular', 'propiedades': (1,1,0.3,0.3), 'descripcion': 'Cache', 'peso_especifico': 24.0}}
            self.modelo.elementos = {1: (1, 2, 1)}
            self.modelo.losas = {1: {'nodos': [1,2,3,4], 'distribucion': 'bidireccional', 'espesor': 0.2, 'peso_especifico': 24.0}}
            self.modelo.apoyos = {1: [True]*6}
            self.modelo.cargas_nodales = [{'id_carga': 1, 'id_nodo': 2, 'id_hipotesis': 1, 'vector': [0,0,-10,0,0,0]}]
            self.modelo.hipotesis_de_carga = {1: {'nombre': 'CacheLoad', 'tipo': 'D'}}

            opciones_cache = {
                'nodos': True, 'elementos': True, 'placas': True, 'apoyos': True,
                'cargas': True, 'ids_nodos': True, 'ids_elementos': True, 'ids_placas': True,
                'ejes_locales': True, 'mostrar_secciones': True, 'mostrar_distribucion_losas': True,
                'z_min': -100, 'z_max': 100
            }

            self.gestor_visualizacion.actualizar(self.vista_preliminar, opciones_cache)
            
            if self.vista_preliminar.isValid():
                self.vista_preliminar.makeCurrent()
                self.vista_preliminar.paintGL()
            
        except Exception as e:
            print(f"Nota: Precalentamiento gráfico omitido o parcial: {e}")
        finally:
            self.modelo.reiniciar()
            self.gestor_visualizacion.actualizar(self.vista_preliminar, {})
            self.blockSignals(bloqueo_previo)
            self.refrescar_toda_la_gui()