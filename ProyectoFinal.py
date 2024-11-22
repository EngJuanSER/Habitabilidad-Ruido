import sys
import math
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QLabel, QVBoxLayout, QPushButton, QWidget,
    QComboBox, QScrollArea, QMessageBox, QHBoxLayout, QDesktopWidget
)
from PyQt5.QtCore import Qt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt
import networkx as nx
from matplotlib.lines import Line2D  # Añadido para solucionar el error NameError

class Nodo:
    def __init__(self, name, tipo, pared, ventana, puerta, ruido, frecuencia, position, piso, es_fuente=False):
        self.name = name
        self.tipo = tipo
        self.pared = pared
        self.ventana = ventana
        self.puerta = puerta
        self.ruido = ruido
        self.frecuencia = frecuencia
        self.sensores = []
        self.conexiones = []
        self.position = position  # (x, y, z)
        self.piso = piso
        self.es_fuente = es_fuente

    def agregar_sensor(self, sensor):
        self.sensores.append(sensor)

    def conectar(self, nodo):
        if nodo not in self.conexiones:
            self.conexiones.append(nodo)
            nodo.conectar_bidireccional(self)

    def conectar_bidireccional(self, nodo):
        if nodo not in self.conexiones:
            self.conexiones.append(nodo)

    def medir_ruido(self):
        ruido_propio = self.ruido if self.es_fuente else 0
        ruido_propagado = 0
        for nodo in self.conexiones:
            distancia = self.calcular_distancia(nodo)
            if distancia == 0:
                continue
            atenuacion = math.log(distancia + 1)  # Atenuación logarítmica
            if self.piso != nodo.piso:
                atenuacion *= 1.5  # Mayor atenuación entre pisos
            ruido_propagado += nodo.ruido / atenuacion
        absorcion = 0.8 if self.pared else 1.0
        ruido_total = ruido_propio + (ruido_propagado * absorcion)
        return ruido_total

    def calcular_distancia(self, otro_nodo):
        x1, y1, z1 = self.position
        x2, y2, z2 = otro_nodo.position
        return math.sqrt((x2 - x1)**2 + (y2 - y1)**2 + (z2 - z1)**2)

    def get_limite_ruido(self):
        limites = {
            "aula": {"limite_adecuado": 55, "limite_cercano": 60, "limite_excedido": 65},
            "pasillo": {"limite_adecuado": 45, "limite_cercano": 50, "limite_excedido": 55},
            "biblioteca": {"limite_adecuado": 35, "limite_cercano": 40, "limite_excedido": 45},
            "auditorio": {"limite_adecuado": 60, "limite_cercano": 65, "limite_excedido": 70},
            "cafetería": {"limite_adecuado": 60, "limite_cercano": 65, "limite_excedido": 70},
            "laboratorio": {"limite_adecuado": 50, "limite_cercano": 55, "limite_excedido": 60},
            "oficina": {"limite_adecuado": 50, "limite_cercano": 55, "limite_excedido": 60},
            "reuniones": {"limite_adecuado": 50, "limite_cercano": 55, "limite_excedido": 60},
        }
        return limites.get(self.tipo, {"limite_adecuado": 50, "limite_cercano": 55, "limite_excedido": 60})

class Sensor:
    def __init__(self, ubicacion, ruido_fijo=None):
        self.ubicacion = ubicacion
        self.ruido_fijo = ruido_fijo

    def medir(self):
        return self.ruido_fijo if self.ruido_fijo is not None else 0

