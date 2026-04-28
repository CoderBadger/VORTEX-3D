# 🌪️ VORTEX 3D

**Plataforma de Código Abierto para el Análisis Estructural de Edificaciones 3D**

![Licencia](https://img.shields.io/badge/Licencia-GNU_GPL_v3-blue.svg)
![Python](https://img.shields.io/badge/Python-3.x-blue?logo=python)
![PySide6](https://img.shields.io/badge/GUI-PySide6-green?logo=qt)
![OpenGL](https://img.shields.io/badge/Render-OpenGL-red?logo=opengl)

VORTEX 3D es una herramienta computacional desarrollada en Python para el análisis y diseño de estructuras aporticadas en tres dimensiones, fundamentada en el **Método Matricial de Rigidez**. Su objetivo es brindar una plataforma transparente, auditable y de código abierto para la validación de cálculos estructurales y el aprendizaje académico.

---

## 🎓 Contexto Académico

Este repositorio contiene el código fuente y los resultados del proyecto de grado (tesis) titulado:
> **"DESARROLLO DE UNA HERRAMIENTA DE CÓDIGO ABIERTO PARA EL ANÁLISIS AUTOMATIZADO DE ESTRUCTURAS APORTICADAS EN 3D MEDIANTE EL MÉTODO MATRICIAL DE RIGIDEZ"**

**Autores e Investigadores Principales:**
* Diego Oliver Vargas Moya (Arquitectura de software, GUI y Motor de Análisis)
* Luis Alberto Ortiz Morales (Módulos de diseño normativo)

Animamos a futuros tesistas y estudiantes de ingeniería a utilizar este código base para realizar proyectos de grado similares, actualizando las características del programa según las recomendaciones de nuestro proyecto o según su propio criterio personal de investigación.

---

## ✨ Características Principales

* **Análisis Estático Lineal 3D:** Soporte para elementos tipo barra (vigas y columnas) y elementos de superficie (losas).
* **Renderizado de Alto Rendimiento:** Visualización 3D interactiva acelerada por hardware (OpenGL) para auditar la geometría, cargas, ejes locales y deformadas.
* **Importación DXF:** Lógica de tolerancia y fusión de nodos para importar geometría, apoyos y cargas directamente desde archivos de dibujo (AutoCAD/BricsCAD).
* **Gestión de Cargas:** Generación de combinaciones automáticas, procesamiento de cargas nodales, distribuidas lineales y presiones superficiales.
* **Resultados y Diseño:** Generación de reportes PDF detallados, diagramas de esfuerzos internos y verificación normativa.

---
## 📖 Manual de Usuario

Para facilitar la curva de aprendizaje y asegurar el uso correcto de todas las herramientas, se incluye un **Manual de Usuario en formato PDF**. Este documento detalla paso a paso el funcionamiento completo de la Versión 1.0 del programa, abarcando desde la creación de geometría y asignación de cargas, hasta la lectura de diagramas y reportes de cálculo.

---

## 🚀 Instalación y Uso

VORTEX 3D está pensado tanto para ingenieros que desean utilizar la herramienta directamente, como para desarrolladores que desean extender su código.

### Opción A: Para Usuarios (Uso Directo)
Si deseas utilizar la herramienta de forma gratuita, directa y sin los inconvenientes de configurar un entorno de programación:
1. Dirígete a la sección de **[Releases](../../releases)** a la derecha de este repositorio.
2. Descarga el archivo ejecutable `.exe` adjunto correspondiente a la **Versión 1.0**.
3. Ejecútalo en tu equipo con Windows y comienza a modelar.

### Opción B: Para Desarrolladores y Tesistas (Código Fuente)
Para los colegas que deseen auditar la matemática, mejorar el motor FEM o adaptar la interfaz:

1. Clona este repositorio
2. Crea un entorno virtual e instala las dependencias principales
3. Ejecuta el programa desde la carpeta de scripts
---

## 📂 Estructura del Repositorio

Todo el código fuente se encuentra encapsulado en la carpeta `Scripts/`. Aquí tienes un mapa rápido de los módulos principales para que te ubiques rápido:

* `app_window.py`: Coordina la Interfaz Gráfica de Usuario (GUI) y la comunicación Modelo-Vista-Controlador.
* `calc.py`: El corazón matemático. Contiene el solucionador 3D y el ensamblaje de la matriz de rigidez global.
* `visualizacion.py`: Motor de renderizado 3D OpenGL (gestión de VBOs/VAOs, shaders, cámara y dibujo de diagramas).
* `modelo_estructura.py`: Gestión de la base de datos en memoria (nodos, elementos, materiales, apoyos).
* `importar_dxf.py`: Lógica de lectura de capas y discretización de geometría CAD.

---

## 🛣️ Hoja de Ruta (Roadmap para futuros tesistas)

Si estás buscando un tema de tesis, aquí hay algunas áreas en las que VORTEX 3D puede expandirse enormemente:

* **[ ] Análisis Dinámico y Sísmico:** Implementación de análisis modal espectral y cálculo de masas participativas.
* **[ ] Elementos Finitos Avanzados:** Transición de elementos Shell básicos a formulaciones de orden superior (ej. MITC4) para modelar muros de corte con alta precisión.
* **[ ] Diseño en Acero y Madera:** Expansión de los módulos normativos más allá del hormigón armado.
* **[ ] Integración BIM:** Soporte para importación y exportación en formato IFC.

---

## 🤝 Cómo Contribuir (Flujo de Trabajo)

¡Las contribuciones de estudiantes, ingenieros y desarrolladores son totalmente bienvenidas! Para mantener la estabilidad del programa y asegurar que la matemática sea correcta, nuestra rama `main` está protegida. Nadie puede subir código directamente a ella. 

Si deseas aportar al proyecto (ya sea resolviendo un bug o añadiendo algo de la hoja de ruta), sigue estos pasos:

1. **Haz un "Fork"** de este repositorio hacia tu propia cuenta de GitHub (botón arriba a la derecha).
2. **Clona** tu Fork en tu computadora y crea una nueva rama para trabajar en tu función: git checkout -b nombre-de-tu-nueva-funcion
3. **Programa, haz commit y sube (push)** los cambios a la rama de tu propio repositorio.
4. **Abre un Pull Request (PR):** Entra a la página original de VORTEX 3D en GitHub y abre un Pull Request solicitando fusionar tu nueva rama con nuestra rama `main`.
5. **Revisión de Código:** Todos los cambios pasan por una revisión humana. Es posible que te dejemos comentarios, sugerencias o dudas sobre el código. **Nota importante:** El sistema bloqueará la fusión hasta que se apruebe el PR y **todas las conversaciones y comentarios estén marcados como resueltos**.

Una vez que todo esté en orden, ¡nosotros mismos haremos el Merge y tu código formará parte oficial de VORTEX 3D!

---

## ⚖️ Licencia y Aviso Legal

Este proyecto está bajo la Licencia Pública General GNU (**GNU GPL v3**). Eres libre de usar, modificar y distribuir este software, siempre y cuando cualquier trabajo derivado también sea de código abierto bajo los mismos términos. Para más detalles, revisa el archivo `LICENSE`.

**Aviso Legal:** VORTEX 3D es una herramienta de validación académica y de aprendizaje. Todo resultado derivado de este software debe ser rigurosamente verificado por un ingeniero profesional debidamente facultado antes de su aplicación en la vida real. Los autores no asumen ninguna responsabilidad por daños o perjuicios derivados del uso de este programa.
