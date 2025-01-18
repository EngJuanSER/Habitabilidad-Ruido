import sys
import random
import math
import json
from copy import deepcopy
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QLabel, QVBoxLayout, QPushButton, QWidget, QScrollArea, QMessageBox, QDesktopWidget
)
from PyQt5.QtCore import Qt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt
import networkx as nx
from matplotlib.lines import Line2D

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

    def medir_ruido(self, vecinos):
        """

        Calcula el nivel total de ruido considerando la propagación desde nodos vecinos.
        
                La propagación del ruido se modela considerando:
        - Atenuación por distancia (inversa al cuadrado)
        - Atenuación entre pisos (50% de reducción)
        - Efectos de elementos estructurales:
            * Ausencia de paredes: +20% propagación
            * Presencia de ventanas: +10% propagación
            * Presencia de puertas: +5% propagación
        - Absorción por paredes: 30% de reducción
        
        """
        
        ruido_propio = self.ruido if self.es_fuente else 0
        ruido_propagado = 0
        for nodo in vecinos:
            distancia = self.calcular_distancia(nodo)
            # Factor base de atenuación por distancia
            atenuacion = 1 / (distancia ** 2)  # Atenuación inversa al cuadrado de la distancia
            
            # Nueva atenuación por frecuencia
            factor_frecuencia = min(1.0, 1.0 / (nodo.frecuencia/1000))
            atenuacion *= factor_frecuencia
            
            # Factores de modificación por elementos estructurales
            if self.piso != nodo.piso:
                atenuacion *= 0.5  # Menor propagación entre pisos
            if not self.pared or not nodo.pared:
                atenuacion *= 1.2  # Mayor propagación si no hay paredes
            if self.ventana or nodo.ventana:
                atenuacion *= 1.1  # Mayor propagación si hay ventanas
            if self.puerta or nodo.puerta:
                atenuacion *= 1.05  # Mayor propagación si hay puertas
            
            
            # Considerar absorción del material según frecuencia
            coef_absorcion = {
                'pared': {'baja': 0.3, 'media': 0.5, 'alta': 0.7},
                'ventana': {'baja': 0.1, 'media': 0.3, 'alta': 0.5},
                'puerta': {'baja': 0.2, 'media': 0.4, 'alta': 0.6}
            }
            
            # Clasificar frecuencia
            if nodo.frecuencia < 500:
                rango_freq = 'baja'
            elif nodo.frecuencia < 2000:
                rango_freq = 'media'
            else:
                rango_freq = 'alta'
                
            # Aplicar absorción específica por material y frecuencia
            if self.pared:
                atenuacion *= (1 - coef_absorcion['pared'][rango_freq])
            if self.ventana:
                atenuacion *= (1 - coef_absorcion['ventana'][rango_freq])
            if self.puerta:
                atenuacion *= (1 - coef_absorcion['puerta'][rango_freq])
                
            ruido_propagado += nodo.ruido * atenuacion

        # Factor de absorción por paredes
        absorcion = 0.7 if self.pared else 1.0
        ruido_total = ruido_propio + (ruido_propagado * absorcion)
        return ruido_total

    def calcular_distancia(self, otro_nodo):
        x1, y1, z1 = self.position
        x2, y2, z2 = otro_nodo.position
        return math.sqrt((x2 - x1)**2 + (y2 - y1)**2 + (z2 - z1)**2)

    def get_limite_ruido(self):
        limites = {
            "aula": {"limite_adecuado": 45, "limite_cercano": 50, "limite_excedido": 60},
            "pasillo": {"limite_adecuado": 47, "limite_cercano": 55, "limite_excedido": 72},
            "biblioteca": {"limite_adecuado": 30, "limite_cercano": 35, "limite_excedido": 40},
            "auditorio": {"limite_adecuado": 50, "limite_cercano": 60, "limite_excedido": 70},
            "cafetería": {"limite_adecuado": 50, "limite_cercano": 60, "limite_excedido": 70},
            "laboratorio": {"limite_adecuado": 40, "limite_cercano": 50, "limite_excedido": 60},
            "oficina": {"limite_adecuado": 35, "limite_cercano": 45, "limite_excedido": 55},
            "reuniones": {"limite_adecuado": 35, "limite_cercano": 45, "limite_excedido": 55},
        }
        return limites.get(self.tipo, {"limite_adecuado": 35, "limite_cercano": 45, "limite_excedido": 55})

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
            texto = f"{simbolo} {name}: {nivel:.2f} dB - {estado}\nRecomendación: {recomendacion}"
            etiqueta = QLabel(texto)
            etiqueta.setWordWrap(True)
            etiqueta.setStyleSheet(f"color: {color};")
            layout.addWidget(etiqueta)

        contenido.setLayout(layout)
        scroll.setWidget(contenido)

        main_layout = QVBoxLayout()
        main_layout.addWidget(scroll)
        self.setLayout(main_layout)

