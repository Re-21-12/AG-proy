import sys
from PyQt6.QtWidgets import QApplication
from ui.window import VentanaEditarGrafo
from ui.config_window import VentanaConfiguracion


if __name__ == "__main__":
    app = QApplication(sys.argv)

    estado: dict = {"config": None, "editor": None}

    def abrir_editor(configuracion):
        estado["config"].hide()
        estado["editor"] = VentanaEditarGrafo('src/data_case_1.csv', configuracion=configuracion)
        estado["editor"].show()

    estado["config"] = VentanaConfiguracion(on_continue=abrir_editor)
    estado["config"].show()

    sys.exit(app.exec())