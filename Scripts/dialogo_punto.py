"""
Módulo: dialogo_punto.py
Descripción: Controlador del cuadro de diálogo para la introducción y 
validación de solicitaciones (Pu, Mux, Muy), conectado directamente 
con los diagramas de interacción gestionados en la pestaña de diseño 
normativo de columnas para la verificación de la capacidad resistente.
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

from PySide6.QtWidgets import (QDialog, QVBoxLayout, QGridLayout, QLabel, 
                             QLineEdit, QPushButton, QDialogButtonBox)

class PuntoDialog(QDialog):
    """
    Una ventana de diálogo para que el usuario ingrese los datos de un nuevo punto de carga.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Añadir Punto de Carga")

        layout = QVBoxLayout(self)
        grid_layout = QGridLayout()

        grid_layout.addWidget(QLabel("Etiqueta (ej: C1, C2):"), 0, 0)
        self.label_input = QLineEdit("Punto 1")
        grid_layout.addWidget(self.label_input, 0, 1)

        grid_layout.addWidget(QLabel("Pu [kN]:"), 1, 0)
        self.pu_input = QLineEdit("1000")
        grid_layout.addWidget(self.pu_input, 1, 1)

        grid_layout.addWidget(QLabel("Mux [kN·m]:"), 2, 0)
        self.mux_input = QLineEdit("150")
        grid_layout.addWidget(self.mux_input, 2, 1)

        grid_layout.addWidget(QLabel("Muy [kN·m]:"), 3, 0)
        self.muy_input = QLineEdit("50")
        grid_layout.addWidget(self.muy_input, 3, 1)

        layout.addLayout(grid_layout)

        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

    def get_data(self):
        """Devuelve los datos ingresados como un diccionario si son válidos."""
        try:
            return {
                "label": self.label_input.text(),
                "p": float(self.pu_input.text()),
                "mx": float(self.mux_input.text()),
                "my": float(self.muy_input.text())
            }
        except (ValueError, TypeError):
            return None