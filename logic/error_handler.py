import logging
import traceback
from datetime import datetime

def setup_logging():
    """Configura el sistema de logging para guardar errores en un archivo."""
    logging.basicConfig(
        filename='error.log',
        level=logging.ERROR,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

def log_error(exc_type, exc_value, exc_traceback):
    """Registra una excepción no controlada en el archivo de log."""
    if issubclass(exc_type, KeyboardInterrupt):
        # No registrar interrupciones de teclado por parte del usuario
        return
    
    tb_lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
    error_message = "".join(tb_lines)
    
    logging.error(f"Excepción no controlada:\n{error_message}")
    
    # Opcional: También puedes imprimir un mensaje a la consola
    print(f"Se ha producido un error. Consulta error.log para más detalles.")
