import sys
import math
import random as rd
import numpy as np
from matplotlib.figure import Figure
from mpl_toolkits.mplot3d import Axes3D
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QPushButton, QWidget, QScrollArea,
    QTextEdit, QLabel, QDialog
)
import networkx as nx


# Clase Nodo
class Nodo:
    def __init__(self, name, pared, ventana, puerta, ruido, frecuencia):
        self.name = name
        self.pared = pared
        self.ventana = ventana
        self.puerta = puerta
        self.ruido = ruido
        self.frecuencia = frecuencia

    def position(self):
        piso = int(self.name[1])
        local = int(self.name[3:])
        return piso, local, 0

    def calcular_transmision_ruido(self, vecino):
        atenuacion_pared = 10 ** (-self.pared / 10)
        atenuacion_ventana = 10 ** (-self.ventana / 10)
        atenuacion_puerta = 10 ** (-self.puerta / 10)

        distancia = math.sqrt(sum([(a - b) ** 2 for a, b in zip(self.position(), vecino.position())]))
        atenuacion_distancia = 10 ** (-distancia / 20)

        transmision_total = atenuacion_pared * atenuacion_ventana * atenuacion_puerta * atenuacion_distancia
        return -10 * math.log10(transmision_total + 1e-9)

    def calcular_nivel_ruido(self, vecinos):
        niveles = [self.ruido]
        for vecino in vecinos:
            niveles.append(self.calcular_transmision_ruido(vecino) + vecino.ruido)
        return 10 * math.log10(sum(10 ** (nivel / 10) for nivel in niveles))

    def calcular_color(self, vecinos):
        nivel_ruido = self.calcular_nivel_ruido(vecinos)
        if nivel_ruido > 80:
            return 'red'
        elif nivel_ruido > 60:
            return 'orange'
        elif nivel_ruido > 40:
            return 'yellow'
        else:
            return 'green'


# Clase para la ventana de resultados
class ResultsWindow(QDialog):
    def __init__(self, habitaciones, grafo):
        super().__init__()
        self.setWindowTitle("Resultados Detallados")
        self.resize(800, 600)

        # Crear área scrolleable
        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        layout = QVBoxLayout(self)
        self.setLayout(layout)

        text_widget = QTextEdit()
        text_widget.setReadOnly(True)
        scroll_area.setWidget(text_widget)
        layout.addWidget(scroll_area)

        # Generar resultados
        result = ""
        for name, habitacion in habitaciones.items():
            vecinos = [habitaciones[vecino] for vecino in grafo.neighbors(name)]
            ruido_actual = habitacion.calcular_nivel_ruido(vecinos)
            result += f"🔵 Nodo {name}:\n"
            result += f"  - Resistencia de Pared: {habitacion.pared}\n"
            result += f"  - Resistencia de Ventana: {habitacion.ventana}\n"
            result += f"  - Resistencia de Puerta: {habitacion.puerta}\n"
            result += f"  - Nivel de Ruido: {ruido_actual:.2f} dB\n\n"

            # Recomendaciones
            if ruido_actual <= 60:
                result += "✅ **Recomendación:** El nivel de ruido es adecuado. No se requieren acciones inmediatas.\n\n"
            elif 60 < ruido_actual <= 80:
                result += "⚠️ **Recomendación:** Nivel moderado. Considere paneles acústicos o ventanas de doble acristalamiento.\n\n"
            else:
                result += "❌ **Recomendación:** Nivel alto. Aísle puertas y ventanas, use materiales insonorizantes.\n\n"

        text_widget.setText(result)


