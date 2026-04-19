import random
from logic.individual import Individual
from logic.state import app_state # Importar el estado de la aplicación

class GeneticAlgorithm:
    minProb = 0.1
    maxProb = 1.0
    def __init__(self, population_size=20, gene_count=10, crossover_prob=0.7, mutation_prob=0.01, max_generations=100):
        self.population_size = population_size
        self.gene_count = gene_count
        self.crossover_prob = crossover_prob
        self.mutation_prob = mutation_prob
        self.max_generations = max_generations
        self.population = []
        self.generation = 0

    def _initialize_population(self):
        """Crea la población inicial."""
        self.population = [Individual(long_genes=self.gene_count) for _ in range(self.population_size)]

    def _select_individual(self):
        """Selecciona un individuo de la población (selección aleatoria simple)."""
        return random.choice(self.population)

    def _crossover(self, parent1, parent2):
        """Realiza un cruce de un solo punto entre dos padres."""
        point = random.randint(1, self.gene_count - 1)
        child1_genes = parent1.genes[:point] + parent2.genes[point:]
        child2_genes = parent2.genes[:point] + parent1.genes[point:]
        return Individual(genes=child1_genes), Individual(genes=child2_genes)

    def _mutate(self, individual):
        """Muta los genes de un individuo basado en la probabilidad de mutación."""
        # La mutación debe ser inteligente para mantener la suma de los genes en 1.0
        if random.random() < self.mutation_prob:
            # Selecciona dos puntos aleatorios para intercambiar una pequeña porción
            idx1, idx2 = random.sample(range(individual.long_genes), 2)
            cantidad = round(random.uniform(0.01, min(individual.genes[idx1], 0.1)), 2)
            
            # Asegurarse de que el gen no se vuelva negativo
            if individual.genes[idx1] - cantidad > 0:
                individual.genes[idx1] -= cantidad
                individual.genes[idx2] += cantidad
                individual.genes[idx1] = round(individual.genes[idx1], 2)
                individual.genes[idx2] = round(individual.genes[idx2], 2)


    def _evaluate_population(self):
        """
        Calcula el fitness de cada individuo simulando el flujo a través del grafo.
        El fitness será el flujo total que llega a las aristas de tipo 'SALIDA'.
        """
        edges_data_frame = app_state.aristas_df
        edge_capacities = app_state.edge_capacities

        for individual in self.population:
            current_flow_edges = [0] * len(edges_data_frame)
            
            # 1. Asignar flujo inicial a las aristas de ENTRADA
            for i, edge in edges_data_frame.iterrows():
                if edge['TipoArista'] == 'ENTRADA':
                    # El flujo de entrada se limita a la capacidad máxima de la arista (si la tuviera)
                    # y se multiplica por el porcentaje de tiempo del semáforo (gen)
                    max_flow_edge = edge_capacities[i][1] if edge_capacities[i][1] > 0 else edge['FlujoEntrada']
                    initial_flow = min(edge['FlujoEntrada'], max_flow_edge)
                    current_flow_edges[i] = initial_flow * individual.genes[i]

            # 2. Simular el flujo a través de los nodos intermedios
            # Esta es una simulación simplificada. Un modelo más complejo usaría un bucle
            # hasta que el flujo se estabilice.
            for _ in range(len(edges_data_frame)): # Iterar varias veces para propagar el flujo
                flujo_entrante_nodos = {}
                # Calcular el flujo total que llega a cada nodo
                for i, edge in edges_data_frame.iterrows():
                    nodo_destino = edge['NodoDestino']
                    if nodo_destino not in flujo_entrante_nodos:
                        flujo_entrante_nodos[nodo_destino] = 0
                    flujo_entrante_nodos[nodo_destino] += current_flow_edges[i]

                # Distribuir el flujo desde los nodos hacia las aristas salientes
                for i, edge in edges_data_frame.iterrows():
                    if edge['TipoArista'] == 'INTERMEDIO':
                        nodo_origen = edge['NodoOrigen']
                        if nodo_origen in flujo_entrante_nodos:
                            # El flujo que puede pasar se limita por la capacidad de la arista
                            # y el porcentaje del semáforo (gen)
                            flujo_disponible = flujo_entrante_nodos[nodo_origen]
                            capacidad_max = edge_capacities[i][1]
                            flujo_a_pasar = min(flujo_disponible, capacidad_max) * individual.genes[i]
                            current_flow_edges[i] = flujo_a_pasar
                            # Restar el flujo que ya pasó para no contarlo dos veces
                            flujo_entrante_nodos[nodo_origen] -= flujo_a_pasar


            # 3. Calcular el fitness como la suma del flujo en las aristas de SALIDA
            fitness_total = 0
            for i, edge in edges_data_frame.iterrows():
                if edge['TipoArista'] == 'SALIDA':
                    # El flujo que llega a una salida es el que pudo pasar por la arista
                    fitness_total += current_flow_edges[i]
            
            individual.fitness = round(fitness_total, 2)

    def run(self):
        """Ejecuta el algoritmo genético."""
        self._initialize_population()
        self._evaluate_population()

        while not self._stopping_condition():
            new_population = []

            # Selección
            for _ in range(self.population_size):
                selected = self._select_individual()
                new_population.append(selected.clone())

            # Cruce
            for i in range(0, self.population_size - 1, 2):
                if random.random() < self.crossover_prob:
                    parent1 = new_population[i]
                    parent2 = new_population[i+1]
                    child1, child2 = self._crossover(parent1, parent2)
                    new_population[i] = child1
                    new_population[i+1] = child2
            
            # Mutación
            for individual in new_population:
                self._mutate(individual)

            # Reemplazo
            self.population = new_population
            self._evaluate_population()

            self.generation += 1
            print(f"Generación {self.generation} completada.")
            # Opcional: Imprimir el mejor individuo de la generación
            # best_fitness = max(ind.fitness for ind in self.population)
            # print(f"Mejor Fitness: {best_fitness}")

        return self.get_best_individual()

    def _stopping_condition(self):
        """Condición de parada (ej: número máximo de generaciones)."""
        return self.generation >= self.max_generations

    def get_best_individual(self):
        """Obtiene el mejor individuo de la población final."""
        return max(self.population, key=lambda ind: ind.fitness)
