from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QFormLayout,
    QSpinBox,
    QDoubleSpinBox,
    QPushButton,
    QMessageBox,
)


class VentanaConfiguracion(QMainWindow):
    def __init__(self, on_continue):
        super().__init__()
        self.on_continue = on_continue

        self.setWindowTitle("Configuración del sistema")
        self.resize(420, 220)

        contenedor = QWidget()
        self.setCentralWidget(contenedor)

        layout = QVBoxLayout(contenedor)
        form = QFormLayout()
        layout.addLayout(form)

        self.spn_generaciones = QSpinBox()
        self.spn_generaciones.setRange(1, 1_000_000)
        self.spn_generaciones.setValue(100)

        self.spn_eficiencia = QDoubleSpinBox()
        self.spn_eficiencia.setRange(0.0, 100.0)
        self.spn_eficiencia.setDecimals(2)
        self.spn_eficiencia.setSingleStep(0.5)
        self.spn_eficiencia.setValue(90.0)
        self.spn_eficiencia.setSuffix(" %")

        self.spn_individuos = QSpinBox()
        self.spn_individuos.setRange(1, 1_000_000)
        self.spn_individuos.setValue(50)

        form.addRow("# de generaciones a estimar", self.spn_generaciones)
        form.addRow("Porcentaje de eficiencia", self.spn_eficiencia)
        form.addRow("# de individuos ", self.spn_individuos)

        self.btn_continuar = QPushButton("Continuar")
        self.btn_continuar.clicked.connect(self.continuar)
        layout.addWidget(self.btn_continuar)

    def continuar(self):
        configuracion = {
            "generaciones": int(self.spn_generaciones.value()),
            "eficiencia": float(self.spn_eficiencia.value()),
            "individuos": int(self.spn_individuos.value()),
        }

        if configuracion["generaciones"] <= 0 or configuracion["individuos"] <= 0:
            QMessageBox.warning(self, "Datos inválidos", "Generaciones e individuos deben ser mayores a 0.")
            return

        if configuracion["eficiencia"] < 0 or configuracion["eficiencia"] > 100:
            QMessageBox.warning(self, "Datos inválidos", "La eficiencia debe estar entre 0 y 100.")
            return

        self.on_continue(configuracion)
