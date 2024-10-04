import sys
import cv2
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QPushButton,
    QLabel,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
    QFileDialog,
    QTextEdit,
    QComboBox,
    QCheckBox,
    QMessageBox,
    QScrollArea,
    QLineEdit,
    QToolBar,
    QStatusBar,
)
from PyQt5.QtCore import Qt, QTimer, QSettings, QSize
from PyQt5.QtGui import QPixmap, QImage, QIcon
from pyzbar.pyzbar import decode
import numpy as np
import webbrowser
import os


class AplicacionDecodificadorQR(QMainWindow):
    def __init__(self):
        super().__init__()
        self.configuraciones = QSettings("DecodificadorQR", "App")
        self.modo_oscuro = self.configuraciones.value("modo_oscuro", True, type=bool)
        self.inicializar_interfaz()
        self.inicializar_camara()
        self.historial = []
        self.aplicar_tema()

    def inicializar_interfaz(self):
        self.setWindowTitle("Decodificador QR")
        self.setMinimumSize(1000, 700)
        widget_central = QWidget()
        self.setCentralWidget(widget_central)
        disposicion = QVBoxLayout(widget_central)
        disposicion.setSpacing(15)
        disposicion.setContentsMargins(20, 20, 20, 20)
        barra_herramientas = QToolBar()
        barra_herramientas.setIconSize(QSize(32, 32))
        self.addToolBar(barra_herramientas)
        accion_tema = QPushButton("Cambiar Tema")
        accion_tema.setFixedSize(150, 40)
        accion_tema.clicked.connect(self.alternar_tema)
        barra_herramientas.addWidget(accion_tema)
        disposicion_camara = QHBoxLayout()
        disposicion_camara.setSpacing(20)
        contenedor_camara = QWidget()
        disposicion_contenedor_camara = QVBoxLayout(contenedor_camara)
        disposicion_contenedor_camara.setSpacing(15)
        self.etiqueta_camara = QLabel()
        self.etiqueta_camara.setAlignment(Qt.AlignCenter)
        self.etiqueta_camara.setMinimumSize(500, 400)
        self.etiqueta_camara.setStyleSheet(
            "border: 2px solid #333; border-radius: 10px;"
        )
        disposicion_contenedor_camara.addWidget(self.etiqueta_camara)
        controles_camara = QHBoxLayout()
        controles_camara.setSpacing(10)
        self.selector_camara = QComboBox()
        self.selector_camara.setFixedHeight(40)
        self.actualizar_camaras()
        self.selector_camara.currentIndexChanged.connect(self.cambiar_camara)
        controles_camara.addWidget(self.selector_camara)
        self.boton_inicio_parada = QPushButton("Detener")
        self.boton_inicio_parada.setFixedSize(100, 40)
        self.boton_inicio_parada.clicked.connect(self.alternar_camara)
        controles_camara.addWidget(self.boton_inicio_parada)
        boton_cargar_imagen = QPushButton("Cargar Imagen QR")
        boton_cargar_imagen.setFixedSize(150, 40)
        boton_cargar_imagen.clicked.connect(self.cargar_imagen)
        controles_camara.addWidget(boton_cargar_imagen)
        disposicion_contenedor_camara.addLayout(controles_camara)
        disposicion_camara.addWidget(contenedor_camara)
        contenedor_resultados = QWidget()
        disposicion_resultados = QVBoxLayout(contenedor_resultados)
        disposicion_resultados.setSpacing(15)
        etiqueta_resultado = QLabel("Resultado")
        etiqueta_resultado.setAlignment(Qt.AlignCenter)
        disposicion_resultados.addWidget(etiqueta_resultado)
        self.texto_resultado = QTextEdit()
        self.texto_resultado.setReadOnly(True)
        self.texto_resultado.setMinimumSize(300, 200)
        disposicion_resultados.addWidget(self.texto_resultado)
        disposicion_botones = QHBoxLayout()
        disposicion_botones.setSpacing(10)
        boton_copiar = QPushButton("Copiar")
        boton_copiar.setFixedSize(100, 40)
        boton_copiar.clicked.connect(self.copiar_resultado)
        disposicion_botones.addWidget(boton_copiar)
        boton_abrir = QPushButton("Abrir URL")
        boton_abrir.setFixedSize(100, 40)
        boton_abrir.clicked.connect(self.abrir_url)
        disposicion_botones.addWidget(boton_abrir)
        boton_guardar = QPushButton("Guardar")
        boton_guardar.setFixedSize(100, 40)
        boton_guardar.clicked.connect(self.guardar_resultado)
        disposicion_botones.addWidget(boton_guardar)
        disposicion_resultados.addLayout(disposicion_botones)
        disposicion_camara.addWidget(contenedor_resultados)
        disposicion.addLayout(disposicion_camara)
        etiqueta_historial = QLabel("Historial de Escaneos")
        etiqueta_historial.setAlignment(Qt.AlignCenter)
        disposicion.addWidget(etiqueta_historial)
        self.area_historial = QScrollArea()
        self.widget_historial = QWidget()
        self.disposicion_historial = QVBoxLayout(self.widget_historial)
        self.disposicion_historial.setSpacing(10)
        self.area_historial.setWidget(self.widget_historial)
        self.area_historial.setWidgetResizable(True)
        self.area_historial.setMinimumHeight(150)
        disposicion.addWidget(self.area_historial)
        barra_estado = QStatusBar()
        self.setStatusBar(barra_estado)
        self.etiqueta_estado = QLabel("Listo")
        barra_estado.addWidget(self.etiqueta_estado)

    def inicializar_camara(self):
        self.camara = None
        self.temporizador = QTimer()
        self.temporizador.timeout.connect(self.actualizar_frame)
        self.iniciar_camara()

    def actualizar_camaras(self):
        self.selector_camara.clear()
        camaras_disponibles = []
        for i in range(5):
            try:
                cap = cv2.VideoCapture(i)
                if cap.isOpened():
                    ret, _ = cap.read()
                    if ret:
                        camaras_disponibles.append(i)
                    cap.release()
            except Exception as e:
                print(f"Error al intentar acceder a la cámara {i}: {str(e)}")
        for i in camaras_disponibles:
            self.selector_camara.addItem(f"Cámara {i}")
        if not camaras_disponibles:
            QMessageBox.warning(self, "Error", "No se detectaron cámaras disponibles")

    def cambiar_camara(self):
        self.iniciar_camara()

    def iniciar_camara(self):
        if self.camara is not None:
            self.camara.release()
        if self.selector_camara.count() == 0:
            QMessageBox.warning(self, "Error", "No hay cámaras disponibles")
            return
        indice_camara = self.selector_camara.currentIndex()
        try:
            self.camara = cv2.VideoCapture(indice_camara)
            if not self.camara.isOpened():
                raise Exception("No se pudo abrir la cámara")
            self.temporizador.start(30)
            self.boton_inicio_parada.setText("Detener")
        except Exception as e:
            QMessageBox.warning(
                self, "Error", f"No se pudo iniciar la cámara: {str(e)}"
            )
            self.camara = None

    def detener_camara(self):
        self.temporizador.stop()
        if self.camara is not None:
            self.camara.release()
            self.camara = None
        self.boton_inicio_parada.setText("Iniciar")
        self.etiqueta_camara.clear()

    def alternar_camara(self):
        if self.temporizador.isActive():
            self.detener_camara()
        else:
            self.iniciar_camara()

    def cargar_imagen(self):
        nombre_archivo, _ = QFileDialog.getOpenFileName(
            self, "Cargar Imagen QR", "", "Imágenes (*.png *.jpg *.jpeg *.bmp *.gif)"
        )
        if nombre_archivo:
            imagen = cv2.imread(nombre_archivo)
            if imagen is not None:
                codigos = decode(imagen)
                for codigo in codigos:
                    datos = codigo.data.decode("utf-8")
                    if datos not in self.historial:
                        self.historial.append(datos)
                        self.agregar_al_historial(datos)
                        self.texto_resultado.setText(datos)
                        self.etiqueta_estado.setText(
                            f"QR detectado: {datos[:30]}..."
                            if len(datos) > 30
                            else datos
                        )
                    puntos = codigo.polygon
                    if len(puntos) > 4:
                        casco = cv2.convexHull(
                            np.array([punto for punto in puntos], dtype=np.float32)
                        )
                        puntos = casco
                    n = len(puntos)
                    for j in range(n):
                        cv2.line(
                            imagen,
                            tuple(puntos[j]),
                            tuple(puntos[(j + 1) % n]),
                            (0, 255, 0),
                            3,
                        )
                imagen_rgb = cv2.cvtColor(imagen, cv2.COLOR_BGR2RGB)
                h, w, ch = imagen_rgb.shape
                bytes_por_linea = ch * w
                imagen_qt = QImage(
                    imagen_rgb.data, w, h, bytes_por_linea, QImage.Format_RGB888
                )
                pixmap_escalado = QPixmap.fromImage(imagen_qt).scaled(
                    self.etiqueta_camara.size(),
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation,
                )
                self.etiqueta_camara.setPixmap(pixmap_escalado)
            else:
                QMessageBox.warning(self, "Error", "No se pudo cargar la imagen")

    def actualizar_frame(self):
        ret, frame = self.camara.read()
        if ret:
            codigos = decode(frame)
            for codigo in codigos:
                datos = codigo.data.decode("utf-8")
                if datos not in self.historial:
                    self.historial.append(datos)
                    self.agregar_al_historial(datos)
                    self.texto_resultado.setText(datos)
                    self.etiqueta_estado.setText(
                        f"QR detectado: {datos[:30]}..." if len(datos) > 30 else datos
                    )
                puntos = codigo.polygon
                if len(puntos) > 4:
                    casco = cv2.convexHull(
                        np.array([punto for punto in puntos], dtype=np.float32)
                    )
                    puntos = casco
                n = len(puntos)
                for j in range(n):
                    cv2.line(
                        frame,
                        tuple(puntos[j]),
                        tuple(puntos[(j + 1) % n]),
                        (0, 255, 0),
                        3,
                    )
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = frame_rgb.shape
            bytes_por_linea = ch * w
            imagen_qt = QImage(
                frame_rgb.data, w, h, bytes_por_linea, QImage.Format_RGB888
            )
            pixmap_escalado = QPixmap.fromImage(imagen_qt).scaled(
                self.etiqueta_camara.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            self.etiqueta_camara.setPixmap(pixmap_escalado)

    def agregar_al_historial(self, datos):
        widget_item = QWidget()
        disposicion_item = QHBoxLayout(widget_item)
        disposicion_item.setContentsMargins(5, 5, 5, 5)
        etiqueta_texto = QLineEdit(datos)
        etiqueta_texto.setReadOnly(True)
        disposicion_item.addWidget(etiqueta_texto)
        boton_copiar = QPushButton("Copiar")
        boton_copiar.setFixedSize(80, 30)
        boton_copiar.clicked.connect(lambda: self.copiar_al_portapapeles(datos))
        disposicion_item.addWidget(boton_copiar)
        if datos.startswith(("http://", "https://")):
            boton_abrir = QPushButton("Abrir")
            boton_abrir.setFixedSize(80, 30)
            boton_abrir.clicked.connect(lambda: webbrowser.open(datos))
            disposicion_item.addWidget(boton_abrir)
        self.disposicion_historial.insertWidget(0, widget_item)

    def copiar_resultado(self):
        QApplication.clipboard().setText(self.texto_resultado.toPlainText())
        self.etiqueta_estado.setText("Texto copiado al portapapeles")

    def copiar_al_portapapeles(self, texto):
        QApplication.clipboard().setText(texto)
        self.etiqueta_estado.setText("Texto copiado al portapapeles")

    def abrir_url(self):
        url = self.texto_resultado.toPlainText()
        if url.startswith(("http://", "https://")):
            webbrowser.open(url)
        else:
            QMessageBox.warning(self, "Error", "El texto no es una URL válida")

    def guardar_resultado(self):
        if not self.texto_resultado.toPlainText():
            QMessageBox.warning(self, "Error", "No hay resultado para guardar")
            return
        nombre_archivo, _ = QFileDialog.getSaveFileName(
            self, "Guardar Resultado", "", "Archivos de texto (*.txt)"
        )
        if nombre_archivo:
            with open(nombre_archivo, "w") as archivo:
                archivo.write(self.texto_resultado.toPlainText())
            self.etiqueta_estado.setText(f"Resultado guardado en {nombre_archivo}")

    def alternar_tema(self):
        self.modo_oscuro = not self.modo_oscuro
        self.configuraciones.setValue("modo_oscuro", self.modo_oscuro)
        self.aplicar_tema()

    def aplicar_tema(self):
        if self.modo_oscuro:
            self.setStyleSheet(
                """
            QMainWindow, QWidget { 
                background-color: #1E1E2E; 
                color: #CDD6F4; 
                font-family: 'Segoe UI', sans-serif;
            }
            QPushButton { 
                background-color: #89B4FA; 
                color: #1E1E2E; 
                border: none; 
                padding: 8px; 
                border-radius: 8px; 
                font-size: 14px; 
                font-weight: bold;
                transition: background-color 0.3s;
            }
            QPushButton:hover { 
                background-color: #B4BEFE; 
            }
            QPushButton:pressed {
                background-color: #74C7EC;
            }
            QLabel { 
                font-size: 16px; 
                color: #CDD6F4;
                font-weight: bold;
            }
            QTextEdit, QLineEdit { 
                background-color: #313244; 
                color: #CDD6F4; 
                border: 2px solid #89B4FA; 
                border-radius: 8px; 
                padding: 8px; 
                font-size: 14px;
            }
            QComboBox { 
                background-color: #313244; 
                color: #CDD6F4; 
                border: 2px solid #89B4FA; 
                border-radius: 8px; 
                padding: 8px; 
                font-size: 14px;
            }
            QComboBox::drop-down { 
                border: none;
                border-radius: 8px;
            }
            QComboBox::down-arrow { 
                image: none; 
                border-left: 6px solid #89B4FA; 
                border-right: 6px solid transparent; 
                border-top: 6px solid #89B4FA; 
                margin-right: 10px;
            }
            QScrollArea, QScrollBar { 
                background-color: #313244; 
                border: 2px solid #89B4FA; 
                border-radius: 8px; 
            }
            QToolBar { 
                background-color: #1E1E2E; 
                border: none; 
                spacing: 10px;
                padding: 10px;
            }
            QStatusBar { 
                background-color: #1E1E2E; 
                color: #CDD6F4; 
                padding: 8px;
            }
            QScrollBar:vertical {
                border: none;
                background-color: #313244;
                width: 14px;
                margin: 15px 0 15px 0;
                border-radius: 0px;
            }
            QScrollBar::handle:vertical {
                background-color: #89B4FA;
                min-height: 30px;
                border-radius: 7px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #B4BEFE;
            }
            QScrollBar::sub-line:vertical, QScrollBar::add-line:vertical {
                border: none;
                background: none;
            }
        """
            )
        else:
            self.setStyleSheet(
                """
            QMainWindow, QWidget { 
                background-color: #EFF1F5; 
                color: #4C4F69; 
                font-family: 'Segoe UI', sans-serif;
            }
            QPushButton { 
                background-color: #7287FD; 
                color: white; 
                border: none; 
                padding: 8px; 
                border-radius: 8px; 
                font-size: 14px; 
                font-weight: bold;
            }
            QPushButton:hover { 
                background-color: #8839EF; 
            }
            QPushButton:pressed {
                background-color: #209FB5;
            }
            QLabel { 
                font-size: 16px; 
                color: #4C4F69;
                font-weight: bold;
            }
            QTextEdit, QLineEdit { 
                background-color: white; 
                color: #4C4F69; 
                border: 2px solid #7287FD; 
                border-radius: 8px; 
                padding: 8px;
                font-size: 14px;
            }
            QComboBox { 
                background-color: white; 
                color: #4C4F69; 
                border: 2px solid #7287FD; 
                border-radius: 8px; 
                padding: 8px;
                font-size: 14px;
            }
            QComboBox::drop-down { 
                border: none;
            }
            QComboBox::down-arrow { 
                image: none; 
                border-left: 6px solid #7287FD; 
                border-right: 6px solid transparent; 
                border-top: 6px solid #7287FD;
                margin-right: 10px;
            }
            QScrollArea, QScrollBar { 
                background-color: white; 
                border: 2px solid #7287FD; 
                border-radius: 8px; 
            }
            QToolBar { 
                background-color: #EFF1F5; 
                border: none; 
                spacing: 10px;
                padding: 10px;
            }
            QStatusBar { 
                background-color: #EFF1F5; 
                color: #4C4F69;
                padding: 8px;
            }
            QScrollBar:vertical {
                border: none;
                background-color: #DCE0E8;
                width: 14px;
                margin: 15px 0 15px 0;
                border-radius: 0px;
            }
            QScrollBar::handle:vertical {
                background-color: #7287FD;
                min-height: 30px;
                border-radius: 7px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #8839EF;
            }
            QScrollBar::sub-line:vertical, QScrollBar::add-line:vertical {
                border: none;
                background: none;
            }
        """
            )

    def closeEvent(self, evento):
        self.detener_camara()
        evento.accept()


def main():
    app = QApplication(sys.argv)
    ex = AplicacionDecodificadorQR()
    ex.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