class ReporteWindow(QWidget):
    def __init__(self, datos_reporte):
        super().__init__()
        self.setWindowTitle("Reporte de Ruido")
        self.setGeometry(150, 150, 400, 500)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        contenido = QWidget()
        layout = QVBoxLayout()

        for name, nivel, estado, recomendacion in datos_reporte:
            if estado == "Excede":
                simbolo = "❌"
                color = "red"
            elif estado == "Cerca":
                simbolo = "⚠️"
                color = "orange"
            else:
                simbolo = "✅"
                color = "green"
            texto = f"{simbolo} {name}: {nivel:.2f} dB - {recomendacion}"
            label = QLabel(texto)
            label.setWordWrap(True)
            label.setStyleSheet(f"color: {color};")
            layout.addWidget(label)

        contenido.setLayout(layout)
        scroll.setWidget(contenido)

        main_layout = QVBoxLayout()
        main_layout.addWidget(scroll)
        self.setLayout(main_layout)

class Grafo3DWindow(QWidget):
    def __init__(self, habitaciones, posiciones_fijas):
        super().__init__()
        self.setWindowTitle("Grafo 3D")
        self.setGeometry(150, 150, 800, 600)
        layout = QVBoxLayout()

        fig = plt.figure()
        ax = fig.add_subplot(111, projection='3d')

        G = nx.Graph()
        for name, nodo in habitaciones.items():
            G.add_node(name, tipo=nodo.tipo, ruido=nodo.medir_ruido())

        # Conectar todos los nodos dentro del mismo piso
        pisos = {}
        for name, nodo in habitaciones.items():
            pisos.setdefault(nodo.piso, []).append(nodo)

        for piso, nodos in pisos.items():
            for i in range(len(nodos)):
                for j in range(i + 1, len(nodos)):
                    G.add_edge(nodos[i].name, nodos[j].name)

        # Conectar entre pisos adyacentes
        for piso, nodos in pisos.items():
            if piso < max(pisos.keys()):
                pisos_siguiente = pisos.get(piso + 1, [])
                for nodo in nodos:
                    for otro_nodo in pisos_siguiente:
                        distancia_total = nodo.calcular_distancia(otro_nodo)
                        if distancia_total <= 7:  # Umbral ajustado
                            G.add_edge(nodo.name, otro_nodo.name)

        pos = posiciones_fijas  # Usar posiciones fijas
        nx.set_node_attributes(G, pos, 'pos')

        # Dibujar nodos
        for name, nodo in habitaciones.items():
            niveles = nodo.get_limite_ruido()
            nivel_ruido = nodo.medir_ruido()
            if nivel_ruido > niveles['limite_excedido']:
                color = 'red'
            elif nivel_ruido > niveles['limite_cercano']:
                color = 'yellow'
            else:
                color = 'green'
            p = pos[name]
            ax.scatter(p[0], p[1], p[2], color=color, s=100)
            ax.text(p[0], p[1], p[2], name, fontsize=9)

        # Dibujar aristas con atenuación logarítmica
        for edge in G.edges():
            if edge[0] in pos and edge[1] in pos:
                p1 = pos[edge[0]]
                p2 = pos[edge[1]]
                distancia = math.sqrt(
                    (p2[0] - p1[0])**2 +
                    (p2[1] - p1[1])**2 +
                    (p2[2] - p1[2])**2
                )
                atenuacion = math.log(distancia + 1)  # Evitar log(0)
                ax.plot(
                    [p1[0], p2[0]],
                    [p1[1], p2[1]],
                    [p1[2], p2[2]],
                    color='gray',
                    linestyle='--',
                    linewidth=0.5 / atenuacion  # Atenuar según distancia
                )

        # Configurar límites de los ejes basados en el primer piso
        limite_piso1 = self.obtener_limites_piso1(habitaciones)
        ax.set_xlim([-limite_piso1['x'], limite_piso1['x']])
        ax.set_ylim([-limite_piso1['y'], limite_piso1['y']])
        ax.set_zlim([0, max(piso for piso in pisos.keys()) * 3 + 3])  # Ajustar según pisos

        # Añadir leyenda
        legend_elements = [
            Line2D([0], [0], marker='o', color='w', label='Adecuado', markerfacecolor='green', markersize=10),
            Line2D([0], [0], marker='o', color='w', label='Cerca del límite', markerfacecolor='yellow', markersize=10),
            Line2D([0], [0], marker='o', color='w', label='Excede límite', markerfacecolor='red', markersize=10)
        ]
        ax.legend(handles=legend_elements, loc='upper right')

        self.canvas = FigureCanvas(fig)
        layout.addWidget(self.canvas)
        self.setLayout(layout)
        self.canvas.draw()

    def obtener_limites_piso1(self, habitaciones):
        nodos_piso1 = [nodo for nodo in habitaciones.values() if nodo.piso == 1]
        max_x = max(abs(nodo.position[0]) for nodo in nodos_piso1)
        max_y = max(abs(nodo.position[1]) for nodo in nodos_piso1)
        return {'x': max_x + 2, 'y': max_y + 2}  # Margen adicional

