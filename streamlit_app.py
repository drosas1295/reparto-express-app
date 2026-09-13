import re
from typing import List, Optional

import streamlit as st

# Importa el motor del juego (asegúrate de que reparto_express.py esté en el repo)
import reparto_express as rx


def _require_plotly():
    """Carga Plotly o muestra un error claro en Streamlit Cloud."""
    try:
        import plotly.graph_objects as go  # type: ignore

        return go
    except ModuleNotFoundError as e:
        st.error(
            "No se pudo importar 'plotly'.\n\n"
            "Solución: agrega/actualiza requirements.txt en el repo con, mínimo:\n"
            "- streamlit\n- plotly\n\n"
            "Luego redeploy en Streamlit Cloud (Manage app → Reboot / Deploy)."
        )
        st.stop()
    except Exception as e:
        st.error(f"Error importando Plotly: {e}")
        st.stop()


def parse_tokens(s: str) -> List[str]:
    return [t.strip().upper() for t in re.split(r"[\s,]+", s.strip()) if t.strip()]


def plot_points_route(points, order: Optional[List[str]] = None, title: str = ""):
    go = _require_plotly()

    xs = [p[0] for p in points.values()]
    ys = [p[1] for p in points.values()]

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=xs,
            y=ys,
            mode="markers+text",
            text=list(points.keys()),
            textposition="top center",
            marker=dict(size=12, color="#ffcc00", line=dict(width=1, color="#111")),
            name="Entregas",
        )
    )

    fig.add_trace(
        go.Scatter(
            x=[rx.ALMACEN[0]],
            y=[rx.ALMACEN[1]],
            mode="markers+text",
            text=["H"],
            textposition="top center",
            marker=dict(size=14, color="#ff3355", line=dict(width=1, color="#111")),
            name="Almacén",
        )
    )

    if order:
        route_x = [rx.ALMACEN[0]] + [points[n][0] for n in order] + [rx.ALMACEN[0]]
        route_y = [rx.ALMACEN[1]] + [points[n][1] for n in order] + [rx.ALMACEN[1]]
        fig.add_trace(
            go.Scatter(
                x=route_x,
                y=route_y,
                mode="lines+markers",
                line=dict(width=3, color="#00d1ff"),
                marker=dict(size=6, color="#00d1ff"),
                name="Ruta",
            )
        )

    fig.update_layout(
        title=title,
        template="plotly_dark",
        height=650,
        xaxis=dict(zeroline=False, showgrid=True, gridcolor="rgba(255,255,255,0.08)"),
        yaxis=dict(
            zeroline=False,
            showgrid=True,
            gridcolor="rgba(255,255,255,0.08)",
            scaleanchor="x",
            scaleratio=1,
        ),
        margin=dict(l=20, r=20, t=50, b=20),
        legend=dict(orientation="h"),
    )
    return fig


def plot_graph(points, edges, path: Optional[List[str]], title: str = ""):
    go = _require_plotly()

    fig = go.Figure()
    for key, w in edges.items():
        a, b = tuple(key)
        xa, ya = points[a]
        xb, yb = points[b]
        fig.add_trace(
            go.Scatter(
                x=[xa, xb],
                y=[ya, yb],
                mode="lines",
                line=dict(color="rgba(200,200,200,0.25)", width=2),
                showlegend=False,
            )
        )

    if path and len(path) >= 2:
        for u, v in zip(path, path[1:]):
            xu, yu = points[u]
            xv, yv = points[v]
            fig.add_trace(
                go.Scatter(
                    x=[xu, xv],
                    y=[yu, yv],
                    mode="lines",
                    line=dict(color="#00d1ff", width=4),
                    showlegend=False,
                )
            )

    fig.add_trace(
        go.Scatter(
            x=[p[0] for p in points.values()],
            y=[p[1] for p in points.values()],
            mode="markers+text",
            text=list(points.keys()),
            textposition="top center",
            marker=dict(size=12, color="#ffcc00", line=dict(width=1, color="#111")),
            showlegend=False,
        )
    )

    fig.update_layout(
        title=title,
        template="plotly_dark",
        height=650,
        margin=dict(l=20, r=20, t=50, b=20),
        yaxis=dict(scaleanchor="x", scaleratio=1),
    )
    return fig


st.set_page_config(page_title="Reparto Express", layout="wide")

st.title("Reparto Express — App (Streamlit)")
st.caption("Selecciona misión + estrellas, genera el escenario y evalúa tu jugada.")

with st.sidebar:
    mission = st.selectbox(
        "Misión",
        options=[
            (1, "TSP"),
            (2, "CVRP"),
            (3, "VRPTW"),
            (4, "Knapsack"),
            (5, "Dijkstra"),
            (6, "Flota"),
            (7, "Orienteering"),
        ],
        format_func=lambda x: f"{x[0]} — {x[1]}",
    )[0]
    stars = st.slider("Dificultad (estrellas)", 1, 5, 3, 1)
    seed = st.number_input("Seed (reproducible)", value=1, step=1)
    generate = st.button("Generar escenario", type="primary")

