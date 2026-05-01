"""
Módulo de configuración de logging para el Algoritmo Genético.
Centraliza toda la lógica de logging y debug.
"""

import logging


def setup_logger(debug: bool = False) -> logging.Logger:
    """
    Configura y retorna el logger para el Algoritmo Genético.
    
    Args:
        debug: Si True, establece nivel DEBUG; si False, nivel INFO.
    
    Returns:
        logging.Logger: Logger configurado para AG.
    """
    logger = logging.getLogger("genetic_algorithm")
    
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter("[%(levelname)s][AG] %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    
    logger.setLevel(logging.DEBUG if debug else logging.INFO)
    logger.propagate = False
    return logger


def log_initialization(logger: logging.Logger, population_size: int, gene_count: int, 
                       max_generations: int, edges_count: int, propagation_depth: int):
    """Registra la inicialización del AG."""
    logger.info(
        "AG inicializado | poblacion=%s genes=%s generaciones=%s aristas=%s",
        population_size, gene_count, max_generations, edges_count,
    )
    logger.info("Profundidad del grafo calculada: %s", propagation_depth)


def log_graph_depth_computation(logger: logging.Logger, nodes_count: int, 
                                roots: set, final_depth: int):
    """Registra el cálculo de profundidad del grafo."""
    logger.debug("Adyacencia construida con %s nodos origen.", nodes_count)
    logger.debug("Nodos raiz detectados: %s", sorted(roots))
    
    if not roots:
        logger.warning(
            "No se detectaron aristas ENTRADA; se usa profundidad por defecto."
        )
    
    logger.debug("Profundidad BFS maxima=%s", final_depth)


def log_population_creation(logger: logging.Logger, population_size: int, first_individual):
    """Registra la creación de la población inicial."""
    logger.info("Poblacion inicial creada: %s cromosomas", population_size)
    logger.debug("Primer cromosoma: %s", first_individual)


def log_population_stats(logger: logging.Logger, min_fit: float, avg_fit: float, max_fit: float):
    """Registra estadísticas de fitness de la población."""
    logger.debug(
        "Fitness poblacion | min=%.4f avg=%.4f max=%.4f",
        min_fit, avg_fit, max_fit,
    )


def log_fitness_computation(logger: logging.Logger, call_count: int, total_edges: int, input_flows: list):
    """Registra el cálculo de fitness."""
    if call_count <= 3:  # FITNESS_DEBUG_CALLS
        logger.debug(
            "Fitness call #%s | total_aristas=%s | flujos_entrada=%s",
            call_count, total_edges, input_flows,
        )


def log_fitness_result(logger: logging.Logger, call_count: int, fitness_total: float):
    """Registra el resultado de fitness."""
    if call_count <= 3:  # FITNESS_DEBUG_CALLS
        logger.debug("Fitness call #%s resultado=%.4f", call_count, fitness_total)


def log_selection(logger: logging.Logger, call_count: int, pick: float = None, 
                 total: float = None, selected_fitness: float = None):
    """Registra la selección de individuos."""
    if call_count <= 5:  # SELECTION_DEBUG_CALLS
        if pick is not None and total is not None and selected_fitness is not None:
            logger.debug(
                "Seleccion #%s | pick=%.4f total=%.4f fitness_sel=%.4f",
                call_count, pick, total, selected_fitness,
            )
        else:
            logger.debug("Seleccion #%s por azar (fitness total=0)", call_count)


def log_crossover(logger: logging.Logger, applied: bool, point: int = None):
    """Registra el cruce."""
    if applied:
        logger.debug("Cruce aplicado en punto=%s", point)
    else:
        logger.debug("Cruce omitido por probabilidad")


def log_mutation(logger: logging.Logger, mutation_count: int):
    """Registra las mutaciones."""
    if mutation_count > 0:
        logger.debug("Mutaciones aplicadas en individuo: %s", mutation_count)


def log_generation_summary(logger: logging.Logger, generation: int, max_generations: int,
                          best_gen: float, best_global: float, avg: float, worst: float,
                          best_individual):
    """Registra el resumen de una generación."""
    logger.info(
        "Gen %s/%s | best_gen=%.4f best_global=%.4f avg=%.4f worst=%.4f",
        generation, max_generations, best_gen, best_global, avg, worst,
    )
    logger.debug("Mejor cromosoma actual: %s", best_individual)


def log_improvement(logger: logging.Logger, generation: int, new_best: float, delta: float, individual):
    """Registra cuando hay mejora en el fitness global."""
    logger.info(
        "MEJORA Gen %s | nuevo_best=%.4f | delta=+%.4f | cromosoma=%s",
        generation, new_best, delta, individual,
    )


def log_execution_start(logger: logging.Logger):
    """Registra el inicio de la ejecución."""
    logger.info("Inicio de ejecucion del AG")


def log_initial_state(logger: logging.Logger, best_fitness: float, best_individual):
    """Registra el estado inicial."""
    logger.info(
        "Estado inicial | mejor_fitness=%.4f | cromosoma=%s",
        best_fitness, best_individual,
    )


def log_execution_end(logger: logging.Logger, best_fitness: float, best_individual):
    """Registra el final de la ejecución."""
    logger.info("Ejecucion finalizada | mejor_fitness=%.4f", best_fitness)
    logger.info("Mejor cromosoma final: %s", best_individual)
