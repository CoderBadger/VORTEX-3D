"""
Módulo: main.py
Descripción: Punto de entrada principal de VOTX3D. Inicializa la aplicación,
configura la interfaz gráfica (GUI) construida con PySide6 y enlaza los 
diferentes submódulos del programa.
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
import os
import time
from PySide6.QtWidgets import QApplication, QSplashScreen, QProgressBar
from PySide6.QtGui import QPixmap, QIcon, QColor, QFont
from PySide6.QtCore import Qt

def ruta_recurso(relative_path):
    """
    Obtiene la ruta absoluta al recurso. 
    Maneja la diferencia entre el entorno de desarrollo (con la carpeta Scripts)
    y el ejecutable compilado con PyInstaller (_MEIPASS).
    """
    try:
        base_path = sys._MEIPASS
    except Exception:
        directorio_actual = os.path.dirname(os.path.abspath(__file__))
        directorio_raiz = os.path.dirname(directorio_actual)
        base_path = directorio_raiz
        
    return os.path.join(base_path, relative_path)

if __name__ == "__main__":
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    
    # --- 1. CONFIGURACIÓN DEL ÍCONO GLOBAL ---
    ruta_icono = ruta_recurso(os.path.join("assets", "icono.ico"))
    if os.path.exists(ruta_icono):
        app.setWindowIcon(QIcon(ruta_icono))

    # --- 2. PANTALLA DE CARGA INMEDIATA ---
    ruta_imagen_splash = ruta_recurso(os.path.join("assets", "p_carga.png"))
    
    if os.path.exists(ruta_imagen_splash):
        pixmap = QPixmap(ruta_imagen_splash)
        splash = QSplashScreen(pixmap)
        
        fuente = QFont("Open Sans", 10, QFont.Bold)
        splash.setFont(fuente)
        
        barra_progreso = QProgressBar(splash)
        ancho_barra = int(pixmap.width() * 0.8)
        x_barra = int((pixmap.width() - ancho_barra) / 2)
        y_barra = pixmap.height() - 80
        
        barra_progreso.setGeometry(x_barra, y_barra, ancho_barra, 15)
        barra_progreso.setStyleSheet("""
            QProgressBar {
                border: 1px solid #bdc3c7;
                border-radius: 7px;
                background-color: #ecf0f1;
                text-align: center;
                color: transparent; 
            }
            QProgressBar::chunk {
                background-color: #2980b9; 
                border-radius: 6px;
            }
        """)
        
        splash.show()
        app.processEvents() # Forzamos a que se dibuje inmediatamente

        def actualizar_carga(mensaje, porcentaje):
            splash.showMessage(f"   {mensaje}", Qt.AlignBottom | Qt.AlignLeft, QColor("#585858"))
            barra_progreso.setValue(porcentaje)
            app.processEvents() # Evita que la ventana se congele
            time.sleep(0.2) 

        # --- 3. SECUENCIA DE IMPORTACIÓN DIFERIDA ---
        actualizar_carga("Iniciando entorno VORTEX 3D...", 10)
        
        actualizar_carga("Cargando librerías matemáticas (NumPy)...", 30)
        import numpy as np # Importación diferida

        actualizar_carga("Cargando motor de Análisis Matricial...", 50)
        import calc # Importación diferida

        actualizar_carga("Preparando motor gráfico OpenGL...", 70)
        from visualizacion import GestorVisualizacion # Importación diferida

        actualizar_carga("Ensamblando interfaz gráfica (GUI)...", 85)
        # Importación de la ventana principal al final
        from app_window import VentanaPrincipalVortex 

        actualizar_carga("Inicializando modelo estructural...", 95)
        ventana = VentanaPrincipalVortex()
        
        actualizar_carga("¡Listo!", 100)
        time.sleep(0.3)
        
        ventana.showMaximized()
        splash.finish(ventana)
        
    else:
        # Fallback de seguridad si no encuentra la imagen
        print(f"[DEBUG] No se encontró la imagen splash en: {ruta_imagen_splash}")
        from app_window import VentanaPrincipalVortex
        ventana = VentanaPrincipalVortex()
        ventana.showMaximized()
        
    sys.exit(app.exec())