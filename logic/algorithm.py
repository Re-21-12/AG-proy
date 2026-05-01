import random
from collections import deque

try:
    from logic.individual import Individual
    from logic.state import app_state
    from logic.logger_config import (
        setup_logger, log_initialization, log_graph_depth_computation,
        log_population_creation, log_population_stats, log_fitness_computation,
        log_fitness_result, log_selection, log_crossover, log_mutation,
        log_generation_summary, log_improvement, log_execution_start,
        log_initial_state, log_execution_end
    )
except ModuleNotFoundError:
    import os
    import sys

    # Permite ejecutar este archivo directamente: python logic/algorithm.py
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    from logic.individual import Individual
    from logic.state import app_state
    from logic.logger_config import (
        setup_logger, log_initialization, log_graph_depth_computation,
        log_population_creation, log_population_stats, log_fitness_computation,
        log_fitness_result, log_selection, log_crossover, log_mutation,
        log_generation_summary, log_improvement, log_execution_start,
        log_initial_state, log_execution_end
    )


class GeneticAlgorithm:
    DEFAULT_DEPTH_WITHOUT_ROOTS = 5
    FITNESS_DEBUG_CALLS = 3
    SELECTION_DEBUG_CALLS = 5
    MAX_MUTATION_TRANSFER = 0.1

    @staticmethod
    def _round_to_int(value: float) -> int:
        return int(float(value) + 0.5)

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
        self.logger = setup_logger(debug)
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
        log_initialization(
            self.logger,
            self.population_size,
            self.gene_count,
            self.max_generations,
            len(self.edges_list),
            0  # propagation_depth se calcula después
        )
        self.edge_capacities = app_state.edge_capacities

        # CORRECCIÓN #7: Calcular profundidad real del grafo para la propagación
        self._propagation_depth = self._compute_graph_depth()
        log_initialization(
            self.logger,
            self.population_size,
            self.gene_count,
            self.max_generations,
            len(self.edges_list),
            self._propagation_depth
        )

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
        log_generation_summary(
            self.logger, self.generation, self.max_generations,
            best, best_global_fitness, avg, worst, best_individual
        )

    # Algoritmo para calcular el flujo que puede pasar por una arista respetando sus capacidades y el flujo disponible de uno a otro nodo
    def _bounded_flow(self, edge_index: int, available_flow: float, gene_value: float) -> float:
        """
        Calcula el flujo que puede pasar por una arista respetando:
        capacidad minima <= flujo <= capacidad maxima.

        Si no se alcanza la capacidad minima, la arista no transfiere flujo.
        """
        cap_min, cap_max = self.edge_capacities[edge_index]
        cap_min = max(0.0, float(cap_min))
        cap_max = max(0.0, float(cap_max))

        if available_flow <= 0:
            return 0.0

        # Si max es 0, se interpreta como sin tope explicito para este paso.
        upper_bound = cap_max if cap_max > 0 else available_flow

        # Flujo propuesto por el gen dentro del limite superior.
        proposed = min(available_flow, upper_bound) * float(gene_value)

        # Restriccion por capacidad minima.
        if 0 < proposed < cap_min:
            proposed = cap_min

        # Nunca exceder ni lo disponible ni el maximo permitido.
        bounded = min(proposed, available_flow, upper_bound)
        if bounded < cap_min:
            return 0.0
        return float(self._round_to_int(bounded))

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

    def _effective_node_percentages(self, edge_indices: list[int], individual) -> dict[int, float]:
        """
        Obtiene los porcentajes efectivos de un nodo asegurando que la suma de
        sus salidas no supere 100%.
        """
        raw = []
        for edge_idx in edge_indices:
            p = float(individual.genes[edge_idx])
            raw.append(max(0.0, min(1.0, p)))

        total = sum(raw)
        if total > 1.0 and total > 0.0:
            raw = [p / total for p in raw]

        return {edge_idx: p for edge_idx, p in zip(edge_indices, raw)}

    def _allocate_node_outgoing_flows(
        self,
        available_flow: float,
        edge_indices: list[int],
        individual,
    ) -> dict[int, float]:
        """
        Reparte el flujo saliente de un nodo respetando:
        - Suma de porcentajes <= 100% (normalizados por nodo)
        - Prioridad por mayor capacidad mínima (DESC)
        - Para cada arista: proposed = remaining × gene%
          Si proposed < mínimo: asigna=0, remaining -= proposed
          Si proposed >= mínimo: asigna=proposed, remaining -= proposed
        - Nunca superar el flujo disponible del nodo
        """
        if available_flow <= 0 or not edge_indices:
            return {}

        available_int = float(self._round_to_int(available_flow))
        remaining = available_int
        flow_by_edge: dict[int, float] = {}

        effective_pct = self._effective_node_percentages(edge_indices, individual)

        # Primero satisfacer aristas más exigentes (mínimo más alto).
        priority_edges = sorted(
            edge_indices,
            key=lambda idx: float(self.edge_capacities[idx][0]),
            reverse=True,
        )

        for edge_idx in priority_edges:
            if remaining <= 0:
                break

            pct = effective_pct.get(edge_idx, 0.0)
            if pct <= 0:
                continue

            cap_min, cap_max = self.edge_capacities[edge_idx]
            cap_min = max(0.0, float(cap_min))
            cap_max = max(0.0, float(cap_max))

            # Calcular flujo propuesto basado en gene %
            proposed = remaining * pct
            proposed = float(self._round_to_int(proposed))

            # Respetar límite máximo
            upper_bound = cap_max if cap_max > 0 else remaining
            proposed = min(proposed, upper_bound)

            # Si no alcanza el mínimo, no asigna pero resta el propuesto del remaining
            if proposed < cap_min:
                remaining -= proposed
                continue

            # Si alcanza el mínimo, asigna y resta del remaining
            flow_by_edge[edge_idx] = proposed
            remaining -= proposed

        return flow_by_edge

    # algoritmo BFS para medir la profundiad de los nodos
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

        # ingresa a edges_list busca las aritas de origen si el tipo de arista es entrada es raiz
        roots = {e["NodoOrigen"] for e in self.edges_list if e["TipoArista"] == "ENTRADA"}
        
        if not roots:
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
        log_graph_depth_computation(self.logger, len(graph), roots, final_depth)
        return final_depth

    # Inicialización
    def _initialize_population(self):
        """Crea la población inicial.
        cada gen en el individuo representa un porcentaje de tiempo en cada semaforo """
        self.population = [Individual(long_genes=self.gene_count) for _ in range(self.population_size)]
        if self.population:
            log_population_creation(self.logger, len(self.population), self.population[0])

    # Evaluación de fitness
    def _evaluate_population(self):
        """Calcula el fitness (Flujo total en aristas de SALIDA)."""
        for individual in self.population:
            individual.fitness = self._compute_fitness(individual)
        if self.population:
            min_fit, avg_fit, max_fit = self._population_stats()
            log_population_stats(self.logger, min_fit, avg_fit, max_fit)

    # le pasa el individuo y a la clase misma
    def _compute_fitness(self, individual) -> float:
        fitness_total, _, _ = self._evaluate_flow(individual, capture_steps=False)
        return fitness_total

    def evaluate_with_trace(self, individual):
        """
        Evalúa un individuo y además devuelve los pasos intermedios del flujo.

        Returns:
            tuple[float, list[dict], dict]: fitness final, lista de frames y métricas.
        """
        return self._evaluate_flow(individual, capture_steps=True)

    def _evaluate_flow(self, individual, capture_steps: bool = False):
        """
        Calcula el flujo total que sale por las aristas de SALIDA.

        CORRECCIÓN #2: La propagación se realiza en orden topológico acumulando
        el flujo entrante a cada nodo de forma persistente entre pasos, de modo
        que nodos profundos del grafo reciban flujo correctamente.
        CORRECCIÓN #7: Se usa la profundidad real del grafo en lugar de 3 fijo.
        """
        total_edges = len(self.edges_list)
        current_flow_edges = [0.0] * total_edges
        frames = []
        self._fitness_calls += 1
        total_input_flow = 0.0

        # ── 1. Flujo de ENTRADA ────────────────────────────────────────────────
        for i, edge in enumerate(self.edges_list):
            if edge["TipoArista"] == "ENTRADA":
                flujo_entrada = float(edge.get("FlujoEntrada", 0))
                total_input_flow += flujo_entrada
                current_flow_edges[i] = self._bounded_flow(i, flujo_entrada, individual.genes[i])

        input_flows = [
            current_flow_edges[i]
            for i, e in enumerate(self.edges_list)
            if e["TipoArista"] == "ENTRADA"
        ]
        log_fitness_computation(self.logger, self._fitness_calls, total_edges, input_flows)

        if capture_steps:
            frames.append(
                {
                    "step": 0,
                    "label": "Entrada inicial",
                    "current_flow_edges": current_flow_edges.copy(),
                    "incoming_flows": {},
                    "genes": list(individual.genes),
                }
            )
        # ── 2. Propagación con flujo acumulado persistente ────────────────────
        # Acumulamos flujo_entrante_nodos entre iteraciones para que nodos
        # a varios saltos de la entrada reciban el flujo correcto.
        flujo_entrante_nodos: dict[str, float] = {}

        # Inicializar con el flujo que llega a partir de las ENTRADA
        for i, edge in enumerate(self.edges_list):
            dest = edge["NodoDestino"]
            flujo_entrante_nodos[dest] = flujo_entrante_nodos.get(dest, 0.0) + current_flow_edges[i]

        outgoing_non_input_by_node: dict[str, list[int]] = {}
        for i, edge in enumerate(self.edges_list):
            if edge["TipoArista"] != "ENTRADA":
                origen = edge["NodoOrigen"]
                outgoing_non_input_by_node.setdefault(origen, []).append(i)

        for _ in range(self._propagation_depth):
            # Snapshot del flujo entrante al inicio de este paso
            flujo_snap = dict(flujo_entrante_nodos)
            nuevos_flujos: dict[str, float] = {}

            for origen, flujo_disponible in flujo_snap.items():
                if flujo_disponible <= 0:
                    continue

                edge_indices = outgoing_non_input_by_node.get(origen, [])
                if not edge_indices:
                    continue

                flow_by_edge = self._allocate_node_outgoing_flows(
                    available_flow=flujo_disponible,
                    edge_indices=edge_indices,
                    individual=individual,
                )

                cedido_total = 0.0
                for edge_idx, flujo_a_pasar in flow_by_edge.items():
                    current_flow_edges[edge_idx] = flujo_a_pasar
                    cedido_total += flujo_a_pasar

                    dest = self.edges_list[edge_idx]["NodoDestino"]
                    flujo_entrante_nodos[dest] = flujo_entrante_nodos.get(dest, 0.0) + flujo_a_pasar

                if cedido_total > 0:
                    nuevos_flujos[origen] = nuevos_flujos.get(origen, 0.0) + cedido_total

            # Restar de cada origen lo que fue cedido en este paso
            for origen, cedido in nuevos_flujos.items():
                flujo_entrante_nodos[origen] = max(0.0, flujo_entrante_nodos.get(origen, 0.0) - cedido)

            if capture_steps:
                frames.append(
                    {
                        "step": len(frames),
                        "label": f"Propagación {len(frames)}",
                        "current_flow_edges": current_flow_edges.copy(),
                        "incoming_flows": dict(flujo_entrante_nodos),
                        "genes": list(individual.genes),
                    }
                )

        # ── 3. Sumar SALIDAS ───────────────────────────────────────────────────
        fitness_total = sum(
            current_flow_edges[i]
            for i, edge in enumerate(self.edges_list)
            if edge["TipoArista"] == "SALIDA"
        )
        fitness_total = self._round_to_int(fitness_total)
        total_input_flow = self._round_to_int(total_input_flow)
        efficiency = self._round_to_int((fitness_total / total_input_flow) * 100) if total_input_flow > 0 else 0
        log_fitness_result(self.logger, self._fitness_calls, fitness_total)
        if capture_steps:
            metrics = {
                "total_input_flow": total_input_flow,
                "total_output_flow": fitness_total,
                "efficiency_percent": efficiency,
            }
            return fitness_total, frames, metrics
        return fitness_total, None, {
            "total_input_flow": total_input_flow,
            "total_output_flow": fitness_total,
            "efficiency_percent": efficiency,
        }

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
            log_selection(self.logger, self._selection_calls)
            return selected

        pick = random.uniform(0, total_f)
        current = 0.0
        for ind, adj_f in zip(pool, adjusted):
            current += adj_f
            if current >= pick:
                log_selection(self.logger, self._selection_calls, pick, total_f, ind.fitness)
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
            log_crossover(self.logger, applied=True, point=point)
            return Individual(genes=child1_genes), Individual(genes=child2_genes)

        log_crossover(self.logger, applied=False)
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
        por individuo "una por gen con probabilidad mutation_prob", en lugar de
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

        log_mutation(self.logger, mutation_count)


    # Bucle principal

    def run(self):
        log_execution_start(self.logger)
        self._initialize_population()
        self._evaluate_population()

        global_best = self.get_best_individual().clone()
        log_initial_state(self.logger, global_best.fitness, global_best)

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
                log_improvement(self.logger, self.generation, global_best.fitness, delta, global_best)

            if self._should_log_generation():
                self._log_generation_summary(global_best.fitness, best_individual)

        result = global_best
        log_execution_end(self.logger, result.fitness, result)
        return result

    # ─────────────────────────────────────────────────────────────────────────────
    # Utilidades
    # ─────────────────────────────────────────────────────────────────────────────
    def get_best_individual(self):
        return max(self.population, key=lambda ind: ind.fitness)