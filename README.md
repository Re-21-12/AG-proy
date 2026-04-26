# AG-proy

Proyecto de optimización de flujo vehicular en una red vial modelada como grafo dirigido, usando un algoritmo genético (AG).

## ¿Qué hace el proyecto?

La aplicación permite:

1. Configurar parámetros del AG (generaciones, individuos y eficiencia desde UI).
2. Editar un grafo de tránsito desde una tabla (nodos, aristas, capacidades y flujo de entrada).
3. Visualizar el grafo con codificación por tipo de arista:
   - ENTRADA (rojo)
   - INTERMEDIO (negro)
   - SALIDA (azul)
4. Ejecutar un AG para encontrar una configuración de semáforos que maximice el flujo total que llega a las salidas.

## Estructura principal

- `main.py`: arranque de la app PyQt6.
- `ui/config_window.py`: ventana inicial para configurar ejecución.
- `ui/window.py`: editor de tabla del grafo, preview y ejecución del AG.
- `logic/algorithm.py`: implementación del algoritmo genético.
- `logic/individual.py`: definición del individuo/cromosoma.
- `logic/graph.py`: visualización del grafo con `networkx` + `matplotlib`.
- `src/data.csv`: datos del grafo.

## ¿Cómo funciona el algoritmo genético?

La implementación está en `logic/algorithm.py` y sigue este flujo:

1. Inicialización de población
   - Se crean `N` individuos.
   - Cada individuo tiene un cromosoma de longitud igual al número de aristas (`gene_count`).
   - Cada gen representa proporción de paso (tiempo/prioridad) en la arista correspondiente.

2. Evaluación (función de utilidad / fitness)
   - Se simula propagación de flujo en el grafo respetando capacidades máximas.
   - El fitness se define como:

$$
fitness = \sum_{e \in SALIDA} flujo_e
$$

    - Objetivo: maximizar el flujo total que sale por aristas de tipo `SALIDA`.

3. Selección de padres
   - Se usa **selección por ruleta (proporcional al fitness)**.
   - Si hay fitness negativos, se desplazan al rango no negativo antes de construir la ruleta.
   - Se fuerza que los dos padres de una pareja sean distintos (`exclude`) para mantener diversidad.

4. Cruzamiento
   - Se usa **cruce de un punto** con probabilidad `crossover_prob`.
   - Si no ocurre cruce, los hijos son clones de los padres.

5. Mutación
   - Para cada gen, con probabilidad `mutation_prob`, se transfiere una pequeña cantidad a otro gen.
   - Se mantiene la validez de genes en el rango `[0, 1]`.
   - Esto incrementa exploración y evita estancamiento prematuro.

6. Reemplazo y elitismo
   - Se crea nueva generación por parejas de hijos.
   - Se reevalúa la población.
   - Se aplica **elitismo**: el mejor individuo previo reemplaza al peor de la nueva generación.

7. Resultado
   - Tras `max_generations`, se devuelve el mejor individuo encontrado.

## Operadores usados y aplicación en este problema

### Selección (ruleta)

Aplicación: favorecer configuraciones de semáforos que ya muestran mayor flujo de salida, sin descartar del todo soluciones menos aptas.

### Cruzamiento (1 punto)

Aplicación: combinar segmentos de dos planes de semaforización para mezclar buenas decisiones locales en distintos tramos de la red.

### Mutación (transferencia entre genes)

Aplicación: ajustar finamente el reparto de prioridad/tiempo entre aristas para descubrir mejoras que el cruce no alcanza.

### Función de utilidad (fitness)

Aplicación: medir de forma directa el rendimiento operativo de la red, maximizando vehículos evacuados por salidas.

## Ejemplo práctico de interpretación

Supón un grafo simple con estas aristas:

| NodoOrigen | NodoDestino | TipoArista | CapacidadMinima | CapacidadMaxima | FlujoEntrada |
| ---------- | ----------- | ---------- | --------------- | --------------- | ------------ |
| n0         | n1          | ENTRADA    | 0               | 100             | 80           |
| n1         | n2          | INTERMEDIO | 0               | 60              | 0            |
| n1         | n3          | INTERMEDIO | 0               | 40              | 0            |
| n2         | n4          | SALIDA     | 0               | 60              | 0            |
| n3         | n5          | SALIDA     | 0               | 40              | 0            |

Si el mejor individuo termina con genes aproximados como:

- [1.0, 0.7, 0.3, 1.0, 1.0]

Se puede interpretar así:

1. La arista de entrada usa el 100% del flujo disponible.
2. Desde n1, el AG prioriza más la rama hacia n2 (0.7) que hacia n3 (0.3).
3. Las aristas de salida permiten descargar totalmente lo que llega a cada rama (según capacidad).

En este caso, el fitness será la suma de flujo en las aristas SALIDA. Un valor más alto de fitness implica mejor evacuación de vehículos en la red.

Consejo práctico:

- Si una salida se satura rápido por su capacidad máxima, el AG tenderá a redistribuir flujo hacia otras rutas durante generaciones posteriores.

## Nota importante

El parámetro `eficiencia` se captura en la UI de configuración, pero actualmente no se usa dentro del cálculo de fitness ni en criterios de parada del AG. En su estado actual, el objetivo de optimización depende del flujo en `SALIDA` y de las capacidades del grafo.

## Ejecución

1. Crear/activar entorno virtual.
2. Instalar dependencias (`PyQt6`, `pandas`, `networkx`, `matplotlib`).
3. Ejecutar:

```bash
python main.py
```
