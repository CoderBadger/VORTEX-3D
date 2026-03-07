"""
Módulo: visualizacion.py
Descripción: Motor de renderizado de alto rendimiento. Utiliza OpenGL (vía PySide)
para dibujar la geometría 3D de la estructura, los ejes locales, las cargas 
aplicadas, diagramas de esfuerzos internos, etc.
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

import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QPainter, QColor
from PySide6.QtOpenGLWidgets import QOpenGLWidget
from collections import defaultdict
from OpenGL import GL as gl
from OpenGL import GLU as glu
import math
from diagramas import GeneradorDiagramas
from distribuidor_losas import (_encontrar_losa_adyacente, _rotar_vector_2d, _calcular_interseccion_lineas, 
                                _calcular_area_poligono, _encontrar_vigas_de_borde, _ordenar_vertices_poligono, _calcular_geometria_aporte_bidireccional)

# --- DEFINICIÓN CENTRALIZADA DE PALETAS DE COLORES ---

PALETAS_TEMA = {
    "oscuro": {
        "fondo": QColor(25, 25, 35),
        "texto": QColor("white"),
        "ejes": {'X': QColor("red"), 'Y': QColor("green"), 'Z': QColor("blue")},
        "nodo": QColor("magenta"),
        "apoyo": QColor(0, 100, 255), # Azul eléctrico
        "elemento_defecto": QColor(100, 100, 255),
        "seccion_transversal": QColor("white"),
        "losa_borde": QColor(200, 200, 200),
        "losa_relleno": QColor(120, 120, 150, 255), # Gris azulado semitransparente
        "carga": QColor("red"),
        "carga_losa_relleno": QColor(255, 80, 80, 70),
        "distribucion_losas": QColor(0, 255, 255, 200), # Cyan
        "distribucion_relleno": QColor(0, 255, 255, 128),
        "diagrama_relleno": QColor(50, 150, 255, 80),
        "diagrama_linea": QColor(50, 150, 255),
        "diagrama_texto": QColor("yellow"),
        "deformada_linea": QColor("orange"),      # Color resaltante
        "deformada_texto": QColor("yellow"),
        # Paleta cíclica para materiales por ID
        "materiales": [
            QColor(100, 100, 255), QColor("#FFFFFF"), QColor("#DA70D6"),
            QColor("#98FB98"), QColor("#F08080")
        ]
    },
    "claro": {
        "fondo": QColor("white"),
        "texto": QColor("black"),
        "ejes": {'X': QColor(200, 0, 0), 'Y': QColor(0, 150, 0), 'Z': QColor(0, 0, 200)}, # Colores más oscuros para contraste
        "nodo": QColor("darkmagenta"),
        "apoyo": QColor(0, 0, 180), # Azul oscuro
        "elemento_defecto": QColor(0, 0, 120), # Azul marino muy oscuro
        "seccion_transversal": QColor("black"),
        "losa_borde": QColor("black"),
        "losa_relleno": QColor(203, 203, 221, 255), # Gris muy claro semitransparente
        "carga": QColor(220, 0, 0), # Rojo oscuro
        "carga_losa_relleno": QColor(255, 0, 0, 40),
        "distribucion_losas": QColor(0, 128, 128, 255), # Teal (Verde azulado oscuro)
        "distribucion_relleno": QColor(0, 128, 128, 80),
        "diagrama_relleno": QColor(0, 100, 255, 60), # Azul suave semitransparente
        "diagrama_linea": QColor(0, 0, 180), # Azul oscuro contorno
        "diagrama_texto": QColor("black"),
        "deformada_linea": QColor(255, 140, 0),   # Naranja oscuro
        "deformada_texto": QColor("blue"),
        # Paleta cíclica para materiales (colores saturados/oscuros para fondo blanco)
        "materiales": [
            QColor(0, 0, 180),       # Azul oscuro
            QColor("#000000"),       # Negro
            QColor("#800080"),       # Púrpura
            QColor("#006400"),       # Verde bosque
            QColor("#8B0000")        # Rojo oscuro
        ]
    }
}

# --- CLASE PRINCIPAL DEL VISOR ---

class GLViewer(QOpenGLWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.text_labels = []
        
        # Estado inicial del tema
        self.modo_tema = "oscuro" # Por defecto
        self.background_color = PALETAS_TEMA["oscuro"]["fondo"]
        
        self.setMinimumSize(400, 300)

        # Parámetros de Cámara
        self.camera_zoom = 20.0
        self.camera_rot_x = 30.0
        self.camera_rot_z = -135.0
        self.focal_point = np.array([0.0, 0.0, 5.0])
        self.last_pos = None
        self.setFocusPolicy(Qt.StrongFocus)
        
        # --- Atributos para VBO/VAO ---
        self.vbos = {} 
        self.data_count = {} 
        self.buffers_inicializados = False
        self.line_width_map = {} # Mapa para grosores de línea
        self.reaction_labels = []

    def _inicializar_buffers_vbo(self):
        """Inicializa los buffers de la tarjeta gráfica (VBOs/VAOs)."""
        if self.buffers_inicializados:
            return
        
        # Tipos de geometría para Batching: Puntos, Líneas, Polígonos, Diagramas
        self.tipos_geometria = ["puntos", "lineas", "poligonos", "diagram_fill", "diagram_line"]
        
        for tipo in self.tipos_geometria:
            self.vbos[f'{tipo}_vbo_id'] = gl.glGenBuffers(1)
            self.vbos[f'{tipo}_color_vbo_id'] = gl.glGenBuffers(1)
            self.data_count[tipo] = 0

        self.buffers_inicializados = True

    def actualizar_buffers(self, compiled_data):
        """
        Sube la geometría compilada (arrays de NumPy) a los VBOs de la tarjeta gráfica.
        """
        self.makeCurrent()
        
        if not self.buffers_inicializados:
            return

        for tipo in self.tipos_geometria:
            verts = compiled_data.get(f'{tipo}_verts', np.array([], dtype=np.float32))
            colors = compiled_data.get(f'{tipo}_colors', np.array([], dtype=np.float32))
            
            self.data_count[tipo] = verts.shape[0] if verts.ndim > 1 else 0

            # Subir datos de VÉRTICES (posición)
            if self.data_count[tipo] > 0:
                gl.glBindBuffer(gl.GL_ARRAY_BUFFER, self.vbos[f'{tipo}_vbo_id'])
                gl.glBufferData(gl.GL_ARRAY_BUFFER, verts.nbytes, verts, gl.GL_STATIC_DRAW)

            # Subir datos de COLORES
            if self.data_count[tipo] > 0:
                gl.glBindBuffer(gl.GL_ARRAY_BUFFER, self.vbos[f'{tipo}_color_vbo_id'])
                gl.glBufferData(gl.GL_ARRAY_BUFFER, colors.nbytes, colors, gl.GL_STATIC_DRAW)
            
            # Guardar el mapa de grosores de línea
            if tipo == 'lineas':
                 self.line_width_map = compiled_data.get('lineas_widths', {})
            
        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, 0)
        
    def clear_scene(self):
        self.makeCurrent()
        self.text_labels.clear()
        
    def set_focal_point(self, point):
        self.focal_point = np.array(point)
        self.update()

    def initializeGL(self):
        gl.glEnable(gl.GL_DEPTH_TEST)
        gl.glEnable(gl.GL_BLEND)
        gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
        gl.glEnable(gl.GL_LINE_SMOOTH)
        gl.glHint(gl.GL_LINE_SMOOTH_HINT, gl.GL_NICEST)
        gl.glEnable(gl.GL_POLYGON_OFFSET_FILL)
        gl.glPolygonOffset(1.0, 1.0)
        self._inicializar_buffers_vbo()

    def resizeGL(self, width, height):
        if height == 0: height = 1
        gl.glViewport(0, 0, width, height)
        gl.glMatrixMode(gl.GL_PROJECTION)
        gl.glLoadIdentity()
        glu.gluPerspective(45, width / float(height), 0.1, 5000.0)
        gl.glMatrixMode(gl.GL_MODELVIEW)

    def paintGL(self):
        # Usar el color de fondo dinámico
        gl.glClearColor(self.background_color.redF(), self.background_color.greenF(), self.background_color.blueF(), 1.0)
        gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT)
        gl.glLoadIdentity()
        
        # Lógica de la cámara
        rad_x = math.radians(self.camera_rot_x)
        rad_z = math.radians(self.camera_rot_z)
        eye_x = self.focal_point[0] + self.camera_zoom * math.cos(rad_x) * math.cos(rad_z)
        eye_y = self.focal_point[1] + self.camera_zoom * math.cos(rad_x) * math.sin(rad_z)
        eye_z = self.focal_point[2] + self.camera_zoom * math.sin(rad_x)
        
        glu.gluLookAt(eye_x, eye_y, eye_z, 
                      self.focal_point[0], self.focal_point[1], self.focal_point[2],
                      0, 0, 1)

        try:
            modelview = gl.glGetDoublev(gl.GL_MODELVIEW_MATRIX)
            projection = gl.glGetDoublev(gl.GL_PROJECTION_MATRIX)
            viewport = gl.glGetIntegerv(gl.GL_VIEWPORT)
        except gl.error.GLError:
            modelview, projection, viewport = None, None, None
            
        if self.buffers_inicializados:
            self._renderizar_buffers() 
        
        self.render_text_labels(modelview, projection, viewport)
        self.render_reaction_labels(modelview, projection, viewport)
        
    def _renderizar_buffers(self):
        """
        Dibuja toda la escena usando VBOs con orden de prioridad para oclusión correcta.
        """
        gl.glEnableClientState(gl.GL_VERTEX_ARRAY)
        gl.glEnableClientState(gl.GL_COLOR_ARRAY)
        
        # --- 1. DIBUJAR LOSAS (OPACAS) ---
        tipo = "poligonos"
        if self.data_count[tipo] > 0:
            gl.glDisable(gl.GL_BLEND)  
            gl.glEnable(gl.GL_DEPTH_TEST) 
            
            gl.glBindBuffer(gl.GL_ARRAY_BUFFER, self.vbos[f'{tipo}_vbo_id'])
            gl.glVertexPointer(3, gl.GL_FLOAT, 0, None)
            gl.glBindBuffer(gl.GL_ARRAY_BUFFER, self.vbos[f'{tipo}_color_vbo_id'])
            gl.glColorPointer(4, gl.GL_FLOAT, 0, None)
            
            gl.glEnable(gl.GL_POLYGON_OFFSET_FILL)
            gl.glPolygonOffset(1.0, 1.0)
            
            gl.glDrawArrays(gl.GL_QUADS, 0, self.data_count[tipo])
            
            gl.glDisable(gl.GL_POLYGON_OFFSET_FILL)
            gl.glEnable(gl.GL_BLEND) 

        # --- 2. DIBUJAR RELLENO DE DIAGRAMAS (TRANSPARENTE) ---
        tipo = "diagram_fill"
        if self.data_count[tipo] > 0:
            gl.glBindBuffer(gl.GL_ARRAY_BUFFER, self.vbos[f'{tipo}_vbo_id'])
            gl.glVertexPointer(3, gl.GL_FLOAT, 0, None)
            gl.glBindBuffer(gl.GL_ARRAY_BUFFER, self.vbos[f'{tipo}_color_vbo_id'])
            gl.glColorPointer(4, gl.GL_FLOAT, 0, None)
            gl.glDrawArrays(gl.GL_QUADS, 0, self.data_count[tipo])

        # --- 3. DIBUJAR LÍNEAS (Elementos 1D, Ejes, Cargas, etc.) ---
        tipo = "lineas"
        if self.data_count[tipo] > 0:
            gl.glBindBuffer(gl.GL_ARRAY_BUFFER, self.vbos[f'{tipo}_vbo_id'])
            gl.glVertexPointer(3, gl.GL_FLOAT, 0, None)
            gl.glBindBuffer(gl.GL_ARRAY_BUFFER, self.vbos[f'{tipo}_color_vbo_id'])
            gl.glColorPointer(4, gl.GL_FLOAT, 0, None)
            
            indice_inicio = 0
            for ancho, count in sorted(self.line_width_map.items()): 
                gl.glLineWidth(ancho)
                gl.glDrawArrays(gl.GL_LINES, indice_inicio, count)
                indice_inicio += count
        
        # --- 4. DIBUJAR LÍNEAS DE DIAGRAMA ---
        tipo = "diagram_line"
        if self.data_count[tipo] > 0:
            gl.glBindBuffer(gl.GL_ARRAY_BUFFER, self.vbos[f'{tipo}_vbo_id'])
            gl.glVertexPointer(3, gl.GL_FLOAT, 0, None)
            gl.glBindBuffer(gl.GL_ARRAY_BUFFER, self.vbos[f'{tipo}_color_vbo_id'])
            gl.glColorPointer(4, gl.GL_FLOAT, 0, None)
            gl.glLineWidth(2.0)
            gl.glDrawArrays(gl.GL_LINE_STRIP, 0, self.data_count[tipo])

        # --- 5. DIBUJAR PUNTOS (Nodos) ---
        tipo = "puntos"
        if self.data_count[tipo] > 0:
            gl.glEnable(gl.GL_POINT_SMOOTH)
            gl.glPointSize(8.0) 
            gl.glBindBuffer(gl.GL_ARRAY_BUFFER, self.vbos[f'{tipo}_vbo_id'])
            gl.glVertexPointer(3, gl.GL_FLOAT, 0, None)
            gl.glBindBuffer(gl.GL_ARRAY_BUFFER, self.vbos[f'{tipo}_color_vbo_id'])
            gl.glColorPointer(4, gl.GL_FLOAT, 0, None)
            gl.glDrawArrays(gl.GL_POINTS, 0, self.data_count[tipo])
            gl.glDisable(gl.GL_POINT_SMOOTH)
            
        gl.glDisableClientState(gl.GL_COLOR_ARRAY)
        gl.glDisableClientState(gl.GL_VERTEX_ARRAY)
        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, 0)

    def render_text_labels(self, modelview, projection, viewport):
        if modelview is None: return
        
        pixel_ratio = self.devicePixelRatioF()
        if pixel_ratio == 0: pixel_ratio = 1.0

        painter = QPainter()
        painter.begin(self) 
        
        try:
            painter.setRenderHint(QPainter.Antialiasing)
            font = QFont("Arial", 10)
            font.setBold(True)
            painter.setFont(font)
            
            for label in self.text_labels:
                pos3d = label['position']
                win_coords = glu.gluProject(pos3d[0], pos3d[1], pos3d[2], modelview, projection, viewport)
                
                if win_coords:
                    screen_x_logico = win_coords[0] / pixel_ratio
                    screen_y_logico = (viewport[3] - win_coords[1]) / pixel_ratio

                    if 0 < screen_x_logico < self.width() and 0 < screen_y_logico < self.height():
                        painter.setPen(label['color'])
                        painter.drawText(int(screen_x_logico) + 5, int(screen_y_logico) - 5, label['text'])
        
        finally:
            painter.end()

    def render_reaction_labels(self, modelview, projection, viewport):
        """Dibuja las etiquetas de reacciones con fondo blanco y borde negro."""
        if modelview is None or not self.reaction_labels: return
        
        pixel_ratio = self.devicePixelRatioF() or 1.0
        
        painter = QPainter()
        if not painter.begin(self): return # Seguridad por si el dispositivo no está listo
        
        try:
            painter.setRenderHint(QPainter.Antialiasing)
            font = QFont("Consolas", 9) # Fuente monoespaciada para que alineen los números
            font.setBold(True)
            painter.setFont(font)
            
            # Métricas para calcular tamaño de la caja
            metrics = painter.fontMetrics()
            altura_linea = metrics.height()
            
            for label in self.reaction_labels:
                pos3d = label['position']
                win_coords = glu.gluProject(pos3d[0], pos3d[1], pos3d[2], modelview, projection, viewport)
                
                # Verificar que la proyección fue exitosa y que el punto está frente a la cámara (win_coords[2] < 1.0)
                if win_coords and 0.0 <= win_coords[2] <= 1.0:
                    screen_x = win_coords[0] / pixel_ratio
                    screen_y = (viewport[3] - win_coords[1]) / pixel_ratio # Invertir Y OpenGL a Y Pantalla

                    # Solo dibujar si está dentro del área visible (con un margen)
                    if -100 < screen_x < self.width() + 100 and -100 < screen_y < self.height() + 100:
                        texto = label['text']
                        lineas = texto.split('\n')
                        
                        # Calcular dimensiones del recuadro
                        ancho_max = max(metrics.horizontalAdvance(l) for l in lineas) + 10
                        alto_total = (len(lineas) * altura_linea) + 10
                        
                        # Posición del recuadro (offset para no tapar el nodo)
                        x_rect = int(screen_x) + 10
                        y_rect = int(screen_y) - int(alto_total / 2)
                        
                        # Dibujar Caja (Fondo blanco, borde negro)
                        painter.setPen(QColor("black"))
                        painter.setBrush(QColor("white"))
                        painter.drawRect(x_rect, y_rect, ancho_max, alto_total)
                        
                        # Dibujar Texto (Línea por línea)
                        painter.setPen(QColor("black"))
                        for i, linea in enumerate(lineas):
                            y_texto = y_rect + 5 + (i + 1) * altura_linea - metrics.descent()
                            painter.drawText(x_rect + 5, y_texto, linea)
                            
        finally:
            painter.end()

    # --- EVENTOS DE RATÓN Y TECLADO ---
    def wheelEvent(self, event):
        delta = event.angleDelta().y() / 120.0
        zoom_factor = 1.05 if event.modifiers() & Qt.ShiftModifier else 1.2
        if delta > 0: self.camera_zoom /= zoom_factor
        else: self.camera_zoom *= zoom_factor
        self.camera_zoom = max(1, self.camera_zoom)
        self.update()

    def keyPressEvent(self, event):
        modifiers = event.modifiers()
        if modifiers == Qt.AltModifier:
            if event.key() == Qt.Key_1:
                self.camera_rot_x = 30.0
                self.camera_rot_z = -135.0
                self.update()
            elif event.key() == Qt.Key_2:
                self.camera_rot_x = 0.0
                self.camera_rot_z = -90.0
                self.update()
            elif event.key() == Qt.Key_3:
                self.camera_rot_x = 0.0
                self.camera_rot_z = 0.0
                self.update()
            elif event.key() == Qt.Key_4:
                self.camera_rot_x = 90.0
                self.camera_rot_z = 0.0
                self.update()
        else:
            super().keyPressEvent(event)

    def mousePressEvent(self, event):
        self.last_pos = event.pos()

    def mouseMoveEvent(self, event):
        if not self.last_pos: return
        dx = event.pos().x() - self.last_pos.x()
        dy = event.pos().y() - self.last_pos.y()
        
        if event.buttons() & Qt.LeftButton:
            self.camera_rot_x += dy * 0.25
            self.camera_rot_z -= dx * 0.25
            self.camera_rot_x = max(-89.0, min(89.0, self.camera_rot_x))

        elif event.buttons() & Qt.MiddleButton:
            pan_speed = self.camera_zoom * 0.001
            shift_pressed = bool(event.modifiers() & Qt.ShiftModifier)
            ctrl_pressed = bool(event.modifiers() & Qt.ControlModifier)

            if ctrl_pressed and shift_pressed:
                self.focal_point[0] -= dx * pan_speed
            elif ctrl_pressed:
                self.focal_point[1] += dy * pan_speed
            elif shift_pressed:
                self.focal_point[2] += dy * pan_speed
            else:
                self.makeCurrent()
                modelview = gl.glGetDoublev(gl.GL_MODELVIEW_MATRIX)
                right = np.array([modelview[0][0], modelview[1][0], modelview[2][0]])
                up = np.array([modelview[0][1], modelview[1][1], modelview[2][1]])
                self.focal_point -= right * dx * pan_speed
                self.focal_point += up * dy * pan_speed
        
        self.last_pos = event.pos()
        self.update()

    def set_tema_fondo(self, modo):
        """Actualiza el estado del tema y el color de fondo OpenGL."""
        # Validar que el modo exista, si no fallback a oscuro
        modo_seguro = modo if modo in PALETAS_TEMA else "oscuro"
        
        self.modo_tema = modo_seguro
        # Extraer el color de fondo de la paleta centralizada
        self.background_color = PALETAS_TEMA[modo_seguro]["fondo"]
        
        self.update()


# --- GESTOR DE VISUALIZACIÓN (COMPILADOR DE VBOs) ---
class GestorVisualizacion:
    def __init__(self, modelo):
        self.modelo = modelo
        self.generador_diagramas = None
        # NOTA: Ya no inicializamos colores aquí. Se leen dinámicamente de PALETAS_TEMA.

    # --- FUNCIONES GEOMÉTRICAS ---
    def _ordenar_nodos_placa(self, coords):
        centro = np.mean(coords, axis=0)
        v1 = coords[1] - coords[0]; v2 = coords[2] - coords[0]
        normal = np.cross(v1, v2)
        if abs(normal[2]) > abs(normal[0]) and abs(normal[2]) > abs(normal[1]): 
            idx1, idx2 = 0, 1
        elif abs(normal[1]) > abs(normal[0]): 
            idx1, idx2 = 0, 2
        else: 
            idx1, idx2 = 1, 2
        angulos = [];
        for p in coords:
            dx = p[idx1] - centro[idx1]
            dy = p[idx2] - centro[idx2]
            angulo = math.atan2(dy, dx)
            angulos.append(angulo)
        coords_ordenadas = [c for _, c in sorted(zip(angulos, coords))]
        return coords_ordenadas

    def _get_ejes_locales(self, p1, p2):
        v = np.array(p2) - np.array(p1)
        L = np.linalg.norm(v)
        if L < 1e-9: 
            return np.array([1.,0.,0.]), np.array([0.,1.,0.]), np.array([0.,0.,1.])
        vx = v / L
        v_up = np.array([0.0, 0.0, 1.0])
        if np.allclose(np.abs(vx), v_up):
            vy_ref = np.array([1.0, 0.0, 0.0])
            vz = np.cross(vx, vy_ref)
            vz /= np.linalg.norm(vz)
            vy = np.cross(vz, vx)
        else:
            vy = np.cross(v_up, vx)
            vy /= np.linalg.norm(vy)
            vz = np.cross(vx, vy)
        return vx, vy, vz
    
    def _calcular_normal_placa(self, coords_ordenadas):
        v1 = coords_ordenadas[1] - coords_ordenadas[0]
        v2 = coords_ordenadas[-1] - coords_ordenadas[0]
        normal = np.cross(v1, v2)
        norma = np.linalg.norm(normal)
        if norma == 0: return np.array([0, 0, 1]) 
        return normal / norma

    # --- FUNCIONES DE ADICIÓN DE GEOMETRÍA ---
    
    def _add_puntos(self, verts_list, colors_list, coords, color_q):
        verts_list.append(coords.astype(np.float32))
        colors_list.append(np.array([color_q.redF(), color_q.greenF(), color_q.blueF(), color_q.alphaF()], dtype=np.float32))

    def _agregar_linea(self, lista_vertices, lista_colores, mapa_anchos, p_inicio, p_fin, color_q, ancho=1.5):
        lista_vertices.append(p_inicio.astype(np.float32))
        lista_vertices.append(p_fin.astype(np.float32))
        color_data = np.array([color_q.redF(), color_q.greenF(), color_q.blueF(), color_q.alphaF()], dtype=np.float32)
        lista_colores.append(color_data)
        lista_colores.append(color_data)
        mapa_anchos[ancho] += 2

    def _add_quad(self, verts_list, colors_list, p1, p2, p3, p4, color_q):
        verts_list.append(p1.astype(np.float32))
        verts_list.append(p2.astype(np.float32))
        verts_list.append(p3.astype(np.float32))
        verts_list.append(p4.astype(np.float32))
        color_data = np.array([color_q.redF(), color_q.greenF(), color_q.blueF(), color_q.alphaF()], dtype=np.float32)
        colors_list.extend([color_data] * 4)

    def _add_label(self, labels_list, text, position, color, opcion_activa):
        if opcion_activa:
            labels_list.append({'text': text, 'position': position, 'color': color})

    # --- LÓGICA DE COMPILACIÓN PRINCIPAL ---
    
    def _compilar_geometria(self, opciones, paleta, lista_reacciones=None):
        """
        Compila toda la geometría usando la paleta de colores inyectada.
        """
        datos_compilados = {
            'puntos_verts': [], 'puntos_colors': [],
            'lineas_verts': [], 'lineas_colors': [], 'lineas_widths_map': defaultdict(int),
            'poligonos_verts': [], 'poligonos_colors': [],
            'diagram_fill_verts': [], 'diagram_fill_colors': [],
            'diagram_line_verts': [], 'diagram_line_colors': []
        }
        labels = []
        
        # --- Lectura de opciones ---
        opcion_ids_elementos = opciones.get('ids_elementos', True)
        opcion_ids_placas = opciones.get('ids_placas', True)
        opcion_ids_nodos = opciones.get('ids_nodos', True)
        # --- MODIFICADO: Lectura de Cortes ---
        cortes = opciones.get('limites_corte', {})
        # Valores por defecto muy grandes si no existen
        x_min = cortes.get('x_min', -float('inf'))
        x_max = cortes.get('x_max', float('inf'))
        y_min = cortes.get('y_min', -float('inf'))
        y_max = cortes.get('y_max', float('inf'))
        z_min = cortes.get('z_min', -float('inf'))
        z_max = cortes.get('z_max', float('inf'))
        
        # --- Filtrado de Nodos (Lógica AND en los 3 ejes) ---
        nodos_visibles_ids = set()
        for id_nodo, coords in self.modelo.nodos.items():
            x, y, z = coords
            # Verificación en los 3 ejes
            en_x = x_min <= x <= x_max
            en_y = y_min <= y <= y_max
            en_z = z_min <= z <= z_max
            
            if en_x and en_y and en_z:
                nodos_visibles_ids.add(id_nodo)

        # --- LÓGICA DE REACCIONES (NUEVO) ---
        mostrar_reacciones = opciones.get('mostrar_reacciones', False)
        resultados = opciones.get('resultados_diagrama_especificos', None)
        
        if mostrar_reacciones and resultados and lista_reacciones is not None:
            # Ahora sabemos que esto es un numpy array plano de tamaño (N_nodos * 6)
            reacciones_vector = resultados.get('reacciones')
            
            if reacciones_vector is not None:
                # Iterar SOLAMENTE sobre los nodos que son apoyos (Requerimiento y Optimización)
                # Usamos self.modelo.apoyos para saber cuáles son
                for id_nodo_reac in self.modelo.apoyos:
                    # Verificar visibilidad (si cortamos la vista, no mostrar etiquetas flotando)
                    if id_nodo_reac in nodos_visibles_ids:
                        
                        # Calcular los índices en el vector global (6 GDL por nodo)
                        idx_base = (id_nodo_reac - 1) * 6
                        
                        # Protección por si el vector no coincide en tamaño
                        if idx_base + 6 > len(reacciones_vector): 
                            continue
                            
                        # Extraer las 6 componentes del vector plano
                        vector_reac = reacciones_vector[idx_base : idx_base + 6]
                        
                        # --- Formateo del Texto (Igual que antes) ---
                        lineas_texto = []
                        etiquetas = ["Fx", "Fy", "Fz", "Mx", "My", "Mz"]
                        unidades = ["kN", "kN", "kN", "kNm", "kNm", "kNm"]
                        
                        hay_valor = False
                        for i in range(6):
                            val = vector_reac[i]
                            # Filtro: Mostrar solo si valor absoluto > 0.001 (para limpiar ruido numérico)
                            if abs(val) >= 0.001: 
                                lineas_texto.append(f"{etiquetas[i]}={val:.2f}{unidades[i]}")
                                hay_valor = True
                        
                        if hay_valor: 
                            texto_final = "\n".join(lineas_texto)
                            coords_nodo = self.modelo.nodos[id_nodo_reac]
                            
                            lista_reacciones.append({
                                'text': texto_final,
                                'position': np.array(coords_nodo)
                            })

        # --- 0. EJES GLOBALES ---
        eje_len = 5
        self._agregar_linea(datos_compilados['lineas_verts'], datos_compilados['lineas_colors'], datos_compilados['lineas_widths_map'], np.array([0,0,0]), np.array([eje_len,0,0]), paleta['ejes']['X'], 1.5)
        self._agregar_linea(datos_compilados['lineas_verts'], datos_compilados['lineas_colors'], datos_compilados['lineas_widths_map'], np.array([0,0,0]), np.array([0,eje_len,0]), paleta['ejes']['Y'], 1.5)
        self._agregar_linea(datos_compilados['lineas_verts'], datos_compilados['lineas_colors'], datos_compilados['lineas_widths_map'], np.array([0,0,0]), np.array([0,0,eje_len]), paleta['ejes']['Z'], 1.5)
        
        self._add_label(labels, "X", (eje_len + 0.5, 0, 0), paleta['ejes']['X'], True)
        self._add_label(labels, "Y", (0, eje_len + 0.5, 0), paleta['ejes']['Y'], True)
        self._add_label(labels, "Z", (0, 0, eje_len + 0.5), paleta['ejes']['Z'], True)

        # --- 1. ELEMENTOS 1D ---
        if opciones.get('elementos', True) and self.modelo.elementos:
            for id_elem, (ni, nj, id_mat) in self.modelo.elementos.items():
                if ni not in nodos_visibles_ids or nj not in nodos_visibles_ids: continue 
                
                if ni in self.modelo.nodos and nj in self.modelo.nodos:
                    p1 = np.array(self.modelo.nodos[ni]); p2 = np.array(self.modelo.nodos[nj])
                    
                    # Selección de color de material desde la paleta
                    color_elemento = paleta['elemento_defecto']
                    if id_mat in self.modelo.materiales:
                        color_idx = (id_mat - 1) % len(paleta['materiales'])
                        color_elemento = paleta['materiales'][color_idx]

                    self._agregar_linea(datos_compilados['lineas_verts'], datos_compilados['lineas_colors'], datos_compilados['lineas_widths_map'], p1, p2, color_elemento, 1.5)

                    # Etiqueta de elemento
                    self._add_label(labels, f"E{id_elem}", (p1+p2)/2, paleta['texto'], opcion_ids_elementos)

                    if opciones.get('ejes_locales', False):
                        vx, vy, vz = self._get_ejes_locales(p1, p2); centro = (p1 + p2) / 2.0
                        escala_eje = 0.5; ancho_eje = 2.0
                        self._agregar_linea(datos_compilados['lineas_verts'], datos_compilados['lineas_colors'], datos_compilados['lineas_widths_map'], centro, centro + vx * escala_eje, paleta['ejes']['X'], ancho_eje)
                        self._agregar_linea(datos_compilados['lineas_verts'], datos_compilados['lineas_colors'], datos_compilados['lineas_widths_map'], centro, centro + vy * escala_eje, paleta['ejes']['Y'], ancho_eje)
                        self._agregar_linea(datos_compilados['lineas_verts'], datos_compilados['lineas_colors'], datos_compilados['lineas_widths_map'], centro, centro + vz * escala_eje, paleta['ejes']['Z'], ancho_eje)

                    if opciones.get('mostrar_secciones', False) and id_mat in self.modelo.materiales:
                        datos_mat = self.modelo.materiales[id_mat]
                        if datos_mat.get('tipo', 'rectangular') == 'rectangular':
                            _, _, b, h, *_ = datos_mat['propiedades']; _, vy, vz = self._get_ejes_locales(p1, p2)
                            punto_medio = (p1 + p2) / 2.0
                            c1 = punto_medio - (vy * b / 2) + (vz * h / 2); c2 = punto_medio + (vy * b / 2) + (vz * h / 2)
                            c3 = punto_medio + (vy * b / 2) - (vz * h / 2); c4 = punto_medio - (vy * b / 2) - (vz * h / 2)
                            color_seccion = paleta['seccion_transversal']; ancho_seccion = 2.0
                            self._agregar_linea(datos_compilados['lineas_verts'], datos_compilados['lineas_colors'], datos_compilados['lineas_widths_map'], c1, c2, color_seccion, ancho_seccion)
                            self._agregar_linea(datos_compilados['lineas_verts'], datos_compilados['lineas_colors'], datos_compilados['lineas_widths_map'], c2, c3, color_seccion, ancho_seccion)
                            self._agregar_linea(datos_compilados['lineas_verts'], datos_compilados['lineas_colors'], datos_compilados['lineas_widths_map'], c3, c4, color_seccion, ancho_seccion)
                            self._agregar_linea(datos_compilados['lineas_verts'], datos_compilados['lineas_colors'], datos_compilados['lineas_widths_map'], c4, c1, color_seccion, ancho_seccion)
                            etiqueta_texto = f"{b:.2f} x {h:.2f}"; posicion_etiqueta = c2 + (vz * 0.1)
                            self._add_label(labels, etiqueta_texto, posicion_etiqueta, color_seccion, True) 

        # --- 2. LOSAS (Polígonos) ---
        if opciones.get('placas', True) and self.modelo.losas:
            for id_placa, datos_placa in self.modelo.losas.items():
                nodos_ids = datos_placa['nodos']; coords = [self.modelo.nodos.get(nid) for nid in nodos_ids]
                if not all(nid in nodos_visibles_ids for nid in nodos_ids): continue
                
                if all(c is not None for c in coords):
                    coords_ordenadas = self._ordenar_nodos_placa(np.array(coords))
                    
                    # Dibujar relleno
                    self._add_quad(datos_compilados['poligonos_verts'], datos_compilados['poligonos_colors'], 
                                   coords_ordenadas[0], coords_ordenadas[1], coords_ordenadas[2], coords_ordenadas[3], paleta['losa_relleno'])
                    
                    # Dibujar borde (opcional, para mejor visibilidad)
                    for i in range(4):
                        self._agregar_linea(datos_compilados['lineas_verts'], datos_compilados['lineas_colors'], datos_compilados['lineas_widths_map'],
                                            coords_ordenadas[i], coords_ordenadas[(i+1)%4], paleta['losa_borde'], 1.0)

                    centro = np.mean(coords, axis=0)
                    self._add_label(labels, f"L{id_placa}", centro, paleta['texto'], opcion_ids_placas)

        # --- 3. DISTRIBUCIÓN DE LOSAS (Líneas) ---
        if opciones.get('mostrar_distribucion_losas', False):
            # CORRECCIÓN: Pasamos nodos_visibles_ids para filtrar
            self._compilar_distribucion_losas(datos_compilados['lineas_verts'], datos_compilados['lineas_colors'], datos_compilados['lineas_widths_map'], paleta, nodos_visibles_ids)

        # --- 4. DIAGRAMAS DE ESFUERZOS ---
        if opciones.get('mostrar_diagramas', False) and self.modelo.resultados_calculo:
            # CORRECCIÓN: Pasamos nodos_visibles_ids
            self._compilar_diagramas(datos_compilados, labels, opciones, paleta, nodos_visibles_ids)

        # --- 5. CARGAS ---
        if opciones.get('cargas', True):
            self._compilar_cargas(datos_compilados, labels, opciones, nodos_visibles_ids, paleta)

        # --- 6. NODOS Y APOYOS ---
        if opciones.get('nodos', True) and self.modelo.nodos:
            for id_nodo, coords in self.modelo.nodos.items():
                if id_nodo not in nodos_visibles_ids: continue
                
                if id_nodo in self.modelo.apoyos:
                    self._compilar_apoyo_individual(datos_compilados['poligonos_verts'], datos_compilados['poligonos_colors'], coords, paleta)
                else: 
                    self._add_puntos(datos_compilados['puntos_verts'], datos_compilados['puntos_colors'], np.array(coords), paleta['nodo'])

                self._add_label(labels, f"N{id_nodo}", coords, paleta['nodo'], opcion_ids_nodos)

        # --- 7. ESTRUCTURA DEFORMADA ---
        if opciones.get('mostrar_deformada', False) and self.modelo.resultados_calculo:
            # CORRECCIÓN: Pasamos nodos_visibles_ids para filtrar
            self._compilar_deformada(datos_compilados, labels, opciones, paleta, nodos_visibles_ids)
            
        # --- ETIQUETAS DE VALORES DE DEFORMACIÓN (NUEVO) ---
        if opciones.get('mostrar_desplazamientos_nodales', False) and resultados:
            vector_despl = resultados.get('desplazamientos')
            if vector_despl is not None:
                color_texto_def = paleta['deformada_texto']
                escala_def = opciones.get('escala_deformada', 1.0)
                
                for id_nodo, coords in self.modelo.nodos.items():
                    if id_nodo not in nodos_visibles_ids: continue
                    
                    # Índices en el vector global
                    idx = (id_nodo - 1) * 6
                    if idx + 6 > len(vector_despl): continue
                    
                    # Extraer vectores (Desplazamiento u, Giro theta)
                    u_vec = vector_despl[idx : idx+3]      # [ux, uy, uz]
                    theta_vec = vector_despl[idx+3 : idx+6] # [rx, ry, rz]
                    
                    # Calcular magnitudes resultantes
                    mag_delta = np.linalg.norm(u_vec)
                    mag_theta = np.linalg.norm(theta_vec)
                    
                    # Filtro para no etiquetar nodos que no se mueven (ej. empotramientos perfectos)
                    if mag_delta > 1e-5 or mag_theta > 1e-5:
                        # Calculamos la posición visual final (Coordenada + Desplazamiento * Escala)
                        pos_visual = np.array(coords) + (u_vec * escala_def)
                        
                        # Formato: δ en mm, θ en radianes
                        texto_label = f"δ={mag_delta*1000:.2f}mm\nθ={mag_theta:.4f}rad"
                        
                        # Agregamos a la lista de etiquetas
                        labels.append({
                            'text': texto_label,
                            'position': pos_visual + np.array([0, 0, 0.1]), # Pequeño offset en Z para no tapar el nodo
                            'color': color_texto_def
                        })

        # --- 8. CONVERTIR A ARRAYS FINALES ---
        for tipo in ["puntos", "lineas", "poligonos", "diagram_fill", "diagram_line"]:
            verts_list = datos_compilados[f'{tipo}_verts']; colors_list = datos_compilados[f'{tipo}_colors']
            
            if verts_list:
                datos_compilados[f'{tipo}_verts'] = np.concatenate(verts_list).astype(np.float32).reshape(-1, 3) 
            else:
                 datos_compilados[f'{tipo}_verts'] = np.array([], dtype=np.float32).reshape(0, 3)

            if colors_list:
                 datos_compilados[f'{tipo}_colors'] = np.concatenate(colors_list).astype(np.float32).reshape(-1, 4) 
            else:
                 datos_compilados[f'{tipo}_colors'] = np.array([], dtype=np.float32).reshape(0, 4)
            
        datos_compilados['lineas_widths'] = datos_compilados.pop('lineas_widths_map')

        return datos_compilados, labels

    # --- FUNCIONES AUXILIARES DE COMPILACIÓN DETALLADA ---

    def _compilar_apoyo_individual(self, verts_list, colors_list, coords, paleta):
        """Compila los 6 quads para un cubo de apoyo usando el color de la paleta."""
        tam = 0.2; color = paleta['apoyo']; c = np.array(coords); d = tam / 2
        c_cubo = c 
        v = [
            c_cubo + [-d, -d, -d], c_cubo + [ d, -d, -d], c_cubo + [ d,  d, -d], c_cubo + [-d,  d, -d],
            c_cubo + [-d, -d,  d], c_cubo + [ d, -d,  d], c_cubo + [ d,  d,  d], c_cubo + [-d,  d,  d],
        ]
        caras = [
            [v[0], v[3], v[2], v[1]], [v[4], v[5], v[6], v[7]],
            [v[0], v[1], v[5], v[4]], [v[2], v[3], v[7], v[6]],
            [v[1], v[2], v[6], v[5]], [v[3], v[0], v[4], v[7]],
        ]
        for cara in caras:
            self._add_quad(verts_list, colors_list, cara[0], cara[1], cara[2], cara[3], color)

    def _compilar_flecha(self, lista_vertices, lista_colores, mapa_anchos, p_inicio, p_fin, color, tamano_punta=0.5):
        """Compila las 3 líneas de una flecha."""
        ancho_linea = 2.0
        p_inicio, p_fin = np.array(p_inicio), np.array(p_fin)
        self._agregar_linea(lista_vertices, lista_colores, mapa_anchos, p_inicio, p_fin, color, ancho_linea)
        
        vector_dir = p_fin - p_inicio
        if np.linalg.norm(vector_dir) < 1e-6: return 
        vector_dir = vector_dir / np.linalg.norm(vector_dir)
        
        if np.allclose(np.abs(vector_dir), [0, 0, 1]) or np.allclose(np.abs(vector_dir), [0, 1, 0]):
            v_perp = np.cross(vector_dir, [1, 0, 0])
        else:
            v_perp = np.cross(vector_dir, [0, 0, 1])
        
        if np.linalg.norm(v_perp) < 1e-6: v_perp = np.cross(vector_dir, [0, 1, 0])
        v_perp = v_perp / np.linalg.norm(v_perp) if np.linalg.norm(v_perp) > 1e-6 else v_perp
        
        p_base1 = p_fin - vector_dir * tamano_punta + v_perp * tamano_punta / 2
        p_base2 = p_fin - vector_dir * tamano_punta - v_perp * tamano_punta / 2
        
        self._agregar_linea(lista_vertices, lista_colores, mapa_anchos, p_fin, p_base1, color, ancho_linea)
        self._agregar_linea(lista_vertices, lista_colores, mapa_anchos, p_fin, p_base2, color, ancho_linea)

    def _compilar_flecha_momento(self, lista_vertices, lista_colores, mapa_anchos, p_nodo, vector_momento, color, escala=1.0, tamano_punta=0.3):
        """Compila flecha de doble punta (mismo sentido) para representar momentos."""
        if np.linalg.norm(vector_momento) < 1e-6: return
        vector_norm = vector_momento / np.linalg.norm(vector_momento)
        ancho_linea = 2.0
        
        # El vector inicia en el nodo y apunta hacia afuera en la dirección del momento
        p_inicio = p_nodo
        p_fin = p_nodo + vector_norm * escala
        
        # Línea principal (cuerpo de la flecha)
        self._agregar_linea(lista_vertices, lista_colores, mapa_anchos, p_inicio, p_fin, color, ancho_linea)

        # Calcular vector perpendicular para dibujar las aletas de las puntas
        if np.allclose(np.abs(vector_norm), [0, 0, 1]) or np.allclose(np.abs(vector_norm), [0, 1, 0]):
            v_perp = np.cross(vector_norm, [1, 0, 0])
        else:
            v_perp = np.cross(vector_norm, [0, 0, 1])
            
        if np.linalg.norm(v_perp) < 1e-6: 
            v_perp = np.cross(vector_norm, [0, 1, 0])
            
        v_perp = v_perp / np.linalg.norm(v_perp) if np.linalg.norm(v_perp) > 1e-6 else v_perp

        # --- PRIMERA PUNTA (en el extremo final) ---
        p_b1_1 = p_fin - vector_norm * tamano_punta + v_perp * tamano_punta / 2
        p_b2_1 = p_fin - vector_norm * tamano_punta - v_perp * tamano_punta / 2
        self._agregar_linea(lista_vertices, lista_colores, mapa_anchos, p_fin, p_b1_1, color, ancho_linea)
        self._agregar_linea(lista_vertices, lista_colores, mapa_anchos, p_fin, p_b2_1, color, ancho_linea)

        # --- SEGUNDA PUNTA (ligeramente retrasada) ---
        offset = tamano_punta * 0.6
        p_fin_2 = p_fin - vector_norm * offset
        p_b1_2 = p_fin_2 - vector_norm * tamano_punta + v_perp * tamano_punta / 2
        p_b2_2 = p_fin_2 - vector_norm * tamano_punta - v_perp * tamano_punta / 2
        self._agregar_linea(lista_vertices, lista_colores, mapa_anchos, p_fin_2, p_b1_2, color, ancho_linea)
        self._agregar_linea(lista_vertices, lista_colores, mapa_anchos, p_fin_2, p_b2_2, color, ancho_linea)

    def _compilar_diagramas(self, datos_compilados, labels, opciones, paleta, nodos_visibles=None):
        """Compila la geometría de los diagramas de esfuerzo (relleno y etiquetas)."""
        resultados_especificos = opciones.get('resultados_diagrama_especificos', None)
        tipo_efecto = opciones.get('efecto_diagrama', None)
        
        if not resultados_especificos or not tipo_efecto: 
            return
        
        if not self.generador_diagramas:
            try: 
                self.generador_diagramas = GeneradorDiagramas(self.modelo)
            except ValueError: 
                return
            
        # 1. Calcular escala global basada en el máximo absoluto de todos los elementos VISIBLES
        MAX_ABS = 1e-6
        elementos_validos = []
        
        for eid in self.modelo.elementos.keys():
            if self.generador_diagramas.get_longitud_elemento(eid) <= 0:
                continue
            
            if nodos_visibles is not None:
                ni, nj, _ = self.modelo.elementos[eid]
                if ni not in nodos_visibles or nj not in nodos_visibles:
                    continue
            
            elementos_validos.append(eid)

        if not elementos_validos: 
            return
            
        for id_elem in elementos_validos:
            _, y_data = self.generador_diagramas.get_diagrama(id_elem, resultados_especificos, tipo_efecto)
            if len(y_data) > 0 and np.any(y_data): 
                MAX_ABS = max(MAX_ABS, np.max(np.abs(y_data)))
        
        longitudes = [self.generador_diagramas.get_longitud_elemento(eid) for eid in elementos_validos]
        longitud_promedio = np.mean(longitudes) if longitudes else 1.0
        
        # Factor de escala visual
        escala = (longitud_promedio / MAX_ABS) * 0.2 if MAX_ABS > 1e-6 else 0
        
        # Colores desde la paleta
        color_relleno = paleta['diagrama_relleno']
        color_texto_diag = paleta['diagrama_texto']

        verts_fill = datos_compilados['diagram_fill_verts']
        colors_fill = datos_compilados['diagram_fill_colors']
        
        for id_elem in elementos_validos:
            p1 = np.array(self.modelo.nodos[self.modelo.elementos[id_elem][0]])
            p2 = np.array(self.modelo.nodos[self.modelo.elementos[id_elem][1]])
            
            vx, vy, vz = self._get_ejes_locales(p1, p2)
            
            # Obtener datos del diagrama
            x_coords, y_coords = self.generador_diagramas.get_diagrama(id_elem, resultados_especificos, tipo_efecto, n_puntos=21)
            
            if len(y_coords) == 0: continue

            # Determinar vector normal para el dibujo
            if tipo_efecto in ['Cortante (Py)', 'Momento (Mz)']: vector_normal = vy
            elif tipo_efecto in ['Cortante (Pz)', 'Momento (My)']: vector_normal = vz
            else: vector_normal = vy 
            
            if tipo_efecto in ['Momento (My)', 'Momento (Mz)']: vector_normal = -vector_normal

            # --- 1. Generar Geometría de Relleno (Quads) ---
            for i in range(len(x_coords) - 1):
                pb_i = p1 + vx * x_coords[i]
                pb_j = p1 + vx * x_coords[i+1]
                pv_i = pb_i + vector_normal * y_coords[i] * escala
                pv_j = pb_j + vector_normal * y_coords[i+1] * escala
                self._add_quad(verts_fill, colors_fill, pb_i, pv_i, pv_j, pb_j, color_relleno)
            
            # --- 2. Etiquetas de Valores (Inicio, Fin, Máx Positivo, Máx Negativo) ---
            
            # Offset para que el texto no pise el gráfico
            distancia_offset = 0.1
            
            def agregar_etiqueta(val, x_loc):
                pos_base = p1 + vx * x_loc
                dir_offset = vector_normal * (1 if val >= 0 else -1)
                pos_etiqueta = pos_base + vector_normal * val * escala + dir_offset * distancia_offset
                labels.append({'text': f"{val:.2f}", 'position': pos_etiqueta, 'color': color_texto_diag})

            # Etiqueta Inicio
            agregar_etiqueta(y_coords[0], x_coords[0])
            
            # Etiqueta Fin
            agregar_etiqueta(y_coords[-1], x_coords[-1])
            
            # Buscar Máximo Positivo (ignorando extremos para no duplicar)
            idx_max = np.argmax(y_coords)
            val_max = y_coords[idx_max]
            if val_max > 1e-6 and 0 < idx_max < len(y_coords) - 1:
                agregar_etiqueta(val_max, x_coords[idx_max])
                
            # Buscar Mínimo Negativo (ignorando extremos)
            idx_min = np.argmin(y_coords)
            val_min = y_coords[idx_min]
            if val_min < -1e-6 and 0 < idx_min < len(y_coords) - 1:
                agregar_etiqueta(val_min, x_coords[idx_min])

    def _interpolacion_hermite(self, L, u1, u2, v1, theta_z1, v2, theta_z2, w1, theta_y1, w2, theta_y2, num_segmentos=10):
        """
        Genera puntos interpolados para una viga 3D usando polinomios de Hermite (Cúbicos).
        Esto garantiza que la curva respete los giros en los extremos.
        Retorna: Lista de coordenadas locales [x, y, z] deformadas.
        """
        puntos_locales = []
        
        # Iteramos a lo largo de la viga (de 0 a L)
        for i in range(num_segmentos + 1):
            xi = i / num_segmentos # Coordenada normalizada (0.0 a 1.0)
            x_pos = xi * L
            
            # --- Funciones de Forma de Hermite ---
            # H1, H2: Relacionados al Nodo 1 (Desplazamiento, Giro)
            # H3, H4: Relacionados al Nodo 2 (Desplazamiento, Giro)
            h1 = 1 - 3*xi**2 + 2*xi**3
            h2 = L * (xi - 2*xi**2 + xi**3)
            h3 = 3*xi**2 - 2*xi**3
            h4 = L * (-xi**2 + xi**3)
            
            # 1. Deformación Axial 'u' (Interpolación Lineal)
            u_def = u1 * (1 - xi) + u2 * xi
            
            # 2. Deformación Transversal 'v' (Plano XY local, depende de giros Theta Z)
            # Convención estándar positiva antihoraria
            v_def = h1*v1 + h2*theta_z1 + h3*v2 + h4*theta_z2
            
            # 3. Deformación Transversal 'w' (Plano XZ local, depende de giros Theta Y)
            w_def = h1*w1 + h2*(-theta_y1) + h3*w2 + h4*(-theta_y2)
            
            # Coordenada final del punto deformado en el sistema local:
            # (Posición original x + deformación u, deformación v, deformación w)
            puntos_locales.append(np.array([x_pos + u_def, v_def, w_def]))
            
        return puntos_locales

    def _compilar_deformada(self, datos_compilados, labels, opciones, paleta, nodos_visibles=None):
        """Compila la estructura deformada con curvatura real (interpolación cúbica)."""
        # 1. Validaciones y Recursos
        resultados = opciones.get('resultados_diagrama_especificos')
        if not resultados: return
        
        vector_despl = resultados.get('desplazamientos') # Vector plano (N_nodos * 6)
        if vector_despl is None: return

        escala = opciones.get('escala_deformada', 1.0)
        color_linea = paleta['deformada_linea']
        
        # Punteros a las listas de geometría para escribir rápido
        verts_lineas = datos_compilados['lineas_verts']
        colors_lineas = datos_compilados['lineas_colors']
        widths_map = datos_compilados['lineas_widths_map']
        
        # --- DIBUJO DE ELEMENTOS CON CURVATURA ---
        for id_elem, (ni, nj, _) in self.modelo.elementos.items():
            if ni not in self.modelo.nodos or nj not in self.modelo.nodos: continue
            
            # --- FILTRO DE VISIBILIDAD (NUEVO) ---
            if nodos_visibles is not None:
                if ni not in nodos_visibles or nj not in nodos_visibles:
                    continue
            
            # Índices en el vector global de resultados (6 GDL por nodo)
            idx_i = (ni - 1) * 6
            idx_j = (nj - 1) * 6
            
            if idx_j + 6 > len(vector_despl): continue
            
            # 1. Extraer Resultados Globales y Escalar (Desplazamientos y GIROS)
            # D = [ux, uy, uz, rx, ry, rz]
            D_i_global = vector_despl[idx_i : idx_i + 6] * escala
            D_j_global = vector_despl[idx_j : idx_j + 6] * escala
            
            # 2. Geometría Original y Matriz de Transformación
            P1 = np.array(self.modelo.nodos[ni])
            P2 = np.array(self.modelo.nodos[nj])
            L = np.linalg.norm(P2 - P1)
            
            if L < 1e-9: continue
            
            # Obtenemos los ejes locales para construir la matriz de rotación R
            vx, vy, vz = self._get_ejes_locales(P1, P2)
            # Matriz R (3x3) donde las filas son los vectores unitarios locales
            R = np.vstack([vx, vy, vz]) 
            
            # 3. Transformar Resultados a Coordenadas LOCALES
            # Necesitamos separar traslación (u) y rotación (theta)
            # Local = R * Global
            
            # Nodo I
            u_global_i = D_i_global[0:3]     # [ux, uy, uz]
            theta_global_i = D_i_global[3:6] # [rx, ry, rz]
            u_local_i = R @ u_global_i       # Traslación local
            theta_local_i = R @ theta_global_i # Rotación local
            
            # Nodo J
            u_global_j = D_j_global[0:3]
            theta_global_j = D_j_global[3:6]
            u_local_j = R @ u_global_j
            theta_local_j = R @ theta_global_j
            
            # 4. Generar Curva (Interpolación)
            # Enviamos los datos locales limpios a la función matemática
            num_seg = 12
            puntos_locales_curva = self._interpolacion_hermite(
                L, 
                u_local_i[0], u_local_j[0],          # Axial
                u_local_i[1], theta_local_i[2],      # Flexión en plano local XY (usa Theta Z)
                u_local_j[1], theta_local_j[2], 
                u_local_i[2], theta_local_i[1],      # Flexión en plano local XZ (usa Theta Y)
                u_local_j[2], theta_local_j[1],
                num_segmentos=num_seg
            )
            
            # --- CÁLCULO DE LA FLECHA MÁXIMA ---
            max_flecha_mag = -1.0
            flecha_real_max = 0.0
            xi_max = 0.0
            pos_etiqueta_global = None
            
            # Coordenadas transversales de los extremos (para calcular la "cuerda" recta)
            v1, w1 = u_local_i[1], u_local_i[2]
            v2, w2 = u_local_j[1], u_local_j[2]
            
            # 5. Transformar Curva a Global y Dibujar
            punto_previo_global = None
            
            for idx, p_local in enumerate(puntos_locales_curva):
                # Transformación inversa: Local -> Global
                p_global_deformado = P1 + (R.T @ p_local)
                
                if punto_previo_global is not None:
                    self._agregar_linea(
                        verts_lineas, colors_lineas, widths_map, 
                        punto_previo_global, p_global_deformado, 
                        color_linea, ancho=2.0
                    )
                
                punto_previo_global = p_global_deformado
                
                # --- Análisis de Flecha Relativa ---
                xi = idx / num_seg
                
                # Posición teórica en la "cuerda" (línea recta entre los dos nodos deformados)
                v_chord = v1 * (1 - xi) + v2 * xi
                w_chord = w1 * (1 - xi) + w2 * xi
                
                # Desplazamientos locales actuales
                v_def = p_local[1]
                w_def = p_local[2]
                
                # Deflexión pura = (Curva deformada) - (Cuerda recta)
                flecha_y = v_def - v_chord
                flecha_z = w_def - w_chord
                flecha_mag = np.sqrt(flecha_y**2 + flecha_z**2)
                
                # Encontrar el máximo
                if flecha_mag > max_flecha_mag:
                    max_flecha_mag = flecha_mag
                    xi_max = xi
                    # Des-escalar para obtener el valor real (porque la matriz venía escalada visualmente)
                    flecha_real_max = flecha_mag / escala if escala > 0 else 0.0
                    pos_etiqueta_global = p_global_deformado

            # Añadir la etiqueta de la flecha máxima si el valor es mecánicamente relevante (ej. > 0.01 mm)
            if flecha_real_max > 1e-5 and opciones.get('mostrar_flecha_maxima', False):
                texto_flecha = f"{xi_max:.2f}L ; δmax={flecha_real_max*1000:.2f}mm"
                # Pequeño offset en Z global para que no pise la línea
                offset_visual = np.array([0, 0, 0.2])
                labels.append({
                    'text': texto_flecha,
                    'position': pos_etiqueta_global + offset_visual,
                    'color': QColor("red")
                })

    def _compilar_distribucion_losas(self, verts_list, colors_list, width_map, paleta, nodos_visibles=None):
        """Compila las líneas de distribución usando colores de la paleta, respetando visibilidad."""
        color_linea = paleta['distribucion_losas']
        color_relleno = paleta['distribucion_relleno']
        
        for id_losa, losa in self.modelo.losas.items():
            nodos_losa_ids = losa['nodos']
            
            if nodos_visibles is not None:
                if not all(nid in nodos_visibles for nid in nodos_losa_ids):
                    continue

            p_esquinas = [np.array(self.modelo.nodos[nid]) for nid in nodos_losa_ids]

            if losa['distribucion'] == 'unidireccional':
                eje_uni = losa.get('eje_uni', 'Global Y')
                p0, p1, p2, p3 = p_esquinas
                mid_01 = (p0 + p1) / 2.0; mid_23 = (p2 + p3) / 2.0
                mid_12 = (p1 + p2) / 2.0; mid_30 = (p3 + p0) / 2.0
                eje_paralelo_viga = np.array([1.0, 0.0, 0.0]) if 'Y' in eje_uni else np.array([0.0, 1.0, 0.0])
                v_div_opcion1 = mid_23 - mid_01; v_div_opcion2 = mid_12 - mid_30
                
                if abs(np.dot(v_div_opcion1, eje_paralelo_viga)) > abs(np.dot(v_div_opcion2, eje_paralelo_viga)):
                    punto_medio1, punto_medio2 = mid_01, mid_23; lado1, lado2 = mid_30, mid_12
                else: 
                    punto_medio1, punto_medio2 = mid_30, mid_12; lado1, lado2 = mid_01, mid_23
                
                self._agregar_linea(verts_list, colors_list, width_map, punto_medio1, punto_medio2, color_linea, 1.5)
                
                vector_division = punto_medio2 - punto_medio1; vector_perpendicular = lado2 - lado1; num_lineas_relleno = 10
                for i in range(1, num_lineas_relleno + 1):
                    fraccion = i / (num_lineas_relleno + 1); punto_en_division = punto_medio1 + (vector_division * fraccion)
                    punto_inicio_relleno = punto_en_division - (vector_perpendicular / 2.0)
                    punto_fin_relleno = punto_en_division + (vector_perpendicular / 2.0)
                    self._agregar_linea(verts_list, colors_list, width_map, punto_inicio_relleno, punto_fin_relleno, color_relleno, 1.0)
            
            elif losa['distribucion'] == 'bidireccional':
                geometria = _calcular_geometria_aporte_bidireccional(id_losa, losa, self.modelo)
                puntos_cresta = geometria.get('puntos_cresta')
                if not puntos_cresta: continue

                p_cresta1, p_cresta2 = puntos_cresta
                if not np.allclose(p_cresta1, p_cresta2):
                    self._agregar_linea(verts_list, colors_list, width_map, p_cresta1, p_cresta2, color_linea, 1.5)

                if geometria['es_cresta_horizontal'] is True:
                    p_h1, p_h2 = geometria['p_h1'], geometria['p_h2']
                    if p_h1 is not None and p_h2 is not None:
                        for idx_esquina, p_destino in [(0, p_h1), (1, p_h2), (2, p_h2), (3, p_h1)]:
                            self._agregar_linea(verts_list, colors_list, width_map, p_esquinas[idx_esquina], p_destino, color_linea, 1.5)
                elif geometria['es_cresta_horizontal'] is False:
                    p_v1, p_v2 = geometria['p_v1'], geometria['p_v2']
                    if p_v1 is not None and p_v2 is not None:
                        for idx_esquina, p_destino in [(0, p_v1), (1, p_v1), (2, p_v2), (3, p_v2)]:
                            self._agregar_linea(verts_list, colors_list, width_map, p_esquinas[idx_esquina], p_destino, color_linea, 1.5)
                else:               
                    for esquina in p_esquinas:
                        self._agregar_linea(verts_list, colors_list, width_map, esquina, puntos_cresta[0], color_linea, 1.5)

    def _compilar_cargas(self, datos_compilados, labels, opciones, nodos_visibles_ids, paleta):
        """Compila cargas usando paleta."""
        color_carga = paleta['carga']
        color_etiqueta = paleta['texto']
        color_carga_prisma = paleta['carga_losa_relleno']
        
        hipotesis_visible_id = opciones.get('hipotesis_visible_id', -1)
        prefijos_nodal = ["Fx", "Fy", "Fz", "Mx", "My", "Mz"]
        prefijos_dist = ["wx", "wy", "wz", "mt"]
        ALTURA_VISUAL_CARGA = 0.2
        OFFSET_ETIQUETA_CARGA = 0.1 
        escala_carga = 1.0

        def _formatear_vector_carga(vector, prefijos): 
            return ", ".join([f"{p}: {v:.2f}" for p, v in zip(prefijos, vector) if abs(v) > 1e-6])
        
        # Cargas Nodales
        for carga in self.modelo.cargas_nodales:
            if hipotesis_visible_id != -1 and carga.get('id_hipotesis') != hipotesis_visible_id: continue
            id_nodo = carga.get('id_nodo')
            if id_nodo not in nodos_visibles_ids: continue
            
            p_nodo = np.array(self.modelo.nodos[id_nodo])
            vector = carga.get('vector', [0]*6)
            fuerza = np.array(vector[:3]); momento = np.array(vector[3:])
            vector_norm_etiqueta = np.array([0.0, 0.0, -1.0])

            if np.linalg.norm(fuerza) > 1e-6:
                f_norm = fuerza / np.linalg.norm(fuerza)
                p_inicio = p_nodo - f_norm * escala_carga
                self._compilar_flecha(datos_compilados['lineas_verts'], datos_compilados['lineas_colors'], datos_compilados['lineas_widths_map'], p_inicio, p_nodo, color_carga)
                vector_norm_etiqueta = f_norm
            
            if np.linalg.norm(momento) > 1e-6:
                color_momento = QColor(255, 165, 0) 
                self._compilar_flecha_momento(datos_compilados['lineas_verts'], datos_compilados['lineas_colors'], datos_compilados['lineas_widths_map'], p_nodo, momento, color_momento, escala=escala_carga)
                if np.linalg.norm(fuerza) < 1e-6: vector_norm_etiqueta = momento / np.linalg.norm(momento)

            nombre_hipotesis = self.modelo.hipotesis_de_carga.get(carga.get('id_hipotesis'), {}).get('nombre', 'ID Desconocido')
            texto_carga = _formatear_vector_carga(vector, prefijos_nodal)
            if texto_carga:
                labels.append({'text': f"({nombre_hipotesis}) {texto_carga}", 'position': p_nodo + (vector_norm_etiqueta * 0.2), 'color': color_etiqueta})
        
        # Cargas Elemento
        for carga in self.modelo.cargas_elementos:
            if hipotesis_visible_id != -1 and carga.get('id_hipotesis') != hipotesis_visible_id: continue
            id_elem = carga.get('id_elemento')
            if id_elem not in self.modelo.elementos: continue
            ni, nj, _ = self.modelo.elementos[id_elem]
            if ni not in nodos_visibles_ids or nj not in nodos_visibles_ids: continue
            p1, p2 = np.array(self.modelo.nodos[ni]), np.array(self.modelo.nodos[nj])
            
            if carga.get('datos_carga', ('',))[0] == 'uniforme':
                _, wx, wy, wz, mt = carga['datos_carga']; vector_carga_global = np.array([wx, wy, wz]); vector_carga_normalizado = np.array([0.0, 0.0, -1.0]) 
                if np.linalg.norm(vector_carga_global) > 1e-6:
                    vector_carga_normalizado = vector_carga_global / np.linalg.norm(vector_carga_global); num_flechas = 5
                    for i in range(num_flechas + 1):
                        frac = i / num_flechas; p_fin_flecha = p1 + (p2 - p1) * frac; p_inicio_flecha = p_fin_flecha - vector_carga_normalizado * escala_carga
                        self._compilar_flecha(datos_compilados['lineas_verts'], datos_compilados['lineas_colors'], datos_compilados['lineas_widths_map'], p_inicio_flecha, p_fin_flecha, color_carga, tamano_punta=0.3)
                    
                    cola_inicio = p1 - vector_carga_normalizado * escala_carga; cola_fin = p2 - vector_carga_normalizado * escala_carga
                    self._agregar_linea(datos_compilados['lineas_verts'], datos_compilados['lineas_colors'], datos_compilados['lineas_widths_map'], cola_inicio, cola_fin, color_carga, 2.0)
                
                nombre_hipotesis = self.modelo.hipotesis_de_carga.get(carga.get('id_hipotesis'), {}).get('nombre', ''); vector_etiqueta = (wx, wy, wz, mt); texto_etiqueta = _formatear_vector_carga(vector_etiqueta, prefijos_dist)
                if texto_etiqueta: 
                    pos_etiqueta = (p1 + p2) / 2.0 - vector_carga_normalizado * (escala_carga + 0.2)
                    labels.append({'text': f"({nombre_hipotesis}) {texto_etiqueta}", 'position': pos_etiqueta, 'color': color_etiqueta})
        
        # Cargas Superficiales
        for id_carga_sup, carga_sup in self.modelo.cargas_superficiales.items():
            if hipotesis_visible_id != -1 and carga_sup.get('id_hipotesis') != hipotesis_visible_id: continue
            id_losa = carga_sup.get('id_losa')
            if id_losa not in self.modelo.losas: continue
            nodos_ids = self.modelo.losas[id_losa]['nodos']
            if not all(nid in nodos_visibles_ids for nid in nodos_ids): continue
                
            coords = np.array([self.modelo.nodos.get(nid) for nid in nodos_ids])
            if not np.any(coords == None):
                try:
                    coords_ordenadas = self._ordenar_nodos_placa(coords) 
                    normal = self._calcular_normal_placa(coords_ordenadas)
                    centro_base = np.mean(coords_ordenadas, axis=0)
                    coords_superiores = coords_ordenadas + (normal * ALTURA_VISUAL_CARGA)
                    
                    # Caras prisma carga
                    self._add_quad(datos_compilados['poligonos_verts'], datos_compilados['poligonos_colors'], 
                                   coords_superiores[0], coords_superiores[1], coords_superiores[2], coords_superiores[3], color_carga_prisma)
                    self._add_quad(datos_compilados['poligonos_verts'], datos_compilados['poligonos_colors'], 
                                   coords_ordenadas[0], coords_ordenadas[3], coords_ordenadas[2], coords_ordenadas[1], color_carga_prisma) 
                    for i in range(4):
                        cara_lateral = [coords_ordenadas[i], coords_ordenadas[(i + 1) % 4], coords_superiores[(i + 1) % 4], coords_superiores[i]]
                        self._add_quad(datos_compilados['poligonos_verts'], datos_compilados['poligonos_colors'], cara_lateral[0], cara_lateral[1], cara_lateral[2], cara_lateral[3], color_carga_prisma)

                    posicion_etiqueta = centro_base + normal * (ALTURA_VISUAL_CARGA + OFFSET_ETIQUETA_CARGA)
                    nombre_hipotesis = self.modelo.hipotesis_de_carga.get(carga_sup.get('id_hipotesis'), {}).get('nombre', '')
                    labels.append({'text': f"({nombre_hipotesis}) wz: {carga_sup['magnitud']:.2f} kN/m²", 'position': posicion_etiqueta, 'color': color_carga})
                except Exception: pass

    def actualizar(self, viewer, opciones):
        """
        Método orquestador: compila, sube a la GPU y pide el repintado.
        """
        viewer.clear_scene()
        viewer.reaction_labels = [] 
        
        # 1. Obtener la paleta basada en el modo del visor
        modo_actual = viewer.modo_tema
        paleta_actual = PALETAS_TEMA.get(modo_actual, PALETAS_TEMA["oscuro"])
        
        # 2. Compilar toda la geometría con la paleta seleccionada
        reaction_labels_temp = [] 
        compiled_data, labels = self._compilar_geometria(opciones, paleta_actual, reaction_labels_temp)
        
        # 3. Subir a GPU
        viewer.actualizar_buffers(compiled_data)
        
        # 4. Asignar etiquetas y repintar
        viewer.text_labels = labels
        viewer.reaction_labels = reaction_labels_temp 
        viewer.update()