if "scenario" not in st.session_state:
    st.session_state.scenario = None
    st.session_state.meta = None

if generate or st.session_state.scenario is None:
    if mission == 1:
        sc = rx.preparar_tsp(int(seed), int(stars))
        st.session_state.scenario = sc
        st.session_state.meta = {"type": "points", "points": sc["entregas"], "tam": sc["tam"]}
    elif mission == 2:
        sc = rx.preparar_cvrp(int(seed), int(stars))
        st.session_state.scenario = sc
        st.session_state.meta = {"type": "points", "points": sc["entregas"], "tam": sc["tam"]}
    elif mission == 3:
        sc = rx.preparar_vrptw(int(seed), int(stars))
        st.session_state.scenario = sc
        st.session_state.meta = {"type": "points", "points": sc["entregas"], "tam": sc["tam"]}
    elif mission == 4:
        sc = rx.preparar_mochila(int(seed), int(stars))
        st.session_state.scenario = sc
        st.session_state.meta = {"type": "knapsack"}
    elif mission == 5:
        sc = rx.preparar_dijkstra(int(seed), int(stars))
        st.session_state.scenario = sc
        st.session_state.meta = {"type": "graph"}
    elif mission == 6:
        sc = rx.preparar_flota(int(seed), int(stars))
        st.session_state.scenario = sc
        st.session_state.meta = {"type": "points", "points": sc["entregas"], "tam": sc["tam"]}
    elif mission == 7:
        sc = rx.preparar_orienteering(int(seed), int(stars))
        st.session_state.scenario = sc
        st.session_state.meta = {"type": "points", "points": sc["entregas"], "tam": sc["tam"]}

scenario = st.session_state.scenario
meta = st.session_state.meta

col_left, col_right = st.columns([1.15, 0.85])

with col_left:
    if meta["type"] == "points":
        points = meta["points"]
        st.plotly_chart(
            plot_points_route(points, None, title=f"Misión {mission} — {'★'*stars}"),
            use_container_width=True,
        )
        st.write("**Puntos:**", {k: v for k, v in points.items()})

    elif meta["type"] == "graph":
        pts = scenario["puntos"]
        st.write(f"Origen: **{scenario['origen']}** | Destino: **{scenario['destino']}**")
        st.plotly_chart(
            plot_graph(pts, scenario["aristas"], None, title=f"Misión 5 — {'★'*stars}"),
            use_container_width=True,
        )

    elif meta["type"] == "knapsack":
        st.write(f"Capacidad: **{scenario['capacidad']}**")
        st.table([
            {"Item": k, "Valor": v[0], "Peso": v[1]} for k, v in scenario["items"].items()
        ])