class Grafo3DWindow(QWidget):
    def __init__(self, habitaciones, modo='analisis'):
        super().__init__()
        self.setWindowTitle("Grafo 3D")
        self.setGeometry(150, 150, 800, 600)
        layout = QVBoxLayout()

        fig = plt.figure()
        ax = fig.add_subplot(111, projection='3d')

        G = nx.Graph()
        for name, nodo in habitaciones.items():
            G.add_node(name, tipo=nodo.tipo, ruido=nodo.medir_ruido(self.obtener_vecinos(name, grafo=habitaciones)))

        # Construcción de pisos y conexiones 
        pisos = {}
        for name, nodo in habitaciones.items():
            pisos.setdefault(nodo.piso, []).append(nodo)

        for piso, nodos in pisos.items():
            for i in range(len(nodos)):
                for j in range(i + 1, len(nodos)):
                    G.add_edge(nodos[i].name, nodos[j].name)

        for piso, nodos in pisos.items():
            if piso < max(pisos.keys()):
                pisos_siguiente = pisos.get(piso + 1, [])
                for nodo in nodos:
                    for otro_nodo in pisos_siguiente:
                        distancia_total = nodo.calcular_distancia(otro_nodo)
                        if distancia_total <= 7:
                            G.add_edge(nodo.name, otro_nodo.name)

        # Asignación de posiciones directamente desde los nodos
        pos = {name: nodo.position for name, nodo in habitaciones.items()}
        nx.set_node_attributes(G, pos, 'pos')

        # Asignación de colores basada en los niveles de ruido
        for name, nodo in habitaciones.items():
            niveles = nodo.get_limite_ruido()
            nivel_ruido = nodo.medir_ruido(self.obtener_vecinos(name, grafo=habitaciones))

            if nivel_ruido > niveles['limite_excedido']:
                color = 'red'
            elif nivel_ruido > niveles['limite_cercano']:
                color = 'yellow'
            else:
                color = 'green'

            p = nodo.position 
            ax.scatter(p[0], p[1], p[2], color=color, s=100)
            ax.text(p[0], p[1], p[2], name, fontsize=9)

        # Dibujar conexiones
        for edge in G.edges():
            if edge[0] in habitaciones and edge[1] in habitaciones:
                p1 = habitaciones[edge[0]].position
                p2 = habitaciones[edge[1]].position
                distancia = math.sqrt(
                    (p2[0] - p1[0])**2 +
                    (p2[1] - p1[1])**2 +
                    (p2[2] - p1[2])**2
                )
                atenuacion_value = math.log(distancia + 1)
                linewidth = 1 if atenuacion_value == 0 else 0.5 / atenuacion_value
                ax.plot(
                    [p1[0], p2[0]],
                    [p1[1], p2[1]],
                    [p1[2], p2[2]],
                    color='gray',
                    linestyle='--',
                    linewidth=linewidth
                )

        # Configuración de límites y leyenda
        limite_piso1 = self.obtener_limites_piso1(habitaciones)
        ax.set_xlim([-limite_piso1['x'], limite_piso1['x']])
        ax.set_ylim([-limite_piso1['y'], limite_piso1['y']])
        ax.set_zlim([0, max(piso for piso in pisos.keys()) * 3 + 3])

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
        return {'x': max_x + 5, 'y': max_y + 5}


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Simulación de Ruido")
        self.setGeometry(100, 100, 300, 100)
        self.centrar_ventana()
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        self.habitaciones = {}
        self.datos_ruido = []
        self.reporte_generado = False
        self.posiciones_fijas = {}

        self.inicializar_nodos()

        layout_principal = QVBoxLayout()
        layout_principal.setSpacing(10)
        layout_principal.setContentsMargins(20, 20, 20, 20)

        bot_textos = ["Análisis Inicial", "Solucionar Grafo", "Salir"]
        botones = []
        ancho_boton = self.obtener_ancho_boton(bot_textos)

        layout_botones = QVBoxLayout()
        layout_botones.setSpacing(10)

        for texto in bot_textos:
            btn = QPushButton(texto)
            btn.setFixedWidth(ancho_boton)
            botones.append(btn)
            layout_botones.addWidget(btn, alignment=Qt.AlignCenter)

        layout_principal.addLayout(layout_botones)
        layout_principal.addStretch()

        botones[0].clicked.connect(self.analisis_inicial)
        botones[1].clicked.connect(self.solucionar_grafo)
        botones[2].clicked.connect(self.close)

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
        try:
            with open('edificio.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
        except FileNotFoundError:
            QMessageBox.critical(self, "Error", "El archivo 'edificio.json' no se encontró.")
            sys.exit(1)
        except json.JSONDecodeError as e:
            QMessageBox.critical(self, "Error", f"Error al parsear 'edificio.json': {e}")
            sys.exit(1)
        
        self.habitaciones = {}
        for nodo in data['nodos']:
            self.habitaciones[nodo['name']] = Nodo(
                name=nodo['name'],
                tipo=nodo['tipo'],
                pared=nodo.get('pared', False),
                ventana=nodo.get('ventana', False),
                puerta=nodo.get('puerta', False),
                ruido=nodo['ruido'],
                frecuencia=nodo.get('frecuencia', 1),
                position=tuple(nodo['position']),
                piso=nodo['piso'],
                es_fuente=nodo.get('es_fuente', False)
            )
        
        for habitacion in self.habitaciones.values():
            habitacion.agregar_sensor(Sensor(habitacion.name, ruido_fijo=habitacion.ruido))
        
        self.posiciones_fijas = {name: nodo.position for name, nodo in self.habitaciones.items()}
        
        # Cargar conexiones (vecinos) desde el archivo JSON
        for nodo in data['nodos']:
            nodo_obj = self.habitaciones[nodo['name']]
            for vecino_name in nodo.get('vecinos', []):
                vecino_obj = self.habitaciones.get(vecino_name)
                if vecino_obj:
                    nodo_obj.conectar(vecino_obj)  

    def obtener_vecinos(self, name, grafo):
        vecinos = grafo[name].conexiones
        return vecinos

    def mostrar_grafo_3d(self, grafo, modo):
        """Muestra el grafo en 3D, optimizado y con recoloreado."""
        fig = plt.figure()
        ax = fig.add_subplot(111, projection='3d')
    
        # Dibujar nodos
        for name, nodo in grafo.items():
            vecinos = self.obtener_vecinos(name, grafo)
            nivel_ruido = nodo.medir_ruido(vecinos)
            limites = nodo.get_limite_ruido()
            if nivel_ruido > limites['limite_excedido']:
                color = "red"
                estado = "Excede"
            elif nivel_ruido > limites['limite_cercano']:
                color = "yellow"
                estado = "Cerca"
            else:
                color = "green"
                estado = "Adecuado"
        
            x, y, z = nodo.position
            ax.scatter(x, y, z, color=color, s=100)
            ax.text(x, y, z, name, fontsize=8)
    
        for nodo in grafo.values():
            for vecino in nodo.conexiones:
                p1, p2 = nodo.position, vecino.position
                distancia = nodo.calcular_distancia(vecino)
                ax.plot(
                    [p1[0], p2[0]], [p1[1], p2[1]], [p1[2], p2[2]],
                    color="gray", linewidth=max(0.1, 1 / (distancia + 1))
                )
    
        ax.set_title(f"Grafo 3D - {modo.capitalize()}")
        ax.set_xlabel("X")
        ax.set_ylabel("Y")
        ax.set_zlabel("Z")
        plt.show()

    def analisis_inicial(self):
        self.mostrar_grafo_3d(self.habitaciones, "análisis inicial")
        # Generar datos de reporte para el análisis inicial
        datos_reporte = self.generar_reporte_inicial(self.habitaciones)
        
        # Mostrar reporte del análisis inicial
        self.mostrar_reporte_inicial(datos_reporte)

    def solucionar_grafo(self):
        # Crear una copia profunda del grafo de análisis inicial
        grafo_copia = deepcopy(self.habitaciones)
        
        # Optimizar la habitabilidad del grafo
        grafo_optimizado, cambios = self.optimizar_habitabilidad(grafo_copia)
        
        # Generar datos de reporte
        datos_reporte = self.generar_reporte_solucion(grafo_optimizado)
        
        # Mostrar reporte
        self.mostrar_reporte(datos_reporte, cambios=cambios)
        
        # Mostrar grafo solucionado
        self.mostrar_grafo_3d(grafo_optimizado, modo='solución')

    def optimizar_habitabilidad(self, grafo):
        """
        Optimiza la distribución de espacios mediante recocido simulado.
        
        El proceso utiliza los siguientes parámetros:
        - Temperatura inicial: 100.0 (controla probabilidad de aceptar soluciones peores)
        - Factor de enfriamiento: 0.95 (reduce temperatura gradualmente)
        - Iteraciones: 1000 (número de intentos de optimización)
        
        El algoritmo:
        1. Selecciona dos nodos al azar (excluyendo pasillos y la recepcion)
        2. Intercambia sus características:
           - Tipo de espacio
           - Nivel de ruido
           - Condición de fuente
           - Posición física
        3. Evalúa la nueva configuración
        4. Acepta el cambio si:
           - Mejora la situación (menor puntaje)
           - O con probabilidad basada en temperatura actual
        """

    
        # Parámetros del recocido simulado
        temperatura = 100.0
        enfriamiento = 0.95
        iteraciones = 1000
    
        # Estado inicial
        mejor_grafo = deepcopy(grafo)
        mejor_puntaje = self.calcular_habitabilidad_total(mejor_grafo)


        mejores_cambios = []
    
        actual_grafo = deepcopy(grafo)
        actual_puntaje = mejor_puntaje
        cambios_actuales = []
    
        # Matriz de compatibilidad entre espacios
        compatibilidad = {
            "biblioteca": ["oficina", "reuniones"],
            "aula": ["laboratorio", "auditorio"],
            "cafetería": ["pasillo", "reuniones"],
            "laboratorio": ["aula", "oficina"],
            "oficina": ["biblioteca", "reuniones"],
            "auditorio": ["aula", "pasillo"],
            "reuniones": ["oficina", "biblioteca"]
        }

        for i in range(iteraciones):
            nuevo_grafo = deepcopy(actual_grafo)
            cambios = deepcopy(cambios_actuales)

            # Identificar nodos problemáticos
            nodos_problematicos = [
                nodo for nodo in nuevo_grafo.values()
                if nodo.tipo != "pasillo" and nodo.tipo != "recepcion" and
                nodo.medir_ruido(self.obtener_vecinos(nodo.name, nuevo_grafo)) > 
                nodo.get_limite_ruido()['limite_cercano']
            ]

            if nodos_problematicos and random.random() < 0.7:  # 70% de probabilidad de elegir nodo problemático
                nodo1 = random.choice(nodos_problematicos)
                # Buscar nodo compatible para intercambio
                candidatos = [
                    nodo for nodo in nuevo_grafo.values()
                    if nodo.tipo != "pasillo" and nodo.tipo != "recepcion" and
                    nodo.tipo in compatibilidad.get(nodo1.tipo, []) and
                    nodo != nodo1
                ]
                if candidatos:
                    nodo2 = min(candidatos, 
                            key=lambda x: x.medir_ruido(self.obtener_vecinos(x.name, nuevo_grafo)))
                else:
                    nodos_no_pasillo = [n for n in nuevo_grafo.values() if n.tipo != "pasillo" and n.tipo != "recepcion" and n != nodo1]
                    nodo2 = random.choice(nodos_no_pasillo)
            else:
                # Selección aleatoria tradicional
                nodos_no_pasillo = [nodo for nodo in nuevo_grafo.values() if nodo.tipo != "pasillo" and nodo.tipo != "recepcion"]
                nodo1, nodo2 = random.sample(nodos_no_pasillo, 2)
    
            # Intercambiar actividades
            nodo1.tipo, nodo2.tipo = nodo2.tipo, nodo1.tipo
            nodo1.ruido, nodo2.ruido = nodo2.ruido, nodo1.ruido
            nodo1.es_fuente, nodo2.es_fuente = nodo2.es_fuente, nodo1.es_fuente

            # Intercambiar tipos
            nodo1.tipo, nodo2.tipo = nodo2.tipo, nodo1.tipo


            # Intercambiar posiciones
            nodo1.position, nodo2.position = nodo2.position, nodo1.position

            # Registrar el cambio
            cambios.append((nodo1.name, nodo2.name))
    
            # Calcular puntaje de la nueva solución
            nuevo_puntaje = self.calcular_habitabilidad_total(nuevo_grafo)
    
            # Ajuste del factor de aceptación basado en la temperatura actual
            factor_temperatura = temperatura / 100.0  # Normalizar temperatura
            delta = nuevo_puntaje - actual_puntaje
       

            # Criterio de aceptación mejorado
            if delta < 0 or random.random() < math.exp(-delta / (temperatura * (1 + i/iteraciones))):
                actual_grafo = nuevo_grafo
                actual_puntaje = nuevo_puntaje
                cambios_actuales = cambios

                if nuevo_puntaje < mejor_puntaje:
                    mejor_grafo = deepcopy(nuevo_grafo)
                    mejor_puntaje = nuevo_puntaje
                    mejores_cambios = deepcopy(cambios_actuales)

            temperatura *= enfriamiento

        return mejor_grafo, mejores_cambios

    def calcular_habitabilidad_total(self, grafo):
        puntaje_total = 0
        for name, nodo in grafo.items():
            if nodo.tipo == "pasillo":
                continue
            vecinos = self.obtener_vecinos(name, grafo)
            nivel_ruido = nodo.medir_ruido(vecinos)
            limites = nodo.get_limite_ruido()
            exceso = max(0, nivel_ruido - limites['limite_adecuado'])
            puntaje_total += exceso
        return puntaje_total

    def mostrar_reporte(self, datos_reporte, cambios):
        """Muestra el reporte de ruido con información de redistribución."""
        if datos_reporte is None:
            QMessageBox.critical(self, "Error", "No se pudieron generar los datos del reporte.")
            return
        
        self.ventana_reporte = QWidget()
        self.ventana_reporte.setWindowTitle("Reporte de Habitabilidad")
        self.ventana_reporte.setGeometry(100, 100, 500, 600)
    
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
    
        contenido = QWidget()
        layout = QVBoxLayout()
    
        # Detallar los cambios realizados
        layout.addWidget(QLabel("<b>Redistribución de Nodos:</b>"))
        for cambio in cambios:
            texto_cambio = f"Nodo <b>{cambio[0]}</b> intercambiado con Nodo <b>{cambio[1]}</b>"
            etiqueta_cambio = QLabel(texto_cambio)
            etiqueta_cambio.setWordWrap(True)
            layout.addWidget(etiqueta_cambio)
    
        layout.addWidget(QLabel("<br><b>Reporte de Nodos:</b>"))
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
            texto = f"{simbolo} <b>{name}</b>: {nivel:.2f} dB - {estado}<br>Recomendación: {recomendacion}"
            etiqueta = QLabel(texto)
            etiqueta.setWordWrap(True)
            etiqueta.setStyleSheet(f"color: {color};")
            layout.addWidget(etiqueta)
    
        contenido.setLayout(layout)
        scroll.setWidget(contenido)
    
        main_layout = QVBoxLayout()
        main_layout.addWidget(scroll)
        self.ventana_reporte.setLayout(main_layout)
        self.ventana_reporte.show()

    def mostrar_reporte_inicial(self, datos_reporte):
        """Muestra el reporte de ruido para el análisis inicial sin recomendaciones."""
        if datos_reporte is None:
            QMessageBox.critical(self, "Error", "No se pudieron generar los datos del reporte.")
            return
        
        # Crea ventana con scroll para visualizar cada nodo y sus datos

        self.ventana_reporte_inicial = QWidget()
        self.ventana_reporte_inicial.setWindowTitle("Reporte de Análisis Inicial")
        self.ventana_reporte_inicial.setGeometry(100, 100, 500, 600)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        contenido = QWidget()
        layout = QVBoxLayout()

        layout.addWidget(QLabel("<b>Reporte de Nodos:</b>"))
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
            texto = f"{simbolo} <b>{name}</b>: {nivel:.2f} dB - {estado}<br>Recomendación: {recomendacion}"
            etiqueta = QLabel(texto)
            etiqueta.setWordWrap(True)
            etiqueta.setStyleSheet(f"color: {color};")
            layout.addWidget(etiqueta)

        contenido.setLayout(layout)
        scroll.setWidget(contenido)

        main_layout = QVBoxLayout()
        main_layout.addWidget(scroll)
        self.ventana_reporte_inicial.setLayout(main_layout)
        self.ventana_reporte_inicial.show()

    def generar_reporte_inicial(self, grafo):
        """
        Genera datos de reporte inicial (antes de la optimización).
        Evalúa el nivel de ruido y asigna estado y recomendación.
        """
        datos_reporte = []
        for name, nodo in grafo.items():
            vecinos = self.obtener_vecinos(name, grafo)
            nivel = nodo.medir_ruido(vecinos)
            limites = nodo.get_limite_ruido()
            tipo_espacio = nodo.tipo.lower()
            # Determina estado según el nivel y personaliza la recomendación
            if nivel > limites['limite_excedido']:
                estado = "Excede"
                recomendaciones = {
                "aula": "Instalar paneles acústicos en paredes, considerar cortinas absorbentes y revisar el sellado de ventanas.",
                "biblioteca": "Implementar zonas de silencio, agregar alfombras y mobiliario con materiales absorbentes.",
                "auditorio": "Revisar el sistema de aislamiento acústico, instalar paneles difusores y verificar puertas acústicas.",
                "cafetería": "Agregar separadores acústicos entre zonas, implementar techos absorbentes y usar mobiliario que reduzca reverberación.",
                "laboratorio": "Instalar cabinas de aislamiento para equipos ruidosos, revisar el funcionamiento de ventilación.",
                "oficina": "Implementar mamparas absorbentes, agregar plantas y considerar redistribución de espacios de trabajo.",
                "reuniones": "Instalar paneles acústicos móviles, revisar sellado de puertas y ventanas.",
                "pasillo": "Instalar materiales absorbentes en paredes y techo, considerar barreras acústicas móviles."
            }
            elif nivel > limites['limite_cercano']:
                estado = "Cerca"
                recomendaciones = {
                "aula": "Verificar el aislamiento de ventanas y puertas, considerar uso de cortinas acústicas.",
                "biblioteca": "Reforzar políticas de silencio, agregar señalización y considerar separadores acústicos.",
                "auditorio": "Revisar el estado de las puertas acústicas y sellos, verificar sistema de ventilación.",
                "cafetería": "Evaluar la distribución de mesas y considerar agregar elementos absorbentes decorativos.",
                "laboratorio": "Verificar el mantenimiento de equipos y considerar horarios de uso.",
                "oficina": "Evaluar la distribución de espacios y agregar elementos absorbentes.",
                "reuniones": "Verificar el sellado acústico y considerar uso de materiales absorbentes.",
                "pasillo": "Implementar señalización de reducción de ruido y evaluar flujos de tránsito."
            }
            else:
                estado = "Adecuado"
                recomendaciones = {
                "aula": "Mantener el monitoreo regular de niveles de ruido.",
                "biblioteca": "Continuar con las políticas actuales de control de ruido.",
                "auditorio": "Realizar mantenimiento preventivo de sistemas acústicos.",
                "cafetería": "Mantener la distribución actual y políticas de uso.",
                "laboratorio": "Seguir con los protocolos actuales de operación.",
                "oficina": "Mantener la configuración actual del espacio.",
                "reuniones": "Conservar las prácticas actuales de uso.",
                "pasillo": "Mantener las medidas actuales de control de ruido."
            }
                
            recomendacion = recomendaciones.get(tipo_espacio, "Revisar configuración del espacio.")
            datos_reporte.append((name, nivel, estado, recomendacion))
        
        return datos_reporte

    def generar_reporte_solucion(self, grafo):
        """
        Genera reporte tras la optimización de habitabilidad.
        Se basa en los mismos criterios de ruido que el reporte inicial.
        """
        datos_reporte = []
        for name, nodo in grafo.items():
            vecinos = self.obtener_vecinos(name, grafo)
            nivel = nodo.medir_ruido(vecinos)
            limites = nodo.get_limite_ruido()
            tipo_espacio = nodo.tipo.lower()

            if nivel > limites['limite_excedido']:
                recomendacion = f"Urgente: Implementar medidas de control acústico para el espacio {tipo_espacio}. Considerar redistribución adicional o refuerzo del aislamiento."
                estado = "Excede"
            elif nivel > limites['limite_cercano']:
                recomendacion = f"Precaución: Monitorear niveles de ruido en el espacio {tipo_espacio} y planificar mejoras preventivas."
                estado = "Cerca"
            else:
                recomendacion = f"Óptimo: Mantener configuración actual del espacio {tipo_espacio} y realizar monitoreo periódico."
                estado = "Adecuado"
            
            datos_reporte.append((name, nivel, estado, recomendacion))
        
        return datos_reporte


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())