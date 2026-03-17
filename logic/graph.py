import collections
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt


def generar_grafo_flujo(csv_path='src/data.csv'):
    try:
        df = pd.read_csv(csv_path, skipinitialspace=True)
    except Exception as e:
        print(f"Error al leer el CSV: {e}")
        return

    G = nx.DiGraph()
    edge_data     = {}  # (origen, destino) -> {label, color}
    entrada_count = 0
    salida_count  = 0
    nodos_entrada = set()
    nodos_salida  = set()

    for _, fila in df.iterrows():
        if pd.isna(fila['NodoOrigen']) or pd.isna(fila['NodoDestino']):
            continue

        origen  = str(fila['NodoOrigen']).strip()
        destino = str(fila['NodoDestino']).strip()
        arista  = str(fila['Arista']).strip()
        tipo    = str(fila['TipoArista']).strip().upper() if pd.notna(fila['TipoArista']) else 'INTERMEDIO'
        porcentaje  = str(fila['PorcentajeDeTiempo']).strip()

        try:
            cap_min = int(float(fila['CapacidadMinima']))
        except (ValueError, TypeError):
            cap_min = 0
        try:
            cap_max = int(float(fila['CapacidadMaxima']))
        except (ValueError, TypeError):
            cap_max = 0
        try:
            flujo = int(float(fila['FlujoEntrada']))
        except (ValueError, TypeError):
            flujo = 0

        ruta = f"{origen}→{destino}"
        if tipo == 'ENTRADA':
            entrada_count += 1
            lbl   = f"{ruta}\nEntrada{entrada_count}\n{flujo}"
            color = 'red'
            nodos_entrada.add(origen)
        elif tipo == 'SALIDA':
            salida_count += 1
            flujo_str = str(flujo) if flujo > 0 else "?"
            lbl   = f"{ruta}\nSalida{salida_count}\n{flujo_str}\nMin.[{cap_min}]\nMax.[{cap_max}]"
            color = 'blue'
            nodos_salida.add(destino)
        else:
            lbl   = f"{ruta}\n{arista}\nMin.[{cap_min}]\nMax.[{cap_max}]"
            color = 'black'

        G.add_edge(origen, destino)
        edge_data[(origen, destino)] = {'label': lbl, 'color': color}

    if G.number_of_nodes() == 0:
        print("No hay nodos para graficar.")
        return

    # ── Layout por capas ─────────────────────────────────────────────────────
    nodos_intermedios = [n for n in G.nodes()
                         if n not in nodos_entrada and n not in nodos_salida]
    intermedios_set = set(nodos_intermedios)

    levels = {n: 0 for n in nodos_entrada}
    queue  = collections.deque(nodos_entrada)
    while queue:
        node = queue.popleft()
        for succ in G.successors(node):
            if succ in intermedios_set and succ not in levels:
                levels[succ] = levels[node] + 1
                queue.append(succ)

    nivel_grupos = collections.defaultdict(list)
    for n in nodos_intermedios:
        nivel_grupos[levels.get(n, 1)].append(n)

    def _col(nodos, x):
        nodos = sorted(nodos)
        total = len(nodos)
        return {n: (x, -i / max(total - 1, 1) if total > 1 else 0.0)
                for i, n in enumerate(nodos)}

    pos = {}
    pos.update(_col(sorted(nodos_entrada), 0.0))
    niveles_interm = sorted(nivel_grupos.keys())
    n_niveles = len(niveles_interm)
    for k, lv in enumerate(niveles_interm):
        pos.update(_col(nivel_grupos[lv], (k + 1) / (n_niveles + 1)))
    pos.update(_col(sorted(nodos_salida), 1.0))

    # ── Dibujar ──────────────────────────────────────────────────────────────
    plt.figure(figsize=(14, 8))
    ax = plt.gca()

    nx.draw_networkx_nodes(G, pos, node_size=1500,
                           node_color='white', edgecolors='black', ax=ax)
    nx.draw_networkx_labels(G, pos, font_size=10, font_weight='bold', ax=ax)

    # Flechas por color
    for color in ('red', 'blue', 'black'):
        aristas_color = [(u, v) for (u, v), d in edge_data.items() if d['color'] == color]
        if aristas_color:
            nx.draw_networkx_edges(
                G, pos,
                edgelist=aristas_color,
                edge_color=color,
                arrows=True,
                arrowsize=25,
                arrowstyle='-|>',
                width=2.0,
                connectionstyle='arc3,rad=0.05',
                node_size=1500,
                ax=ax,
            )

    # Etiquetas por color (rojo / azul / negro)
    for color in ('red', 'blue', 'black'):
        subset = {k: v['label'] for k, v in edge_data.items() if v['color'] == color}
        if subset:
            nx.draw_networkx_edge_labels(G, pos, edge_labels=subset,
                                         font_size=8, font_color=color, ax=ax)

    plt.title("GRAFO INICIAL", fontsize=14)
    plt.axis('off')
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    generar_grafo_flujo()