with col_right:
    st.subheader("Tu jugada")

    if mission in (1, 3):
        st.write("Orden (usa todas exactamente una vez). Ej: `A C B D`")
        inp = st.text_input("Orden", value="")
        if st.button("Evaluar"):
            order = parse_tokens(inp)
            puntos = scenario["entregas"]
            if set(order) != set(puntos.keys()) or len(order) != len(puntos):
                st.error("Orden inválido: debes usar cada punto exactamente una vez.")
            else:
                if mission == 1:
                    d = rx.longitud_ruta(order, puntos)
                    nn = rx.ruta_vecino_mas_cercano(puntos)
                    dnn = rx.longitud_ruta(nn, puntos)
                    score = rx.puntuar_min(d, dnn)
                    st.metric("Puntuación", f"{score}/100")
                    st.metric("Distancia", f"{d:.2f}")
                    st.plotly_chart(plot_points_route(puntos, order, title=f"Tu ruta — {score}/100"), use_container_width=True)
                else:
                    dist, tard, _ = rx._sim_vrptw(order, puntos, scenario["ventanas"], scenario["velocidad"])
                    costo = dist + scenario["pen"] * tard
                    edd = sorted(puntos.keys(), key=lambda k: scenario["ventanas"][k][1])
                    distb, tardb, _ = rx._sim_vrptw(edd, puntos, scenario["ventanas"], scenario["velocidad"])
                    costb = distb + scenario["pen"] * tardb
                    score = rx.puntuar_min(costo, costb)
                    st.metric("Puntuación", f"{score}/100")
                    st.write({"dist": dist, "tard": tard, "costo": costo})
                    st.plotly_chart(plot_points_route(puntos, order, title=f"Tu ruta — {score}/100"), use_container_width=True)

    elif mission == 2:
        st.write("Una línea por viaje. Ej:\nA C\nB D E")
        text = st.text_area("Viajes", value="")
        if st.button("Evaluar"):
            lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
            viajes = [parse_tokens(ln) for ln in lines]
            all_nodes = [n for v in viajes for n in v]
            puntos = scenario["entregas"]
            if len(all_nodes) != len(set(all_nodes)):
                st.error("No repitas entregas entre viajes.")
            elif set(all_nodes) != set(puntos.keys()):
                st.error("Debes incluir todas las entregas exactamente una vez.")
            else:
                cap = scenario["capacidad"]
                dem = scenario["demanda"]
                for i, v in enumerate(viajes, 1):
                    load = sum(dem[n] for n in v)
                    if load > cap:
                        st.error(f"Viaje {i} excede capacidad: {load} > {cap}")
                        st.stop()
                dist = sum(rx.longitud_ruta(v, puntos) for v in viajes)
                base = rx._heuristica_cvrp(puntos, dem, cap)
                distb = sum(rx.longitud_ruta(v, puntos) for v in base)
                score = rx.puntuar_min(dist, distb)
                st.metric("Puntuación", f"{score}/100")
                st.metric("Distancia total", f"{dist:.2f}")

    elif mission == 4:
        st.write("Escribe items a llevar, ej: `A D F` (sin repetir)")
        inp = st.text_input("Selección", value="")
        if st.button("Evaluar"):
            sel = parse_tokens(inp)
            if len(sel) != len(set(sel)):
                st.error("No repitas items.")
            elif not set(sel) <= set(scenario["items"].keys()):
                st.error("Items inválidos.")
            else:
                peso = sum(scenario["items"][k][1] for k in sel)
                valor = sum(scenario["items"][k][0] for k in sel)
                opt, _ = rx.knapsack_optimo(scenario["items"], scenario["capacidad"])
                if peso > scenario["capacidad"]:
                    st.error("Sobrepeso: puntuación 0.")
                    score = 0
                else:
                    score = rx.puntuar_max(valor, opt)
                st.metric("Puntuación", f"{score}/100")
                st.write({"peso": peso, "valor": valor, "optimo": opt})

    elif mission == 5:
        st.write(f"Camino de {scenario['origen']} a {scenario['destino']}, ej: `A B C`")
        inp = st.text_input("Camino", value="")
        if st.button("Evaluar"):
            path = parse_tokens(inp)
            if not path or path[0] != scenario["origen"] or path[-1] != scenario["destino"]:
                st.error("Camino inválido (origen/destino).")
            else:
                cost = 0.0
                for u, v in zip(path, path[1:]):
                    neigh = dict(scenario["grafo"][u])
                    if v not in neigh:
                        st.error(f"No existe arista {u}-{v}.")
                        st.stop()
                    cost += neigh[v]
                opt_cost, opt_path = rx.dijkstra(scenario["grafo"], scenario["origen"], scenario["destino"])
                score = rx.puntuar_min(cost, opt_cost)
                st.metric("Puntuación", f"{score}/100")
                st.write({"costo": cost, "óptimo": opt_cost, "camino_óptimo": opt_path})
                st.plotly_chart(plot_graph(scenario["puntos"], scenario["aristas"], path, title=f"Tu camino — {score}/100"), use_container_width=True)

    elif mission == 6:
        k = scenario["k"]
        st.write(f"Una línea por vehículo (exactamente {k} líneas).")
        text = st.text_area("Vehículos", value="")
        if st.button("Evaluar"):
            lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
            grupos = [parse_tokens(ln) for ln in lines]
            puntos = scenario["entregas"]
            if len(grupos) != k:
                st.error(f"Debes ingresar exactamente {k} líneas.")
            else:
                all_nodes = [n for g in grupos for n in g]
                if len(all_nodes) != len(set(all_nodes)):
                    st.error("No repitas entregas.")
                elif set(all_nodes) != set(puntos.keys()):
                    st.error("Debes incluir todas las entregas exactamente una vez.")
                else:
                    largos = rx._largos_grupos(grupos, puntos)
                    makes = max(largos)
                    base = rx._heuristica_flota(puntos, k)
                    makesb = max(rx._largos_grupos(base, puntos))
                    score = rx.puntuar_min(makes, makesb)
                    st.metric("Puntuación", f"{score}/100")
                    st.write({"makespan": makes, "baseline": makesb, "largos": largos})

    elif mission == 7:
        st.write("Entregas a visitar en orden, ej: `A C E` (puede ser vacío)")
        inp = st.text_input("Orden", value="")
        if st.button("Evaluar"):
            order = parse_tokens(inp)
            puntos = scenario["entregas"]
            if len(order) != len(set(order)):
                st.error("No repitas entregas.")
            elif not set(order) <= set(puntos.keys()):
                st.error("Entregas inválidas.")
            else:
                dist = rx.longitud_ruta(order, puntos) if order else 0.0
                if dist > scenario["presupuesto"] + 1e-9:
                    st.error("Te pasaste del presupuesto: puntuación 0.")
                    score = 0
                else:
                    val = sum(scenario["premio"][k] for k in order)
                    opt_val, _, _ = rx._orienteering_optimo(puntos, scenario["premio"], scenario["presupuesto"], int(stars))
                    score = rx.puntuar_max(val, opt_val)
                st.metric("Puntuación", f"{score}/100")
                st.write({"dist": dist, "presupuesto": scenario["presupuesto"]})
                st.plotly_chart(plot_points_route(puntos, order, title=f"Tu ruta — {score}/100"), use_container_width=True)
