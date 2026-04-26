import random
from logic.individual import Individual
from logic.state import app_state


class GeneticAlgorithm:
    def __init__(
        self,
        population_size=20,
        gene_count=10,
        crossover_prob=0.7,
        mutation_prob=0.1,
        max_generations=100,
    ):
        # Aseguramos que la población sea par para el cruce por parejas
        self.population_size = population_size if population_size % 2 == 0 else population_size + 1
        self.gene_count = gene_count
        self.crossover_prob = crossover_prob
        self.mutation_prob = mutation_prob
        self.max_generations = max_generations
        self.population = []
        self.generation = 0

        # Optimización: Convertir DF a lista para acceso rápido en el bucle de fitness
        self.edges_list = app_state.aristas_df.to_dict("records")
        self.edge_capacities = app_state.edge_capacities

        # CORRECCIÓN #7: Calcular profundidad real del grafo para la propagación
        self._propagation_depth = self._compute_graph_depth()

    # ─────────────────────────────────────────────────────────────────────────────
    # CORRECCIÓN #7: Calcular profundidad del grafo basada en su topología
    # ─────────────────────────────────────────────────────────────────────────────
    def _compute_graph_depth(self) -> int:
        """
        Calcula la profundidad máxima del grafo (número de niveles de nodos)
        mediante BFS desde los nodos de entrada.
        Garantiza que la propagación cubra todos los niveles.
        """
        # Construir lista de adyacencia
        graph = {}
        for edge in self.edges_list:
            src = edge["NodoOrigen"]
            dst = edge["NodoDestino"]
            graph.setdefault(src, []).append(dst)

        # Nodos raíz = nodos que aparecen en aristas de ENTRADA
        roots = {e["NodoOrigen"] for e in self.edges_list if e["TipoArista"] == "ENTRADA"}

        if not roots:
            return 5  # Valor por defecto si no hay nodos de entrada definidos

        # BFS para calcular la profundidad máxima
        visited = {}
        queue = [(root, 0) for root in roots]
        while queue:
            node, depth = queue.pop(0)
            if node in visited and visited[node] >= depth:
                continue
            visited[node] = depth
            for neighbor in graph.get(node, []):
                queue.append((neighbor, depth + 1))

        max_depth = max(visited.values(), default=3)
        # Al menos 1 iteración, sin acotar arbitrariamente
        return max(1, max_depth)

    # ─────────────────────────────────────────────────────────────────────────────
    # Inicialización
    # ─────────────────────────────────────────────────────────────────────────────
    def _initialize_population(self):
        """Crea la población inicial."""
        self.population = [Individual(long_genes=self.gene_count) for _ in range(self.population_size)]

    # ─────────────────────────────────────────────────────────────────────────────
    # Evaluación de fitness
    # ─────────────────────────────────────────────────────────────────────────────
    def _evaluate_population(self):
        """Calcula el fitness (Flujo total en aristas de SALIDA)."""
        for individual in self.population:
            individual.fitness = self._compute_fitness(individual)

    def _compute_fitness(self, individual) -> float:
        """
        Calcula el flujo total que sale por las aristas de SALIDA.

        CORRECCIÓN #2: La propagación se realiza en orden topológico acumulando
        el flujo entrante a cada nodo de forma persistente entre pasos, de modo
        que nodos profundos del grafo reciban flujo correctamente.
        CORRECCIÓN #7: Se usa la profundidad real del grafo en lugar de 3 fijo.
        """
        n = len(self.edges_list)
        current_flow_edges = [0.0] * n

        # ── 1. Flujo de ENTRADA ────────────────────────────────────────────────
        for i, edge in enumerate(self.edges_list):
            if edge["TipoArista"] == "ENTRADA":
                flujo_entrada = float(edge.get("FlujoEntrada", 0))
                cap_max = self.edge_capacities[i][1]
                max_cap = cap_max if cap_max > 0 else flujo_entrada
                initial_flow = min(flujo_entrada, max_cap)
                current_flow_edges[i] = initial_flow * individual.genes[i]

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
        return round(fitness_total, 4)

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

        min_f = min(ind.fitness for ind in pool)
        # Desplazar para que todos sean >= 0 (maneja fitness negativos)
        offset = max(0.0, -min_f)
        adjusted = [ind.fitness + offset for ind in pool]
        total_f = sum(adjusted)

        if total_f == 0:
            return random.choice(pool)

        pick = random.uniform(0, total_f)
        current = 0.0
        for ind, adj_f in zip(pool, adjusted):
            current += adj_f
            if current >= pick:
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
            return Individual(genes=child1_genes), Individual(genes=child2_genes)

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

        for idx1 in range(len(genes)):
            if random.random() >= self.mutation_prob:
                continue

            # Elegir un segundo gen distinto al azar
            idx2 = random.choice([j for j in range(len(genes)) if j != idx1])

            # Cantidad máxima que se puede transferir sin violar [0, 1]
            max_cambio = min(genes[idx1], 1.0 - genes[idx2], 0.1)
            if max_cambio <= 0:
                continue

            cantidad = round(random.uniform(0.01, max_cambio), 2)

            genes[idx1] = max(0.0, round(genes[idx1] - cantidad, 2))
            genes[idx2] = min(1.0, round(genes[idx2] + cantidad, 2))  # CORRECCIÓN #1

    # ─────────────────────────────────────────────────────────────────────────────
    # Bucle principal
    # ─────────────────────────────────────────────────────────────────────────────
    def run(self):
        self._initialize_population()
        self._evaluate_population()

        for _ in range(self.max_generations):
            # ELITISMO: Guardamos al mejor antes de alterar la población.
            # CORRECCIÓN #6: El clon ya carga el fitness calculado, por lo que
            # no es necesario re-evaluarlo al insertarlo en la nueva generación.
            best_ind = self.get_best_individual().clone()

            new_population = []

            # Crear nueva generación por parejas
            for _ in range(self.population_size // 2):
                # CORRECCIÓN #4: Selección de padres distintos
                p1 = self._select_individual()
                p2 = self._select_individual(exclude=p1)

                c1, c2 = self._crossover(p1, p2)

                self._mutate(c1)
                self._mutate(c2)

                new_population.extend([c1, c2])

            self.population = new_population
            self._evaluate_population()

            # Elitismo: Reemplazar al peor con el mejor de la generación anterior
            peor_idx = self.population.index(min(self.population, key=lambda x: x.fitness))
            self.population[peor_idx] = best_ind  # fitness ya válido (CORRECCIÓN #6)

            self.generation += 1
            if self.generation % 10 == 0:
                print(f"Gen {self.generation} | Mejor Fitness: {self.get_best_individual().fitness}")

        return self.get_best_individual()

    # ─────────────────────────────────────────────────────────────────────────────
    # Utilidades
    # ─────────────────────────────────────────────────────────────────────────────
    def get_best_individual(self):
        return max(self.population, key=lambda ind: ind.fitness)