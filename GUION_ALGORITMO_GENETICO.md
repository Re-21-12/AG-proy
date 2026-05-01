# 🧬 Guion: Algoritmo Genético para Optimización de Semáforos

## 📌 Introducción

**¿Qué es el problema?**

Tenemos una red de intersecciones (nodos) conectadas por calles (aristas). Cada arista tiene un semáforo que controla el flujo de vehículos.

**El desafío:** Encontrar la configuración óptima de tiempos de semáforo para que **el máximo número de vehículos llegue a su destino** en el menor tiempo posible.

**¿Por qué un algoritmo genético?**

- El problema es **complejo y no lineal**: pequeños cambios en tiempos generan efectos grandes.
- No hay una fórmula directa para la solución óptima.
- El AG **explora muchas soluciones** simultáneamente (población) y evoluciona hacia mejores resultados.

---

## 🎯 Conceptos Clave

### 1. **Cromosoma (Individual)**

Representa una **configuración completa de semáforos**.

```
Cromosoma = [0.18, 0.16, 0.07, 0.01, 0.16, 0.0, 0.13, 0.19, 0.1]
            (Semáforo 1)(Semáforo 2)(Semáforo 3)...
```

- **Genes**: Cada número es el **porcentaje de tiempo** que ese semáforo está en verde (0 = rojo, 1 = siempre verde).
- **Restricción**: Todos los genes suman **1.0** (normalización).
- **Rango**: Cada gen está entre 0.0 y 1.0.

### 2. **Fitness (Evaluación)**

Mide qué tan **buena** es una configuración de semáforos.

```
Fitness = Número de vehículos que llegaron a su destino
```

**Ejemplo:**

- Configuración A → 24 vehículos llegan ✅
- Configuración B → 35 vehículos llegan ✅✅ (MEJOR)

El algoritmo **favorece a B** porque tiene mayor fitness.

### 3. **Población**

Un conjunto de **individuos (cromosomas)** que evolucionan juntos.

```
Generación 0:
- Individuo 1: [0.18, 0.16, 0.07, ...] → Fitness = 24
- Individuo 2: [0.12, 0.20, 0.08, ...] → Fitness = 18
- Individuo 3: [0.22, 0.14, 0.06, ...] → Fitness = 20
- ... (50 individuos en total)
```

---

## ⚙️ Proceso del Algoritmo (Paso a Paso)

### **Fase 1: Inicialización**

```
1. Crear 50 individuos aleatorios
2. Evaluar fitness de cada uno (simular tráfico con esos tiempos)
3. Registrar el mejor individual
```

**Log esperado:**

```
[INFO] AG inicializado | poblacion=50 genes=9 generaciones=100 aristas=9
[INFO] Población inicial creada: 50 individuos
[INFO] Estado inicial | mejor_fitness=24.0000 | individuo=Cromosoma: [0.18, 0.16, 0.07, ...] | Fitness: 24.0
```

---

### **Fase 2: Evolución (Bucle Principal)**

**Para cada generación (1 a 100):**

#### **A) Selección por Torneo**

Elegimos los individuos más aptos para reproducirse.

```
Torneo:
1. Seleccionar 3 individuos aleatorios
2. El con MAYOR fitness es elegido como "padre"
3. Repetir hasta tener 50 padres

Padres seleccionados:
- Padre 1: Fitness = 24 ✅
- Padre 2: Fitness = 20 ✅
- Padre 3: Fitness = 18
- ...
```

**Resultado:** Los mejores individuos tienen más probabilidad de reproducirse.

---

#### **B) Cruza (Recombinación)**

Los padres se "cruzan" para crear hijos con características de ambos.

```
Padre 1: [0.18, 0.16, 0.07, 0.01, 0.16, 0.0, 0.13, 0.19, 0.1]
Padre 2: [0.12, 0.20, 0.08, 0.02, 0.14, 0.1, 0.15, 0.18, 0.01]

Punto de cruza: Posición 4

Hijo 1:  [0.18, 0.16, 0.07, 0.01 | 0.14, 0.1, 0.15, 0.18, 0.01]
Hijo 2:  [0.12, 0.20, 0.08, 0.02 | 0.16, 0.0, 0.13, 0.19, 0.1]
         (Hereda del Padre 1) + (Hereda del Padre 2)
```

**Probabilidad:** 70% de cruza, 30% de copiar directamente.

---

#### **C) Mutación**

Introducimos **variación aleatoria** para explorar nuevas soluciones.

```
Individuo antes: [0.18, 0.16, 0.07, 0.01, 0.16, 0.0, 0.13, 0.19, 0.1]

Mutación en gen 3 (aumenta 0.05):
Individuo después: [0.18, 0.16, 0.12, 0.01, 0.16, 0.0, 0.13, 0.19, 0.05]
                                    ▲
                             Gene modificado
```

**Probabilidad:** 10% de que cada gen mute.

**Efecto:**

- Previene que la población se "atasque" en máximos locales.
- Permite descubrir nuevas soluciones.

---

#### **D) Evaluación de la Nueva Población**

Calculamos el fitness de todos los nuevos individuos.

```
Simulación de tráfico:
- Los vehículos intentan llegar a su destino
- Los tiempos de semáforo (genes) determinan velocidad
- Contar cuántos llegan exitosamente = Fitness
```

---

### **Fase 3: Mejora Progresiva**

Con cada generación, el algoritmo **evoluciona hacia mejores soluciones**.