# Clase para manejar la ventana principal y los gráficos
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Análisis de Niveles de Ruido")
        self.resize(800, 600)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        self.layout = QVBoxLayout()
        self.central_widget.setLayout(self.layout)

        # Botones
        self.button_results = QPushButton("Mostrar Resultados")
        self.button_results.clicked.connect(self.show_results)
        self.layout.addWidget(self.button_results)

        self.button_graph = QPushButton("Mostrar Gráfico")
        self.button_graph.clicked.connect(self.show_graph)
        self.layout.addWidget(self.button_graph)

        self.button_fix_node = QPushButton("Arreglar Nodo Específico")
        self.button_fix_node.clicked.connect(self.fix_specific_node)
        self.layout.addWidget(self.button_fix_node)

        self.button_exit = QPushButton("Salir")
        self.button_exit.clicked.connect(self.close)
        self.layout.addWidget(self.button_exit)

        # Crear el grafo y las habitaciones
        self.G = nx.Graph()
        self.create_test_case()

    def create_test_case(self):
        self.habitaciones = {}
        num_pisos = 5
        locales_por_piso = [6, 8, 7, 10, 5]  # Ejemplo: cantidad de locales por piso

        for piso in range(num_pisos):
            for local in range(locales_por_piso[piso]):
                name = f"P{piso + 1}L{local + 1}"
                pared = rd.randint(10, 40)  # Resistencia de pared más variada
                ventana = rd.uniform(2.0, 5.0)  # Ventanas con diferentes niveles
                puerta = rd.uniform(1.0, 3.0)  # Variación en puertas
                ruido = rd.randint(10, 50)  # Niveles iniciales ajustados a 10-50
                frecuencia = rd.randint(10, 100)  # Frecuencia del ruido

                habitacion = Nodo(name, pared, ventana, puerta, ruido, frecuencia)
                self.G.add_node(name)
                self.habitaciones[name] = habitacion

                # Conectar con otras habitaciones del mismo piso
                if local > 0:
                    vecino_name = f"P{piso + 1}L{local}"  # Conectar con el anterior
                    self.G.add_edge(name, vecino_name)

                # Conectar con pisos superiores/inferiores
                if piso > 0:
                    vecino_name = f"P{piso}L{rd.randint(1, locales_por_piso[piso - 1])}"
                    self.G.add_edge(name, vecino_name)

    def show_results(self):
        # Mostrar ventana de resultados
        results_window = ResultsWindow(self.habitaciones, self.G)
        results_window.exec_()

    def show_graph(self):
        # Crear la figura y el eje 3D
        fig = Figure(figsize=(8, 6))
        ax = fig.add_subplot(111, projection='3d')

        for name, habitacion in self.habitaciones.items():
            vecinos = [self.habitaciones[vecino] for vecino in self.G.neighbors(name)]
            x, y, z = habitacion.position()
            color = habitacion.calcular_color(vecinos)

            # Representar la habitación como una esfera separada
            u = np.linspace(0, 2 * np.pi, 30)
            v = np.linspace(0, np.pi, 30)
            x_sphere = 0.5 * np.outer(np.cos(u), np.sin(v)) + x
            y_sphere = 0.5 * np.outer(np.sin(u), np.sin(v)) + y
            z_sphere = 0.5 * np.outer(np.ones(np.size(u)), np.cos(v)) + z

            # Dibujar la esfera
            ax.plot_surface(x_sphere, y_sphere, z_sphere, color=color, rstride=1, cstride=1, alpha=0.6, edgecolors='k')

            # Etiquetas
            ax.text(x, y, z + 1.2, name, fontsize=8, color='black')

        # Configuración del gráfico
        ax.set_title("Edificio - Niveles de Ruido")
        ax.set_xlabel("Local (X)")
        ax.set_ylabel("Local (Y)")
        ax.set_zlabel("Piso (Z)")

        # Mostrar el gráfico en una ventana
        graph_window = QDialog(self)
        graph_window.setWindowTitle("Gráfico de Niveles de Ruido")
        graph_window.resize(800, 600)

        layout = QVBoxLayout(graph_window)
        canvas = FigureCanvas(fig)
        layout.addWidget(canvas)

        graph_window.exec_()


    def fix_specific_node(self):
        # Crear ventana para seleccionar un nodo
        fix_window = QDialog(self)
        fix_window.setWindowTitle("Arreglar Nodo")
        fix_window.resize(400, 300)

        layout = QVBoxLayout(fix_window)
        label = QLabel("Ingrese el nombre del nodo a arreglar:")
        layout.addWidget(label)

        node_input = QTextEdit()
        node_input.setFixedHeight(30)
        layout.addWidget(node_input)

        def show_fix_options():
            # Obtener el nodo
            node_name = node_input.toPlainText().strip()
            if node_name in self.habitaciones:
                fix_options_window = QDialog(self)
                fix_options_window.setWindowTitle("Opciones de Arreglo")
                fix_options_window.resize(300, 200)

                options_layout = QVBoxLayout(fix_options_window)

                # Botón para hacer el nodo amarillo (moderar el ruido)
                yellow_button = QPushButton("Hacer Amarillo")
                yellow_button.clicked.connect(lambda: self.apply_fix(node_name, color="yellow"))
                options_layout.addWidget(yellow_button)

                # Botón para hacer el nodo verde (hacerlo habitable)
                green_button = QPushButton("Hacer Verde (Habitable)")
                green_button.clicked.connect(lambda: self.apply_fix(node_name, color="green"))
                options_layout.addWidget(green_button)

                fix_options_window.exec_()
            else:
                label.setText(f"Nodo '{node_name}' no encontrado.")

        # Botón para mostrar las opciones de arreglo
        fix_button = QPushButton("Mostrar Opciones de Arreglo")
        fix_button.clicked.connect(show_fix_options)
        layout.addWidget(fix_button)

        fix_window.exec_()

    def apply_fix(self, node_name, color):
        habitacion = self.habitaciones[node_name]
        
        # Ajustar las propiedades acústicas dependiendo de si es amarillo o verde
        if color == "yellow":
            habitacion.pared = 25  # Moderado
            habitacion.ventana = 3.0
            habitacion.puerta = 2.0
        elif color == "green":
            habitacion.pared = 40  # Mejorado
            habitacion.ventana = 4.0
            habitacion.puerta = 3.0
            habitacion.ruido = 10  # Reducir el ruido al mínimo

        # Actualizar la propagación de ruido (ajustar vecinos)
        for vecino in self.G.neighbors(node_name):
            vecino_habitacion = self.habitaciones[vecino]
            if color == "green":
                vecino_habitacion.ruido = max(10, vecino_habitacion.ruido - 15)  # Reducir ruido en los vecinos

        # Actualizar el gráfico y los resultados
        self.show_results()
        self.show_graph()



# Main
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
