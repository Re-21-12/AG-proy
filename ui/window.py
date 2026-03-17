import sys
import re
import pandas as pd
from PyQt6.QtWidgets import (QApplication, QMainWindow, QTableWidget, 
                             QTableWidgetItem, QVBoxLayout, QHBoxLayout, 
                             QWidget, QPushButton, QHeaderView, QLabel)
# Importamos tu función de grafos
# from logic.grafos import generar_grafo_flujo 

class VentanaEditarGrafo(QMainWindow):
    COLUMNAS_ENTERO  = {"CapacidadMinima", "CapacidadMaxima", "FlujoEntrada", "PorcentajeDeTiempo"}
    COLUMNAS_OCULTAS = {"Porcentaje", "PorcentajeDeTiempo"}

    def __init__(self, csv_path, configuracion=None):
        super().__init__()
        self.csv_path = csv_path
        self.setWindowTitle("Ingreso de GRAFO")
        self.resize(1000, 500)

        self.configuracion = configuracion or {
            "generaciones": 0,
            "eficiencia": 0.0,
            "individuos": 0,
        }

        # Cargar datos iniciales
        self.df = pd.read_csv(csv_path, skipinitialspace=True)
        self.columnas_visibles = [c for c in self.df.columns if c not in self.COLUMNAS_OCULTAS]

        # Widget Principal
        self.main_widget = QWidget()
        self.setCentralWidget(self.main_widget)
        self.layout_principal = QHBoxLayout(self.main_widget)

        # --- TABLA ---
        self.tabla = QTableWidget()
        self.tabla.setColumnCount(len(self.columnas_visibles))
        self.tabla.setHorizontalHeaderLabels(self.columnas_visibles)
        self.cargar_datos_en_tabla()
        self.layout_principal.addWidget(self.tabla)

        # --- BOTONES + CONFIG (Lado derecho) ---
        self.layout_botones = QVBoxLayout()

        self.lbl_config = QLabel(
            "Configuración activa:\n"
            f"Generaciones: {self.configuracion.get('generaciones', 0)}\n"
            f"Eficiencia: {self.configuracion.get('eficiencia', 0)}%\n"
            f"Individuos: {self.configuracion.get('individuos', 0)}"
        )
        self.layout_botones.addWidget(self.lbl_config)

        self.btn_agregar = QPushButton("Agregar")
        self.btn_quitar = QPushButton("Quitar")
        self.btn_preview = QPushButton("Preview")
        self.btn_limpiar = QPushButton("Limpiar")

        for btn in [self.btn_agregar, self.btn_quitar, self.btn_preview, self.btn_limpiar]:
            btn.setFixedWidth(100)
            self.layout_botones.addWidget(btn)

        self.layout_botones.addStretch() # Empuja los botones hacia arriba
        self.layout_principal.addLayout(self.layout_botones)

        # Conectar eventos
        self.btn_preview.clicked.connect(self.mostrar_grafico)
        self.btn_agregar.clicked.connect(self.agregar_fila)
        self.btn_quitar.clicked.connect(self.quitar_fila)

    def _sanitizar_valor(self, valor, columna=""):
        """Sanitiza el valor según las reglas de cada columna."""
        texto = "" if valor is None else str(valor).strip()
        if texto.lower() in ("nan", "none", "null", "undefined", ""):
            texto = "0"

        if columna == "Arista":
            # Siempre string; debe tener formato a<número>
            if not re.match(r'^a\d+$', texto):
                m = re.search(r'\d+', texto)
                texto = f"a{m.group()}" if m else texto
            return texto

        if columna == "TipoArista":
            t = texto.upper()
            return t if t in ("ENTRADA", "SALIDA") else "INTERMEDIO"

        if columna in ("NodoOrigen", "NodoDestino"):
            # Debe ser n + un único dígito
            if not re.match(r'^n\d$', texto):
                m = re.search(r'\d', texto)
                texto = f"n{m.group()}" if m else "n0"
            return texto

        if columna in self.COLUMNAS_ENTERO:
            try:
                return str(int(float(texto)))
            except (ValueError, TypeError):
                return "0"

        return texto

    def cargar_datos_en_tabla(self):
        self.tabla.setRowCount(len(self.df))
        for i in range(len(self.df)):
            for j, col in enumerate(self.columnas_visibles):
                valor = self.df[col].iloc[i]
                item = QTableWidgetItem(self._sanitizar_valor(valor, col))
                self.tabla.setItem(i, j, item)
        self.tabla.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

    def agregar_fila(self):
        self.tabla.insertRow(self.tabla.rowCount())

    def quitar_fila(self):
        current_row = self.tabla.currentRow()
        if current_row >= 0:
            self.tabla.removeRow(current_row)

    def mostrar_grafico(self):
        # 1. Guardar cambios de la tabla al DataFrame antes de graficar
        datos_editados = []
        for row in range(self.tabla.rowCount()):
            fila = {}
            for j, col in enumerate(self.columnas_visibles):
                item = self.tabla.item(row, j)
                fila[col] = self._sanitizar_valor(item.text() if item else None, col)
            datos_editados.append(fila)

        nuevo_df = pd.DataFrame(datos_editados)
        # Conservar columnas ocultas del CSV original
        for col in self.df.columns:
            if col in self.COLUMNAS_OCULTAS and col not in nuevo_df.columns:
                orig = self.df[col].values
                nuevo_df[col] = list(orig[:len(nuevo_df)]) + [""] * max(0, len(nuevo_df) - len(orig))
        nuevo_df = nuevo_df.reindex(columns=self.df.columns)
        nuevo_df.to_csv(self.csv_path, index=False)  # Guardar en disco
        
        # 2. Llamar a tu función (asegúrate de que esté importada)
        from logic.graph import generar_grafo_flujo
        generar_grafo_flujo()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    ventana = VentanaEditarGrafo('src/data.csv')
    ventana.show()
    sys.exit(app.exec())