"""
Módulo: interfaz_diag_int_3d.py
Descripción: Interfaz gráfica para la visualización de los diagramas de 
interacción de diseño de columnas, utilizando la librería Matplotlib.
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

import sys
import numpy as np
from PySide6.QtWidgets import (QMainWindow, QVBoxLayout, QWidget, QPushButton, 
                             QHBoxLayout, QGroupBox, QGridLayout)
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from mpl_toolkits.mplot3d import Axes3D

class Ventana3DMatplotlib(QMainWindow):
    def __init__(self, datos_malla, puntos_2d_fuerte, puntos_2d_debil, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Visor de Superficie de Interacción 3D (Matplotlib)")
        self.setGeometry(150, 150, 1100, 800) # Hacemos la ventana un poco más ancha
        
        # Datos y estado
        self.X, self.Y, self.Z = datos_malla
        self.puntos_2d_fuerte = puntos_2d_fuerte
        self.puntos_2d_debil = puntos_2d_debil
        self.puntos_demanda = []
        self.es_opaco = True
        self.eje_resaltado = 'fuerte'

        # ### CAMBIO: Layout principal ahora es Horizontal ###
        layout_principal = QHBoxLayout()
        panel_izquierdo = QWidget()
        panel_derecho = QWidget()
        layout_izquierdo = QVBoxLayout(panel_izquierdo)
        layout_derecho = QVBoxLayout(panel_derecho)
        
        panel_izquierdo.setMaximumWidth(150) # Panel de control angosto
        
        # --- Panel Izquierdo (Nuevos Controles de Vista) ---
        vista_group = QGroupBox("Control de Vista")
        vista_layout = QGridLayout(vista_group)
        
        self.boton_iso = QPushButton("Isométrica")
        self.boton_superior = QPushButton("Superior (Planta)")
        self.boton_frontal = QPushButton("Frontal (Pn-Mnx)")
        self.boton_lateral = QPushButton("Lateral (Pn-Mny)")
        
        vista_layout.addWidget(self.boton_iso, 0, 0)
        vista_layout.addWidget(self.boton_superior, 1, 0)
        vista_layout.addWidget(self.boton_frontal, 2, 0)
        vista_layout.addWidget(self.boton_lateral, 3, 0)
        
        layout_izquierdo.addWidget(vista_group)
        layout_izquierdo.addStretch()

        # --- Panel Derecho (Gráfico) ---
        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas, self)
        self.boton_transparencia = QPushButton("Hacer Transparente")
        
        toolbar_layout = QHBoxLayout()
        toolbar_layout.addWidget(self.toolbar)
        toolbar_layout.addStretch()
        toolbar_layout.addWidget(self.boton_transparencia)
        
        layout_derecho.addLayout(toolbar_layout)
        layout_derecho.addWidget(self.canvas)
        
        # Añadimos los paneles al layout principal
        layout_principal.addWidget(panel_izquierdo)
        layout_principal.addWidget(panel_derecho)
        
        widget_central = QWidget()
        widget_central.setLayout(layout_principal)
        self.setCentralWidget(widget_central)
        
        # Conectamos las señales de los nuevos botones
        self.boton_transparencia.clicked.connect(self.toggle_transparencia)
        self._connect_view_buttons()

        self.ax = self.figure.add_subplot(111, projection='3d')
        self.redibujar_todo()

    def _connect_view_buttons(self):
        self.boton_iso.clicked.connect(lambda: self.cambiar_vista(elev=30, azim=-60))
        self.boton_superior.clicked.connect(lambda: self.cambiar_vista(elev=90, azim=-90)) # Vista desde arriba
        self.boton_frontal.clicked.connect(lambda: self.cambiar_vista(elev=0, azim=-90)) # Vista de frente (plano Pn-Mnx)
        self.boton_lateral.clicked.connect(lambda: self.cambiar_vista(elev=0, azim=0)) # Vista de lado (plano Pn-Mny)

    def cambiar_vista(self, elev, azim):
        """Ajusta la cámara del gráfico 3D y redibuja."""
        self.ax.view_init(elev=elev, azim=azim)
        self.canvas.draw()

    def redibujar_todo(self):
        """Función maestra que limpia y redibuja todos los elementos."""
        posicion_camara = self.ax.getView() if hasattr(self.ax, 'getView') else (30, -60)
        self.ax.clear()
        
        alpha = 1.0 if self.es_opaco else 0.4
        self.ax.plot_surface(self.X, self.Y, self.Z, cmap='viridis', edgecolor='royalblue', linewidth=0.3, alpha=alpha, rstride=1, cstride=1)
        
        self._dibujar_puntos_en_ejes()
        self._resaltar_eje_en_ejes()
        
        self.ax.set_xlabel('Mnx (kN·m)', fontweight='bold'); self.ax.set_ylabel('Mny (kN·m)', fontweight='bold')
        self.ax.set_zlabel('Pn (kN)', fontweight='bold'); self.ax.set_title('Superficie de Interacción de Diseño', fontsize=14, fontweight='bold')
        self.ax.invert_xaxis()
        
        self.ax.view_init(elev=posicion_camara[0], azim=posicion_camara[1])
        self.canvas.draw()

    def toggle_transparencia(self):
        self.es_opaco = not self.es_opaco
        self.boton_transparencia.setText("Hacer Transparente" if self.es_opaco else "Hacer Opaco")
        self.redibujar_todo()

    def resaltar_eje(self, eje):
        self.eje_resaltado = eje
        self.redibujar_todo()
    
    def _resaltar_eje_en_ejes(self):
        puntos = self.puntos_2d_fuerte if self.eje_resaltado == 'fuerte' else self.puntos_2d_debil
        linea_x = np.array([p[0]/1e6 for p in puntos if p])
        linea_y = np.zeros_like(linea_x) if self.eje_resaltado == 'fuerte' else np.array([p[0]/1e6 for p in puntos if p])
        if self.eje_resaltado == 'debil': linea_x = np.zeros_like(linea_y)
        linea_z = np.array([p[1]/1000 for p in puntos if p])
        self.ax.plot(linea_x, linea_y, linea_z, color='magenta', linewidth=4)

    def dibujar_puntos_3d(self, puntos_demanda):
        self.puntos_demanda = puntos_demanda
        self.redibujar_todo()

    def _dibujar_puntos_en_ejes(self):
        if not self.puntos_demanda: return
            
        mx_vals = [abs(p['mx']) for p in self.puntos_demanda]
        my_vals = [abs(p['my']) for p in self.puntos_demanda]
        p_vals = [p['p'] for p in self.puntos_demanda]

        self.ax.scatter(mx_vals, my_vals, p_vals, s=80, c='red', edgecolor='black', depthshade=False)
        
        min_x, _ = self.ax.get_xlim(); min_y, _ = self.ax.get_ylim()
        for mx, my, p in zip(mx_vals, my_vals, p_vals):
            self.ax.plot([mx, min_x], [my, my], [p, p], 'k--', lw=0.8, alpha=0.7)
            self.ax.plot([mx, mx], [my, min_y], [p, p], 'k--', lw=0.8, alpha=0.7)