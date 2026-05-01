import collections

import pandas as pd
import networkx as nx
from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure


class VentanaAnimacionFlujo(QDialog):
    def __init__(self, df: pd.DataFrame, frames: list[dict], metrics: dict | None = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Animación del Flujo")
        self.resize(1200, 800)

        self.df = df.copy()
        self.frames = frames or []
        self.metrics = metrics or {}
        self.current_index = 0
        self.is_playing = True
        self.max_flow = self._max_flow_value()
        self.edge_order = []

        self.G, self.node_types, self.edge_meta = self._build_graph()
        self.pos = self._compute_layout()

        self.figure = Figure(figsize=(12, 8))
        self.canvas = FigureCanvas(self.figure)
        self.ax = self.figure.add_subplot(111)

        self.lbl_summary = QLabel(self._build_summary_text())
        self.lbl_frame = QLabel("Preparando animación...")
        self.btn_play_pause = QPushButton("Pausar")
        self.btn_restart = QPushButton("Reiniciar")
        self.btn_close = QPushButton("Cerrar")

        self.btn_play_pause.clicked.connect(self.toggle_play)
        self.btn_restart.clicked.connect(self.restart)
        self.btn_close.clicked.connect(self.close)

        controls = QHBoxLayout()
        controls.addWidget(self.lbl_summary)
        controls.addWidget(self.lbl_frame)
        controls.addStretch()
        controls.addWidget(self.btn_play_pause)
        controls.addWidget(self.btn_restart)
        controls.addWidget(self.btn_close)

        layout = QVBoxLayout(self)
        layout.addWidget(self.canvas)
        layout.addLayout(controls)

        self.timer = QTimer(self)
        self.timer.setInterval(900)
        self.timer.timeout.connect(self.next_frame)

        if self.frames:
            self.render_frame(0)
            self.timer.start()
        else:
            self.lbl_frame.setText("No hay pasos para animar.")

    def _build_summary_text(self) -> str:
        total_input = int(self.metrics.get("total_input_flow", 0))
        total_output = int(self.metrics.get("total_output_flow", 0))
        efficiency = int(self.metrics.get("efficiency_percent", 0))
        return f"Entrada: {total_input} | Salida: {total_output} | Eficiencia: {efficiency}%"

    def _max_flow_value(self) -> float:
        if self.df.empty:
            return 1.0
        entrada = pd.to_numeric(self.df.get("FlujoEntrada", pd.Series(dtype=float)), errors="coerce").fillna(0).max()
        salida = pd.to_numeric(self.df.get("CapacidadMaxima", pd.Series(dtype=float)), errors="coerce").fillna(0).max()
        return float(max(1.0, entrada, salida))

    def _build_graph(self):
        graph = nx.DiGraph()
        node_types = {}
        edge_meta = {}

        for _, row in self.df.iterrows():
            origen = str(row["NodoOrigen"]).strip()
            destino = str(row["NodoDestino"]).strip()
            arista = str(row["Arista"]).strip()
            tipo = str(row["TipoArista"]).strip().upper()
            cap_min = float(pd.to_numeric(row.get("CapacidadMinima", 0), errors="coerce") or 0)
            cap_max = float(pd.to_numeric(row.get("CapacidadMaxima", 0), errors="coerce") or 0)
            flujo = float(pd.to_numeric(row.get("FlujoEntrada", 0), errors="coerce") or 0)

            graph.add_edge(origen, destino)
            self.edge_order.append((origen, destino))
            node_types.setdefault(origen, tipo if tipo == "ENTRADA" else "INTERMEDIO")
            node_types.setdefault(destino, "SALIDA" if tipo == "SALIDA" else "INTERMEDIO")
            edge_meta[(origen, destino)] = {
                "label": arista,
                "tipo": tipo,
                "cap_min": cap_min,
                "cap_max": cap_max,
                "flujo": flujo,
            }

        return graph, node_types, edge_meta

    def _compute_layout(self):
        entradas = {n for n, t in self.node_types.items() if t == "ENTRADA"}
        salidas = {n for n, t in self.node_types.items() if t == "SALIDA"}
        intermedios = [n for n in self.G.nodes() if n not in entradas and n not in salidas]
        intermedios_set = set(intermedios)

        levels = {n: 0 for n in entradas}
        queue = collections.deque(entradas)
        while queue:
            node = queue.popleft()
            for succ in self.G.successors(node):
                if succ in intermedios_set and succ not in levels:
                    levels[succ] = levels[node] + 1
                    queue.append(succ)

        nivel_grupos = collections.defaultdict(list)
        for node in intermedios:
            nivel_grupos[levels.get(node, 1)].append(node)

        def _col(nodes, x):
            nodes = sorted(nodes)
            total = len(nodes)
            return {
                node: (x, -index / max(total - 1, 1) if total > 1 else 0.0)
                for index, node in enumerate(nodes)
            }

        pos = {}
        pos.update(_col(sorted(entradas), 0.0))
        niveles = sorted(nivel_grupos.keys())
        count = len(niveles)
        for index, level in enumerate(niveles):
            pos.update(_col(nivel_grupos[level], (index + 1) / (count + 1)))
        pos.update(_col(sorted(salidas), 1.0))
        return pos

    def toggle_play(self):
        self.is_playing = not self.is_playing
        self.btn_play_pause.setText("Reanudar" if not self.is_playing else "Pausar")
        if self.is_playing and self.frames:
            self.timer.start()
        else:
            self.timer.stop()

    def restart(self):
        if not self.frames:
            return
        self.current_index = 0
        self.render_frame(0)
        self.is_playing = True
        self.btn_play_pause.setText("Pausar")
        self.timer.start()

    def next_frame(self):
        if not self.frames:
            self.timer.stop()
            return
        next_index = self.current_index + 1
        if next_index >= len(self.frames):
            self.timer.stop()
            self.is_playing = False
            self.btn_play_pause.setText("Reanudar")
            return
        self.render_frame(next_index)

    def render_frame(self, frame_index: int):
        frame = self.frames[frame_index]
        self.current_index = frame_index
        current_flow_edges = frame.get("current_flow_edges", [])
        incoming_flows = frame.get("incoming_flows", {})
        genes = frame.get("genes", [])
        self.ax.clear()

        node_incoming = {node: 0.0 for node in self.G.nodes()}
        node_outgoing = {node: 0.0 for node in self.G.nodes()}
        for index, (u, v) in enumerate(self.edge_order):
            flow = current_flow_edges[index] if index < len(current_flow_edges) else 0.0
            node_outgoing[u] = node_outgoing.get(u, 0.0) + flow
            node_incoming[v] = node_incoming.get(v, 0.0) + flow

        node_colors = []
        for node in self.G.nodes():
            if self.node_types.get(node) == "ENTRADA":
                node_colors.append("#d9f2d9")
            elif self.node_types.get(node) == "SALIDA":
                node_colors.append("#d9e8ff")
            else:
                node_colors.append("white")

        nx.draw_networkx_nodes(
            self.G,
            self.pos,
            node_size=1600,
            node_color=node_colors,
            edgecolors="black",
            ax=self.ax,
        )

        node_labels = {}
        for node in self.G.nodes():
            incoming = node_incoming.get(node, 0.0)
            outgoing = node_outgoing.get(node, 0.0)
            residual = incoming_flows.get(node, 0.0)
            node_labels[node] = (
                f"{node}\n"
                f"En:{int(incoming)} Sa:{int(outgoing)}\n"
                f"Disp:{int(residual)}"
            )
        nx.draw_networkx_labels(self.G, self.pos, labels=node_labels, font_size=10, font_weight="bold", ax=self.ax)

        edge_labels = {}
        active_edges = []
        edge_colors = []
        widths = []

        for index, (u, v) in enumerate(self.edge_order):
            meta = self.edge_meta[(u, v)]
            flow = current_flow_edges[index] if index < len(current_flow_edges) else 0.0
            gene_value = genes[index] if index < len(genes) else 0.0
            percent = int(float(gene_value) * 100.0 + 0.5)
            base_color = "red" if meta["tipo"] == "ENTRADA" else "blue" if meta["tipo"] == "SALIDA" else "black"
            active_edges.append((u, v))
            edge_colors.append(base_color if flow > 0 else "#bbbbbb")
            scale = flow / self.max_flow if self.max_flow else 0.0
            widths.append(1.2 + max(0.0, scale) * 5.0)
            if meta["tipo"] == "ENTRADA":
                edge_labels[(u, v)] = (
                    f"{meta['label']}\n"
                    f"Entrada {int(meta['flujo'])}\n"
                    f"Tiempo {percent}%\n"
                    f"Flujo {int(flow)}"
                )
            else:
                edge_labels[(u, v)] = (
                    f"{meta['label']}\n"
                    f"Tiempo {percent}%\n"
                    f"Flujo {int(flow)}\n"
                    f"Min.{int(meta['cap_min'])} Max.{int(meta['cap_max'])}"
                )

        nx.draw_networkx_edges(
            self.G,
            self.pos,
            edgelist=active_edges,
            edge_color=edge_colors,
            arrows=True,
            arrowsize=22,
            arrowstyle="-|>",
            width=widths,
            connectionstyle="arc3,rad=0.05",
            node_size=1600,
            ax=self.ax,
        )
        nx.draw_networkx_edge_labels(self.G, self.pos, edge_labels=edge_labels, font_size=8, ax=self.ax)

        titulo = frame.get("label", f"Paso {frame_index}")
        self.ax.set_title(f"Animación del flujo - {titulo}", fontsize=14)
        self.ax.axis("off")
        self.figure.tight_layout()
        self.canvas.draw_idle()
        self.lbl_frame.setText(f"Paso {frame_index + 1} de {len(self.frames)}")
