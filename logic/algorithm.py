import random
import logging
from collections import deque

try:
    from logic.individual import Individual
    from logic.state import app_state
except ModuleNotFoundError:
    import os
    import sys

    # Permite ejecutar este archivo directamente: python logic/algorithm.py
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    from logic.individual import Individual
    from logic.state import app_state


class GeneticAlgorithm:
    DEFAULT_DEPTH_WITHOUT_ROOTS = 5
    FITNESS_DEBUG_CALLS = 3
    SELECTION_DEBUG_CALLS = 5
    MAX_MUTATION_TRANSFER = 0.1

    def __init__(
        self,
        population_size=20,
        gene_count=10,
        crossover_prob=0.7,
        mutation_prob=0.1,
        max_generations=100,
        debug=False,
        log_every=10,
    ):
        self.logger = self._setup_logger(debug)
        # Aseguramos que la población sea par para el cruce por parejas
        self.population_size = population_size if population_size % 2 == 0 else population_size + 1
        self.gene_count = gene_count
        self.crossover_prob = crossover_prob
        self.mutation_prob = mutation_prob
        self.max_generations = max_generations
        self.log_every = max(1, int(log_every))
        self.population = []
        self.generation = 0
        self._fitness_calls = 0
        self._selection_calls = 0

        # Optimización: Convertir DF a lista para acceso rápido en el bucle de fitness
        self.edges_list = app_state.aristas_df.to_dict("records")
        self.logger.info(
            "AG inicializado | poblacion=%s genes=%s generaciones=%s aristas=%s",
            self.population_size,
            self.gene_count,
            self.max_generations,
            len(self.edges_list),
        )
        self.edge_capacities = app_state.edge_capacities

        # CORRECCIÓN #7: Calcular profundidad real del grafo para la propagación
        self._propagation_depth = self._compute_graph_depth()
        self.logger.info("Profundidad del grafo calculada: %s", self._propagation_depth)

    def _population_stats(self):
        if not self.population:
            return 0.0, 0.0, 0.0
        fitness_values = [ind.fitness for ind in self.population]
        avg_fit = sum(fitness_values) / len(fitness_values)
        return min(fitness_values), avg_fit, max(fitness_values)

    def _should_log_generation(self):
        return (
            self.generation == 1
            or self.generation % self.log_every == 0
            or self.generation == self.max_generations
        )

    def _log_generation_summary(self, best_global_fitness: float, best_individual):
        worst, avg, best = self._population_stats()
        self.logger.info(
            "Gen %s/%s | best_gen=%.4f best_global=%.4f avg=%.4f worst=%.4f",
            self.generation,
            self.max_generations,
            best,
            best_global_fitness,
            avg,
            worst,
        )
        self.logger.debug("Mejor individuo actual: %s", best_individual)

    def _create_next_generation(self):
        new_population = []
        for _ in range(self.population_size // 2):
            p1 = self._select_individual()
            p2 = self._select_individual(exclude=p1)
            c1, c2 = self._crossover(p1, p2)
            self._mutate(c1)
            self._mutate(c2)
            new_population.extend([c1, c2])
        return new_population

    def _setup_logger(self, debug: bool) -> logging.Logger:
        logger = logging.getLogger("genetic_algorithm")
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter("[%(levelname)s][AG] %(message)s")
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        logger.setLevel(logging.DEBUG if debug else logging.INFO)
        logger.propagate = False
        return logger

    # CORRECCIÓN #7: Calcular profundidad del grafo basada en su topología
    def _compute_graph_depth(self) -> int:
        """
        Calcula la profundidad máxima del grafo (número de niveles de nodos)
        mediante BFS desde los nodos de entrada. Breath First Search (BFS) 
        """
        # Construir lista de adyacencia
        graph = {}
        for edge in self.edges_list:
            src = edge["NodoOrigen"]
            dst = edge["NodoDestino"]
            graph.setdefault(src, []).append(dst)

        self.logger.debug("Adyacencia construida con %s nodos origen.", len(graph))

        # ingresa a edges_list busca las aritas de origen si el tipo de arista es entrada es raiz
        roots = {e["NodoOrigen"] for e in self.edges_list if e["TipoArista"] == "ENTRADA"}
        self.logger.debug("Nodos raiz detectados: %s", sorted(roots))

        if not roots:
            self.logger.warning(
                "No se detectaron aristas ENTRADA; se usa profundidad por defecto=%s.",
                self.DEFAULT_DEPTH_WITHOUT_ROOTS,
            )
            return self.DEFAULT_DEPTH_WITHOUT_ROOTS

        # BFS para calcular la profundidad máxima
        visited = {}
        queue = deque((root, 0) for root in roots)
        while queue:
            node, depth = queue.popleft()
            if node in visited and visited[node] >= depth:
                continue
            visited[node] = depth
            for neighbor in graph.get(node, []):
                queue.append((neighbor, depth + 1))

        max_depth = max(visited.values(), default=3)
        final_depth = max(1, max_depth)
        self.logger.debug("Profundidad BFS maxima=%s", final_depth)
        return final_depth

    # Inicialización
    def _initialize_population(self):
        """Crea la población inicial.
        cada gen en el individuo representa un porcentaje de tiempo en cada semaforo """
        self.population = [Individual(long_genes=self.gene_count) for _ in range(self.population_size)]
        if self.population:
            self.logger.info("Poblacion inicial creada: %s individuos", len(self.population))
            self.logger.debug("Primer individuo: %s", self.population[0])

    # Evaluación de fitness
    def _evaluate_population(self):
        """Calcula el fitness (Flujo total en aristas de SALIDA)."""
        for individual in self.population:
            individual.fitness = self._compute_fitness(individual)
        if self.population:
            min_fit, avg_fit, max_fit = self._population_stats()
            self.logger.debug(
                "Fitness poblacion | min=%.4f avg=%.4f max=%.4f",
                min_fit,
                avg_fit,
                max_fit,
            )

# le pasa el individuo y a la clase misma
    def _compute_fitness(self, individual) -> float:
        """
        Calcula el flujo total que sale por las aristas de SALIDA.

        CORRECCIÓN #2: La propagación se realiza en orden topológico acumulando
        el flujo entrante a cada nodo de forma persistente entre pasos, de modo
        que nodos profundos del grafo reciban flujo correctamente.
        CORRECCIÓN #7: Se usa la profundidad real del grafo en lugar de 3 fijo.
        """
        total_edges = len(self.edges_list)
        current_flow_edges = [0.0] * total_edges
        self._fitness_calls += 1

        # ── 1. Flujo de ENTRADA ────────────────────────────────────────────────
        for i, edge in enumerate(self.edges_list):
            if edge["TipoArista"] == "ENTRADA":
                flujo_entrada = float(edge.get("FlujoEntrada", 0))
                cap_max = self.edge_capacities[i][1]
                max_cap = cap_max if cap_max > 0 else flujo_entrada
                initial_flow = min(flujo_entrada, max_cap)
                current_flow_edges[i] = initial_flow * individual.genes[i]

        if self._fitness_calls <= self.FITNESS_DEBUG_CALLS:
            input_flows = [
                current_flow_edges[i]
                for i, e in enumerate(self.edges_list)
                if e["TipoArista"] == "ENTRADA"
            ]
            self.logger.debug(
                "Fitness call #%s | total_aristas=%s | flujos_entrada=%s",
                self._fitness_calls,
                total_edges,
                input_flows,
            )
        # ── 2. Propagación con flujo acumulado persistente ────────────────────
        # Acumulamos flujo_entrante_nodos entre iteraciones para que nodos
        # a varios saltos de la entrada reciban el flujo correcto.
        flujo_entrante_nodos: dict[str, float] = {}

        # Inicializar con el flujo que llega a partir de las ENTRADA
        for i, edge in enumerate(self.edges_list):
            dest = edge["NodoDestino"]
            flujo_entrante_nodos[dest] = flujo_entrante_nodos.get(dest, 0.0) + current_flow_edges[i]

        for _ in range(self._propagation_depth):
            # Snapshot del flujo entrante al inicio de este paso
            flujo_snap = dict(flujo_entrante_nodos)
            nuevos_flujos: dict[str, float] = {}

            for i, edge in enumerate(self.edges_list):
                if edge["TipoArista"] == "ENTRADA":
                    continue

                origen = edge["NodoOrigen"]
                flujo_disponible = flujo_snap.get(origen, 0.0)
                if flujo_disponible <= 0:
                    continue

                cap_max = self.edge_capacities[i][1]
                flujo_a_pasar = min(flujo_disponible, cap_max) * individual.genes[i]
                current_flow_edges[i] = flujo_a_pasar

                # Acumular lo que este nodo consume (para no ceder más de lo disponible)
                nuevos_flujos[origen] = nuevos_flujos.get(origen, 0.0) + flujo_a_pasar

                # El nodo destino recibe este flujo
                dest = edge["NodoDestino"]
                flujo_entrante_nodos[dest] = flujo_entrante_nodos.get(dest, 0.0) + flujo_a_pasar

            # Restar de cada origen lo que fue cedido en este paso
            for origen, cedido in nuevos_flujos.items():
                flujo_entrante_nodos[origen] = max(0.0, flujo_entrante_nodos.get(origen, 0.0) - cedido)

        # ── 3. Sumar SALIDAS ───────────────────────────────────────────────────
        fitness_total = sum(
            current_flow_edges[i]
            for i, edge in enumerate(self.edges_list)
            if edge["TipoArista"] == "SALIDA"
        )
        fitness_total = round(fitness_total, 4)
        if self._fitness_calls <= self.FITNESS_DEBUG_CALLS:
            self.logger.debug("Fitness call #%s resultado=%.4f", self._fitness_calls, fitness_total)
        return fitness_total

    # ─────────────────────────────────────────────────────────────────────────────
    # Selección
    # ─────────────────────────────────────────────────────────────────────────────
    def _select_individual(self, exclude=None):
        """
        Selección por Ruleta (Proporcional).

        CORRECCIÓN #3: Se desplazan los fitness al rango positivo antes de
        construir la ruleta, evitando comportamiento incorrecto con valores
        negativos o todos iguales.
        CORRECCIÓN #4: Parámetro `exclude` para garantizar que los dos padres
        seleccionados para cruce sean distintos, preservando diversidad genética.
        """
        pool = [ind for ind in self.population if ind is not exclude] or self.population
        self._selection_calls += 1

        min_f = min(ind.fitness for ind in pool)
        # Desplazar para que todos sean >= 0 (maneja fitness negativos)
        offset = max(0.0, -min_f)
        adjusted = [ind.fitness + offset for ind in pool]
        total_f = sum(adjusted)

        if total_f == 0:
            selected = random.choice(pool)
            if self._selection_calls <= self.SELECTION_DEBUG_CALLS:
                self.logger.debug("Seleccion #%s por azar (fitness total=0)", self._selection_calls)
            return selected

        pick = random.uniform(0, total_f)
        current = 0.0
        for ind, adj_f in zip(pool, adjusted):
            current += adj_f
            if current >= pick:
                if self._selection_calls <= self.SELECTION_DEBUG_CALLS:
                    self.logger.debug(
                        "Seleccion #%s | pick=%.4f total=%.4f fitness_sel=%.4f",
                        self._selection_calls,
                        pick,
                        total_f,
                        ind.fitness,
                    )
                return ind
        return pool[-1]

    # ─────────────────────────────────────────────────────────────────────────────
    # Cruce
    # ─────────────────────────────────────────────────────────────────────────────
    def _crossover(self, parent1, parent2):
        """
        Cruce de un punto.

        CORRECCIÓN #8: Se valida que genes sea lista para garantizar que el
        slicing funcione correctamente independientemente del tipo original.
        """
        g1 = list(parent1.genes)
        g2 = list(parent2.genes)

        if random.random() < self.crossover_prob:
            point = random.randint(1, self.gene_count - 1)
            child1_genes = g1[:point] + g2[point:]
            child2_genes = g2[:point] + g1[point:]
            self.logger.debug("Cruce aplicado en punto=%s", point)
            return Individual(genes=child1_genes), Individual(genes=child2_genes)

        self.logger.debug("Cruce omitido por probabilidad")
        return parent1.clone(), parent2.clone()

    # ─────────────────────────────────────────────────────────────────────────────
    # Mutación
    # ─────────────────────────────────────────────────────────────────────────────

    def _mutate(self, individual):
        """
        Mutación que mantiene la integridad de los genes en el rango [0, 1].

        CORRECCIÓN #1: Se añade `min(1, ...)` en genes[idx2] para garantizar
        que ningún gen supere 1.0 tras la mutación.
        CORRECCIÓN #5: Se amplía la diversidad permitiendo múltiples mutaciones
        por individuo (una por gen con probabilidad mutation_prob), en lugar de
        limitarse siempre a exactamente 2 genes.
        """
        genes = individual.genes
        mutation_count = 0

        for idx1 in range(len(genes)):
            if random.random() >= self.mutation_prob:
                continue

            idx2 = random.choice([j for j in range(len(genes)) if j != idx1])
            
            # CUMPLIMIENTO: Obtener el límite mínimo de la tabla para el gen idx1
            # Calculamos el ratio mínimo: CapacidadMinima / CapacidadMaxima
            cap_min = self.edge_capacities[idx1][0]
            cap_max = self.edge_capacities[idx1][1]
            min_permitido = (cap_min / cap_max) if cap_max > 0 else 0.0

            # Cantidad máxima que se puede quitar a idx1 sin bajar del mínimo permitido
            max_disponible_para_quitar = max(0.0, genes[idx1] - min_permitido)
            
            # Cantidad máxima que puede recibir idx2 sin pasarse de 1.0
            max_espacio_en_idx2 = max(0.0, 1.0 - genes[idx2])
            
            max_cambio = min(max_disponible_para_quitar, max_espacio_en_idx2, self.MAX_MUTATION_TRANSFER)
            
            if max_cambio <= 0.01:
                continue

            cantidad = round(random.uniform(0.01, max_cambio), 2)

            genes[idx1] = max(min_permitido, round(genes[idx1] - cantidad, 2)) # Respeta el mínimo
            genes[idx2] = min(1.0, round(genes[idx2] + cantidad, 2))
            mutation_count += 1

            if mutation_count > 0:
                self.logger.debug("Mutaciones aplicadas en individuo: %s", mutation_count)

    # ─────────────────────────────────────────────────────────────────────────────
    # Bucle principal
    # ─────────────────────────────────────────────────────────────────────────────
    def run(self):
        self.logger.info("Inicio de ejecucion del AG")
        self._initialize_population()
        self._evaluate_population()

        global_best = self.get_best_individual().clone()
        self.logger.info(
            "Estado inicial | mejor_fitness=%.4f | individuo=%s",
            global_best.fitness,
            global_best,
        )

        for _ in range(self.max_generations):
            # ELITISMO: Guardamos al mejor antes de alterar la población.
            # CORRECCIÓN #6: El clon ya carga el fitness calculado, por lo que
            # no es necesario re-evaluarlo al insertarlo en la nueva generación.
            best_ind = self.get_best_individual().clone()

            new_population = self._create_next_generation()

            self.population = new_population
            self._evaluate_population()

            # Elitismo: Reemplazar al peor con el mejor de la generación anterior
            peor_idx = self.population.index(min(self.population, key=lambda x: x.fitness))
            self.population[peor_idx] = best_ind  # fitness ya válido (CORRECCIÓN #6)

            self.generation += 1
            best_individual = self.get_best_individual()

            if best_individual.fitness > global_best.fitness:
                delta = best_individual.fitness - global_best.fitness
                global_best = best_individual.clone()
                self.logger.info(
                    "MEJORA Gen %s | nuevo_best=%.4f | delta=+%.4f | individuo=%s",
                    self.generation,
                    global_best.fitness,
                    delta,
                    global_best,
                )

            if self._should_log_generation():
                self._log_generation_summary(global_best.fitness, best_individual)

        result = global_best
        self.logger.info("Ejecucion finalizada | mejor_fitness=%.4f", result.fitness)
        self.logger.info("Mejor individuo final: %s", result)
        return result

    # ─────────────────────────────────────────────────────────────────────────────
    # Utilidades
    # ─────────────────────────────────────────────────────────────────────────────
    def get_best_individual(self):
        return max(self.population, key=lambda ind: ind.fitness)