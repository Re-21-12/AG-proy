import random

class Individual:
    '''
    Representa a un individuo en la población del algoritmo genético.
    - long_genes: Es la cantidad de semáforos/aristas de decisión.
    - genes: El % de tiempo asignado a cada semáforo para conducir vehículos.
    '''
    # Generamos valores entre 0.1 y 1.0 para evitar semáforos totalmente cerrados
    minProb = 0.1
    maxProb = 1.0
    def __init__(self, long_genes=0, genes=None):
        # Si pasamos una lista de genes (usado en cruce o clonación)
        if genes is not None:
            self.genes = list(genes)
        else:
            # Generamos un conjunto de genes cuya suma es 1.0
            # Esto se hace generando n-1 puntos de división aleatorios en el rango [0,1]
            puntos_division = sorted([0.0] + [random.uniform(0, 1) for _ in range(long_genes - 1)] + [1.0])
            # Los genes son las diferencias entre puntos de división consecutivos
            self.genes = [round(puntos_division[i+1] - puntos_division[i], 2) for i in range(long_genes)]
            
            # Nos aseguramos de que no haya genes con valor 0 y que la suma siga siendo 1
            # Esta es una normalización simple. Puede necesitar ajustes más complejos
            # dependiendo de la rigurosidad requerida.
            suma_actual = sum(self.genes)
            if suma_actual != 1.0:
                # Ajuste para corregir imprecisiones de punto flotante
                diferencia = 1.0 - suma_actual
                self.genes[-1] += diferencia
                self.genes[-1] = round(self.genes[-1], 2)


        self.long_genes = len(self.genes)
        # El fitness representa la mayor cantidad de vehiculos hacia la salida 
        self.fitness = 0 

    def clone(self):
        # Retorna un nuevo objeto con la misma configuración de genes y fitness
        clone = Individual(genes=self.genes)
        clone.fitness = self.fitness
        return clone
        
    # Metodo ToString
    def __str__(self):
        return f"Cromosoma: {self.genes} | Fitness: {self.fitness}"