```
Gen 1:   best_fitness = 24.0000  avg = 18.2400
Gen 10:  best_fitness = 24.0000  avg = 23.7000 ⬆️
Gen 20:  best_fitness = 24.0000  avg = 24.0000 ⬆️⬆️
Gen 40:  best_fitness = 26.7222  avg = 24.0544 ⬆️⬆️⬆️ (MEJORA ENCONTRADA!)
Gen 60:  best_fitness = 32.3468  avg = 24.7093 ⬆️⬆️⬆️
Gen 100: best_fitness = 35.6288  avg = 32.3046 ✅ (SOLUCIÓN FINAL)
```

**Interpretación:**

- `best_fitness`: El mejor individual encontrado hasta ahora.
- `avg`: Promedio de la población (convergencia).
- ⬆️ La población mejora en promedio → Convergencia exitosa.

---

## 📊 Componentes del Algoritmo (Código)

### 1. **Clase Individual**

```python
class Individual:
    def __init__(self, long_genes=0, genes=None):
        self.genes = [...]  # Lista de % de tiempo para cada semáforo
        self.fitness = 0    # Número de vehículos que llegaron
```

### 2. **Clase GeneticAlgorithm**

```python
class GeneticAlgorithm:
    def __init__(self, population_size=50, max_generations=100, ...):
        self.population = []      # Lista de individuos
        self.generation = 0       # Generación actual
        self.edges_list = [...]   # Aristas del grafo (semáforos)

    def evolve(self):
        """Ejecuta todas las generaciones"""
        while self.generation < self.max_generations:
            # Selección → Cruza → Mutación → Evaluación
```

### 3. **Flujo de Datos**

```
Grafo (CSV) → Individual (cromosoma) → Simulación de tráfico
                                           ↓
                                       Fitness
                                           ↓
                                    Selección/Cruza
                                           ↓
                                       Mutación
                                           ↓
                                    Nueva generación
```

---

## 🔬 Ejemplo Visual: Optimización Real

**Configuración MALA (Generación 1):**

```
Semáforos: [0.18, 0.16, 0.07, ...]
Tráfico: XXX → XX → X → X → 24 llegan ❌ (ineficiente)
```

**Configuración BUENA (Generación 100):**

```
Semáforos: [0.09, 0.06, 0.03, ...]
Tráfico: XXX → XXX → XXX → XXX → 35 llegan ✅ (optimizado!)
```

**¿Qué cambió?**

- Los semáforos se ajustaron para **minimizar congestiones**.
- Las rutas principales reciben más tiempo verde.
- Las rutas secundarias ceden tiempo.

---

## 📈 Resultados Esperados

**Ejecución típica:**

```
[INFO] Gen 1/100   | best_gen=24.0000 best_global=24.0000 avg=18.2400 worst=0.0000
[INFO] Gen 10/100  | best_gen=24.0000 best_global=24.0000 avg=23.7000 worst=9.0000
[INFO] Gen 20/100  | best_gen=24.0000 best_global=24.0000 avg=24.0000 worst=24.0000
[INFO] Gen 30/100  | best_gen=24.0000 best_global=24.0000 avg=24.0000 worst=24.0000
[INFO] MEJORA Gen 27 | nuevo_best=24.4246 | delta=+0.4246
[INFO] MEJORA Gen 33 | nuevo_best=25.4225 | delta=+0.9979
[INFO] MEJORA Gen 40 | nuevo_best=26.7222 | delta=+1.1488
[INFO] MEJORA Gen 88 | nuevo_best=35.6217 | delta=+0.1910
[INFO] Ejecucion finalizada | mejor_fitness=35.6288
[INFO] Mejor individuo final: Cromosoma: [0.09, 0.06, 0.03, ...] | Fitness: 35.6288
```

**Análisis:**

- ✅ Mejora encontrada en Gen 27 (+0.4246 vehículos más).
- ✅ Convergencia visible: Gen 30 onwards el promedio está cerca del mejor.
- ✅ Solución final: **35.6288 vehículos llegan** (vs 24 al inicio).
- ✅ **Mejora del 48%** en eficiencia.

---

## 🎓 Conclusión

**El Algoritmo Genético funciona como la evolución natural:**

1. **Población inicial** aleatoria (individuos con genes variados).
2. **Selección natural** (los más aptos se reproducen).
3. **Herencia** (hijos heredan genes de padres exitosos).
4. **Mutación** (variación permite explorar nuevas soluciones).
5. **Generaciones** (proceso repetido hasta encontrar optimización).

**Resultado:** Una configuración de semáforos que **maximiza el flujo de tráfico** sin conocer la solución de antemano.

---

## 💡 Preguntas para Profundizar

1. ¿Por qué no simplemente probar **todas las combinaciones** posibles?
   - Con 9 semáforos y valores continuos, hay **infinitas combinaciones**.
   - El AG en 100 generaciones encuentra buenas soluciones en milisegundos.

2. ¿Qué pasa si aumentamos la población a 100 individuos?
   - Más diversidad genética → Mejores soluciones, pero más lento.

3. ¿Y si aumentamos mutación al 50%?
   - Más exploración pero menos convergencia → Soluciones más aleatorias.

4. ¿Por qué el promedio no baja nunca?
   - Porque mantenemos a los mejores (`elitismo`) → La población **nunca retrocede**.

---

## 📚 Referencias Visuales

**Convergencia típica de un AG:**

```
Fitness
   |     ╱╲
   |    ╱  ╲ ╱╲    ╱╲
   |   ╱    ╲╱  ╲  ╱  ╲
   |  ╱           ╲╱
   |_╱__________________ Generaciones

Inicial        Mejoras         Convergencia
(Aleatorio)   (Exploración)   (Explotación)
```

**Distribución de población:**

```
Gen 1:   Muy dispersa (0-24 fitness)
   │
Gen 50:  Más concentrada (20-30 fitness)
   │
Gen 100: Muy concentrada (32-36 fitness) ✅
```

---

¡Listo para explicar a tu audiencia! 🎤
