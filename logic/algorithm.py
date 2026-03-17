import random
from logic.individual import Individual

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
        for i in range(individual.long_genes):
            if random.random() < self.mutation_prob:
                individual.genes[i] = round(random.uniform(self.minProb, self.maxProb), 2)

    def _evaluate_population(self, ENTRANCE):
        """
        Placeholder para la función de evaluación.
        Aquí es donde calcularías el fitness de cada individuo.
        Por ahora, asignaremos un fitness aleatorio para demostración.
        """
    
        for individual in self.population:
            # Reemplaza esto con tu lógica de evaluación real
            
            individual.fitness = individual.genes 

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
