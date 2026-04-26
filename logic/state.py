import random
import pandas as pd
from logic.graph import generar_grafo_flujo
from dataclasses import dataclass, field
import pandas as pd

@dataclass
class AppState:
    """Almacena el estado global de la aplicación."""
    aristas_df: pd.DataFrame = field(default_factory=pd.DataFrame)
    edge_capacities: list = field(default_factory=list)

# Instancia única que será compartida
app_state = AppState()



class AppState:
    """
    Almacena y gestiona el estado compartido de la aplicación,
    similar a un servicio en Angular.
    """

    def __init__(self):
        self.settings = {}
        self.total_input_flow = 0
        self.edge_capacities = []  # Almacenará tuplas (min, max)
        self.num_genes = 0 # Cantidad de aristas que serán controladas por el AG

    def configurar_datos(self, configuracion, df_aristas):
        """
        Guarda la configuración y procesa los datos de las aristas de la tabla.

        Args:
            configuracion (dict): Diccionario con 'individuos', 'eficiencia', etc.
            df_aristas (pd.DataFrame): DataFrame con los datos de las aristas de la tabla.
        """
        self.settings = configuracion
        self.procesar_aristas(df_aristas)

    def procesar_aristas(self, df):
        """
        Calcula y almacena datos derivados del grafo/tabla.
        - Suma el flujo de las aristas de tipo ENTRADA.
        - Almacena las capacidades (mínima, máxima) de cada arista.
        - Cuenta el número de aristas para determinar la longitud de los cromosomas.
        """
        # Asegurarse de que las columnas sean numéricas
        df['FlujoEntrada'] = pd.to_numeric(df['FlujoEntrada'], errors='coerce').fillna(0)
        df['CapacidadMinima'] = pd.to_numeric(df['CapacidadMinima'], errors='coerce').fillna(0)
        df['CapacidadMaxima'] = pd.to_numeric(df['CapacidadMaxima'], errors='coerce').fillna(0)

        # 1. Suma de flujo de entrada
        input_edges_df = df[df['TipoArista'] == 'ENTRADA']
        self.total_input_flow = input_edges_df['FlujoEntrada'].sum()

        # 2. Arreglo con flujo máximo y mínimo por arista
        self.edge_capacities = list(zip(df['CapacidadMinima'], df['CapacidadMaxima']))
        
        # 3. Determinar el número de genes (longitud del cromosoma)
        #    Asumimos que cada arista es un gen.
        self.num_genes = len(df)


    def obtener_configuracion(self):
        return self.settings.copy()


# Instancia única que se compartirá en toda la aplicación
app_state = AppState()