class ArreglarNodoWindow(QWidget):
    def __init__(self, habitaciones, actualizar_func):
        super().__init__()
        self.setWindowTitle("Arreglar Nodo")
        self.setGeometry(300, 300, 300, 200)  # Tamaño reducido
        self.habitaciones = habitaciones
        self.actualizar_func = actualizar_func

        layout = QVBoxLayout()

        self.combo = QComboBox()
        for name, nodo in habitaciones.items():
            limites = nodo.get_limite_ruido()
            nivel = nodo.medir_ruido()
            if nivel > limites['limite_excedido']:
                self.combo.addItem(name)
        layout.addWidget(QLabel("Seleccionar nodo a arreglar:"))
        layout.addWidget(self.combo)

        self.btn_arreglar = QPushButton("Arreglar")
        self.btn_arreglar.clicked.connect(self.arreglar)
        layout.addWidget(self.btn_arreglar, alignment=Qt.AlignCenter)

        self.setLayout(layout)

    def arreglar(self):
        name = self.combo.currentText()
        if name:
            nodo = self.habitaciones[name]
            limites = nodo.get_limite_ruido()
            nodo.ruido = limites['limite_adecuado']  # Reducir el ruido al límite adecuado
            self.actualizar_func()
            QMessageBox.information(self, "Arreglar Nodo", f"Nodo '{name}' arreglado al límite adecuado.")
            self.close()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Simulación de Ruido")
        self.setGeometry(100, 100, 600, 400)  # Tamaño reducido
        self.centrar_ventana()
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        self.habitaciones = {}
        self.datos_ruido = []
        self.reporte_generado = False
        self.posiciones_fijas = {}

        self.inicializar_nodos()
        self.conectar_nodos()
        self.aplicar_reduccion_grafo()

        # Crear botones
        layout_principal = QVBoxLayout()
        layout_principal.setSpacing(10)  # Espaciado reducido
        layout_principal.setContentsMargins(20, 20, 20, 20)  # Márgenes ajustados

        bot_textos = ["Generar Reporte", "Mostrar Grafo 3D", "Arreglar Nodo", "Salir"]
        botones = []
        ancho_boton = self.obtener_ancho_boton(bot_textos)

        # Layout para centrar los botones
        layout_botones = QVBoxLayout()
        layout_botones.setSpacing(10)

        for texto in bot_textos:
            btn = QPushButton(texto)
            btn.setFixedWidth(ancho_boton)
            botones.append(btn)
            layout_botones.addWidget(btn, alignment=Qt.AlignCenter)

        layout_principal.addLayout(layout_botones)
        layout_principal.addStretch()

        # Conectar botones
        botones[0].clicked.connect(self.mostrar_reporte)
        botones[1].clicked.connect(self.mostrar_grafo)
        botones[2].clicked.connect(self.arreglar_nodo)
        botones[3].clicked.connect(self.close)

        self.central_widget.setLayout(layout_principal)

    def centrar_ventana(self):
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def obtener_ancho_boton(self, textos):
        fuente = self.font()
        fm = self.fontMetrics()
        max_ancho = max([fm.width(texto) for texto in textos]) + 40
        return max_ancho

    def inicializar_nodos(self):
        # Definir posiciones fijas para asegurar layout consistente
        # Ampliar el edificio con más pisos y espacios
        # Formato: (x, y, z)
        self.habitaciones = {
            # Piso 1
            "Recepción": Nodo("Recepción", "oficina", True, True, True, 50, 1, (0, 0, 0), piso=1, es_fuente=True),
            "Oficina 1": Nodo("Oficina 1", "oficina", True, True, True, 55, 1, (-4, 2, 0), piso=1),
            "Oficina 2": Nodo("Oficina 2", "oficina", True, True, True, 60, 1, (-4, -2, 0), piso=1),
            "Pasillo 1": Nodo("Pasillo 1", "pasillo", False, False, False, 40, 1, (-2, 0, 0), piso=1),
            "Sala de Reuniones 1": Nodo("Sala de Reuniones 1", "reuniones", True, True, True, 52, 1, (2, 2, 0), piso=1),
            "Sala de Reuniones 2": Nodo("Sala de Reuniones 2", "reuniones", True, True, True, 48, 1, (2, -2, 0), piso=1),
            "Aula 1": Nodo("Aula 1", "aula", True, True, True, 58, 1, (4, 2, 0), piso=1),
            "Aula 2": Nodo("Aula 2", "aula", True, True, True, 62, 1, (4, -2, 0), piso=1),
            # Piso 2
            "Laboratorio 1": Nodo("Laboratorio 1", "laboratorio", True, True, True, 45, 1, (-4, 2, 3), piso=2),
            "Laboratorio 2": Nodo("Laboratorio 2", "laboratorio", True, True, True, 48, 1, (-4, -2, 3), piso=2),
            "Oficina 3": Nodo("Oficina 3", "oficina", True, True, True, 50, 1, (-2, 2, 3), piso=2),
            "Pasillo 2": Nodo("Pasillo 2", "pasillo", False, False, False, 42, 1, (-2, 0, 3), piso=2),
            "Biblioteca": Nodo("Biblioteca", "biblioteca", True, True, True, 35, 1, (2, 2, 3), piso=2),
            "Aula 3": Nodo("Aula 3", "aula", True, True, True, 57, 1, (4, 2, 3), piso=2),
            "Aula 4": Nodo("Aula 4", "aula", True, True, True, 61, 1, (4, -2, 3), piso=2),
            # Piso 3
            "Auditorio": Nodo("Auditorio", "auditorio", True, True, True, 70, 1, (-4, 2, 6), piso=3, es_fuente=True),
            "Cafetería": Nodo("Cafetería", "cafetería", True, True, True, 65, 1, (-4, -2, 6), piso=3),
            "Oficina 4": Nodo("Oficina 4", "oficina", True, True, True, 55, 1, (-2, 2, 6), piso=3),
            "Pasillo 3": Nodo("Pasillo 3", "pasillo", False, False, False, 43, 1, (-2, 0, 6), piso=3),
            "Laboratorio 3": Nodo("Laboratorio 3", "laboratorio", True, True, True, 50, 1, (2, 2, 6), piso=3),
            "Oficina 5": Nodo("Oficina 5", "oficina", True, True, True, 53, 1, (2, -2, 6), piso=3),
            "Sala de Reuniones 3": Nodo("Sala de Reuniones 3", "reuniones", True, True, True, 49, 1, (0, 0, 6), piso=3),
            "Aula 5": Nodo("Aula 5", "aula", True, True, True, 59, 1, (4, 2, 6), piso=3),
            "Aula 6": Nodo("Aula 6", "aula", True, True, True, 63, 1, (4, -2, 6), piso=3),
            # Piso 4
            "Biblioteca 2": Nodo("Biblioteca 2", "biblioteca", True, True, True, 34, 1, (-4, 2, 9), piso=4),
            "Oficina 6": Nodo("Oficina 6", "oficina", True, True, True, 54, 1, (-2, 2, 9), piso=4),
            "Pasillo 4": Nodo("Pasillo 4", "pasillo", False, False, False, 44, 1, (-2, 0, 9), piso=4),
            "Aula 7": Nodo("Aula 7", "aula", True, True, True, 60, 1, (4, 2, 9), piso=4),
            "Aula 8": Nodo("Aula 8", "aula", True, True, True, 64, 1, (4, -2, 9), piso=4),
        }

        # Agregar sensores a los nodos
        for habitacion in self.habitaciones.values():
            habitacion.agregar_sensor(Sensor(habitacion.name, ruido_fijo=habitacion.ruido))

        # Definir posiciones fijas
        self.posiciones_fijas = {name: nodo.position for name, nodo in self.habitaciones.items()}

    def conectar_nodos(self):
        # Conexiones Piso 1
        self.habitaciones["Recepción"].conectar(self.habitaciones["Pasillo 1"])
        self.habitaciones["Oficina 1"].conectar(self.habitaciones["Pasillo 1"])
        self.habitaciones["Oficina 2"].conectar(self.habitaciones["Pasillo 1"])
        self.habitaciones["Pasillo 1"].conectar(self.habitaciones["Sala de Reuniones 1"])
        self.habitaciones["Pasillo 1"].conectar(self.habitaciones["Sala de Reuniones 2"])
        self.habitaciones["Pasillo 1"].conectar(self.habitaciones["Aula 1"])
        self.habitaciones["Pasillo 1"].conectar(self.habitaciones["Aula 2"])

        # Conexiones entre Piso 1 y Piso 2
        self.habitaciones["Pasillo 1"].conectar(self.habitaciones["Pasillo 2"])

        # Conexiones Piso 2
        self.habitaciones["Pasillo 2"].conectar(self.habitaciones["Laboratorio 1"])
        self.habitaciones["Pasillo 2"].conectar(self.habitaciones["Laboratorio 2"])
        self.habitaciones["Pasillo 2"].conectar(self.habitaciones["Oficina 3"])
        self.habitaciones["Pasillo 2"].conectar(self.habitaciones["Biblioteca"])
        self.habitaciones["Pasillo 2"].conectar(self.habitaciones["Aula 3"])
        self.habitaciones["Pasillo 2"].conectar(self.habitaciones["Aula 4"])

        # Conexiones entre Piso 2 y Piso 3
        self.habitaciones["Pasillo 2"].conectar(self.habitaciones["Pasillo 3"])

        # Conexiones Piso 3
        self.habitaciones["Pasillo 3"].conectar(self.habitaciones["Auditorio"])
        self.habitaciones["Pasillo 3"].conectar(self.habitaciones["Cafetería"])
        self.habitaciones["Pasillo 3"].conectar(self.habitaciones["Oficina 4"])
        self.habitaciones["Pasillo 3"].conectar(self.habitaciones["Laboratorio 3"])
        self.habitaciones["Pasillo 3"].conectar(self.habitaciones["Oficina 5"])
        self.habitaciones["Pasillo 3"].conectar(self.habitaciones["Sala de Reuniones 3"])
        self.habitaciones["Pasillo 3"].conectar(self.habitaciones["Aula 5"])
        self.habitaciones["Pasillo 3"].conectar(self.habitaciones["Aula 6"])

        # Conexiones entre Piso 3 y Piso 4
        self.habitaciones["Pasillo 3"].conectar(self.habitaciones["Pasillo 4"])

        # Conexiones Piso 4
        self.habitaciones["Pasillo 4"].conectar(self.habitaciones["Biblioteca 2"])
        self.habitaciones["Pasillo 4"].conectar(self.habitaciones["Oficina 6"])
        self.habitaciones["Pasillo 4"].conectar(self.habitaciones["Aula 7"])
        self.habitaciones["Pasillo 4"].conectar(self.habitaciones["Aula 8"])

    def aplicar_reduccion_grafo(self):
        # Implementar reducción del grafo directamente en el código base
        nodos_fusionables = []
        nombres = list(self.habitaciones.keys())
        for i in range(len(nombres)):
            for j in range(i + 1, len(nombres)):
                nodo1 = self.habitaciones[nombres[i]]
                nodo2 = self.habitaciones[nombres[j]]
                if nodo1.tipo == nodo2.tipo and abs(nodo1.ruido - nodo2.ruido) <= 5:
                    distancia = nodo1.calcular_distancia(nodo2)
                    if distancia <= 2.0 and nodo1.piso == nodo2.piso:
                        nodos_fusionables.append((nodo1, nodo2))

        for nodo1, nodo2 in nodos_fusionables:
            for conexion in nodo2.conexiones.copy():
                if conexion != nodo1:
                    nodo1.conectar(conexion)
            nodo1.ruido = (nodo1.ruido + nodo2.ruido) / 2
            # Eliminar conexiones bidireccionales
            for conexion in nodo2.conexiones:
                conexion.conexiones.remove(nodo2)
            del self.habitaciones[nodo2.name]
            del self.posiciones_fijas[nodo2.name]

    def recibir_datos(self):
        self.datos_ruido = []
        for name, habitacion in self.habitaciones.items():
            nivel_ruido = habitacion.medir_ruido()
            self.datos_ruido.append((name, nivel_ruido))

    def analizar_datos(self):
        if not self.datos_ruido:
            self.promedio_ruido = 0
            self.max_ruido = 0
        else:
            self.promedio_ruido = sum(nivel for _, nivel in self.datos_ruido) / len(self.datos_ruido)
            self.max_ruido = max(nivel for _, nivel in self.datos_ruido)

    def comparar_estandares(self):
        self.reporte = []
        for name, nivel in self.datos_ruido:
            espacio = self.habitaciones[name]
            limites = espacio.get_limite_ruido()
            if nivel > limites['limite_excedido']:
                recomendacion = (
                    "Implementar soluciones acústicas: Instalación de paneles acústicos en paredes y techos, "
                    "aislamiento de fuentes de ruido externas o internas, rediseño de la distribución de actividades, "
                    "y mejora del aislamiento en puertas y ventanas."
                )
                estado = "Excede"
            elif nivel > limites['limite_cercano']:
                recomendacion = (
                    "Revisar medidas de mitigación: Considerar instalación de paneles acústicos o rediseño de actividades "
                    "para reducir niveles de ruido."
                )
                estado = "Cerca"
            else:
                recomendacion = "El nivel de ruido es adecuado."
                estado = "Adecuado"
            self.reporte.append((name, nivel, estado, recomendacion))

    def generar_reporte(self):
        pass  # Ya se ha generado en comparar_estandares

    def mostrar_reporte(self):
        self.recibir_datos()
        self.analizar_datos()
        self.comparar_estandares()
        self.generar_reporte()
        self.reporte_generado = True
        self.reporte_window = ReporteWindow(self.reporte)
        self.reporte_window.show()

    def mostrar_grafo(self):
        self.grafo_window = Grafo3DWindow(self.habitaciones, self.posiciones_fijas)
        self.grafo_window.show()

    def arreglar_nodo(self):
        self.arreglar_window = ArreglarNodoWindow(self.habitaciones, self.actualizar_datos)
        self.arreglar_window.show()

    def actualizar_datos(self):
        self.recibir_datos()
        self.analizar_datos()
        self.comparar_estandares()
        self.generar_reporte()
        self.reporte_generado = False

        # Actualizar el grafo si está abierto
        try:
            if hasattr(self, 'grafo_window') and self.grafo_window.isVisible():
                self.grafo_window.close()
                self.mostrar_grafo()
        except AttributeError:
            pass

        # Actualizar el reporte si está abierto
        try:
            if hasattr(self, 'reporte_window') and self.reporte_window.isVisible():
                self.reporte_window.close()
                self.mostrar_reporte()
        except AttributeError:
            pass

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())