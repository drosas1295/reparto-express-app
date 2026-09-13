import re
from typing import Dict, List, Optional
import streamlit as st
import reparto_express as rx

def _require_plotly():
    try:
        import plotly.graph_objects as go
        return go
    except ModuleNotFoundError:
        st.error("No se pudo importar 'plotly'. Revisa la instalación.")
        st.stop()

def parse_tokens(s: str) -> List[str]:
    return [t.strip().upper() for t in re.split(r"[\s,]+", s.strip()) if t.strip()]

def plot_points_route(points: Dict[str, tuple], order: Optional[List[str]] = None, title: str = "", labels_override: Optional[Dict[str, str]] = None):
    go = _require_plotly()
    xs = [p[0] for p in points.values()]
    ys = [p[1] for p in points.values()]
    labels = [labels_override.get(k, k) if labels_override else k for k in points.keys()]
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=xs, y=ys, mode="markers+text", text=labels,
        textposition="top center", marker=dict(size=12, color="#ffcc00"), name="Entregas"
    ))
    fig.add_trace(go.Scatter(
        x=[rx.ALMACEN[0]], y=[rx.ALMACEN[1]], mode="markers+text",
        text=["H (Almacén)"], textposition="top center", marker=dict(size=14, color="#ff3355"), name="Almacén"
    ))
    
    if order:
        route_x = [rx.ALMACEN[0]] + [points[n][0] for n in order if n in points] + [rx.ALMACEN[0]]
        route_y = [rx.ALMACEN[1]] + [points[n][1] for n in order if n in points] + [rx.ALMACEN[1]]
        fig.add_trace(go.Scatter(
            x=route_x, y=route_y, mode="lines+markers", line=dict(width=3, color="#00d1ff"), name="Ruta"
        ))
        
    fig.update_layout(
        title=title, template="plotly_dark", height=450,
        margin=dict(l=10, r=10, t=40, b=10)
    )
    return fig

def plot_graph(points: Dict[str, tuple], edges: Dict, path: Optional[List[str]], title: str = ""):
    go = _require_plotly()
    fig = go.Figure()
    
    for key, w in edges.items():
        a, b = tuple(key)
        fig.add_trace(go.Scatter(
            x=[points[a][0], points[b][0]], y=[points[a][1], points[b][1]],
            mode="lines", line=dict(color="rgba(200,200,200,0.3)", width=2), showlegend=False
        ))
        
    if path and len(path) >= 2:
        for u, v in zip(path, path[1:]):
            if u in points and v in points:
                fig.add_trace(go.Scatter(
                    x=[points[u][0], points[v][0]], y=[points[u][1], points[v][1]],
                    mode="lines", line=dict(color="#00d1ff", width=4), showlegend=False
                ))
            
    fig.add_trace(go.Scatter(
        x=[p[0] for p in points.values()], y=[p[1] for p in points.values()],
        mode="markers+text", text=list(points.keys()), textposition="top center",
        marker=dict(size=12, color="#ffcc00"), showlegend=False
    ))
                             
    fig.update_layout(
        title=title, template="plotly_dark", height=450,
        margin=dict(l=10, r=10, t=40, b=10)
    )
    return fig

st.set_page_config(page_title="Reparto Express", layout="wide")
st.title("Reparto Express — App (Streamlit)")
st.caption("Selecciona la misión, define la dificultad y resuelve el problema de optimización sin necesidad de hacer scroll.")

instrucciones = {
    1: "🎯 **Misión 1 (TSP):** Visita todos los puntos exactamente una vez y regresa al almacén (H) recorriendo la menor distancia posible. Escribe el orden separado por espacios (Ej: A C B D).",
    2: "🎯 **Misión 2 (CVRP):** Reparte la carga respetando la capacidad máxima de cada vehículo. Escribe un viaje por línea (Ej: A C en la línea 1, B D en la línea 2).",
    3: "🎯 **Misión 3 (VRPTW):** Cada punto tiene una ventana de tiempo [Inicio, Fin]. Ordena tu ruta para cumplir las entregas a tiempo y evitar penalizaciones (Ej: A B C D).",
    4: "🎯 **Misión 4 (Knapsack):** Selecciona los objetos que maximicen el valor total sin exceder la capacidad de peso permitida (Ej: A D F).",
    5: "🎯 **Misión 5 (Dijkstra):** Encuentra la ruta con la menor distancia/costo para conectar el punto de Origen con el Destino (Ej: A B D F).",
    6: "🎯 **Misión 6 (Flota):** Divide los puntos entre la cantidad de vehículos indicada (una línea por vehículo) para minimizar el tiempo de la ruta más larga (makespan).",
    7: "🎯 **Misión 7 (Orienteering):** Tienes un límite estricto de kilómetros. Elige qué puntos visitar para obtener el mayor puntaje de premio posible sin exceder el presupuesto de distancia."
}

with st.sidebar:
    mission = st.selectbox("Misión", options=[
        (1, "TSP"), (2, "CVRP"), (3, "VRPTW"), (4, "Knapsack"), 
        (5, "Dijkstra"), (6, "Flota"), (7, "Orienteering")
    ], format_func=lambda x: f"{x[0]} — {x[1]}")[0]
    
    stars = st.slider("Dificultad (estrellas)", 1, 5, 2, 1)
    seed = st.number_input("Semilla (Seed)", value=3, step=1)
    generate = st.button("Generar escenario", type="primary")

# REGENERA AUTOMÁTICAMENTE EL ESCENARIO SI SE CAMBIA DE MISIÓN O SE PRESIONA BOTÓN
if ("scenario" not in st.session_state 
    or generate 
    or st.session_state.get("last_mission") != mission):
    st.session_state.last_mission = mission
    if mission == 1: sc = rx.preparar_tsp(int(seed), int(stars)); st.session_state.meta = {"type": "points"}
    elif mission == 2: sc = rx.preparar_cvrp(int(seed), int(stars)); st.session_state.meta = {"type": "points"}
    elif mission == 3: sc = rx.preparar_vrptw(int(seed), int(stars)); st.session_state.meta = {"type": "points"}
    elif mission == 4: sc = rx.preparar_mochila(int(seed), int(stars)); st.session_state.meta = {"type": "knapsack"}
    elif mission == 5: sc = rx.preparar_dijkstra(int(seed), int(stars)); st.session_state.meta = {"type": "graph"}
    elif mission == 6: sc = rx.preparar_flota(int(seed), int(stars)); st.session_state.meta = {"type": "points"}
    elif mission == 7: sc = rx.preparar_orienteering(int(seed), int(stars)); st.session_state.meta = {"type": "points"}
    st.session_state.scenario = sc

scenario = st.session_state.scenario
meta = st.session_state.meta

st.info(instrucciones[mission])

col_left, col_right = st.columns([1.1, 0.9])

with col_left:
    if meta["type"] == "points":
        labels_map = None
        if mission == 2:
            labels_map = {k: f"{k} (d={scenario['demanda'][k]})" for k in scenario["entregas"]}
        elif mission == 3:
            labels_map = {k: f"{k} {scenario['ventanas'][k]}" for k in scenario["entregas"]}
        elif mission == 7:
            labels_map = {k: f"{k} (+{scenario['premio'][k]})" for k in scenario["entregas"]}
            
        st.plotly_chart(
            plot_points_route(scenario["entregas"], None, title=f"Mapa Misión {mission} — {'★'*stars}", labels_override=labels_map), 
            use_container_width=True
        )
    elif meta["type"] == "graph":
        st.plotly_chart(
            plot_graph(scenario["puntos"], scenario["aristas"], None, title=f"Grafo Misión 5 — {'★'*stars}"), 
            use_container_width=True
        )
    elif meta["type"] == "knapsack":
        st.metric("📦 Capacidad de la Mochila", f"{scenario['capacidad']} kg")

with col_right:
    st.markdown("### Datos de la Misión y Respuesta")
    
    # DATOS DE LA MISIÓN
    if mission == 1:
        st.write("**Puntos a visitar:**", ", ".join(scenario["entregas"].keys()))
        
    elif mission == 2:
        st.metric("📦 Capacidad Máxima por Vehículo", f"{scenario['capacidad']} unidades")
        st.write("**Demandas por punto:**")
        st.dataframe(
            [{"Punto": k, "Demanda": v} for k, v in scenario["demanda"].items()],
            use_container_width=True, height=140
        )
            
    elif mission == 3:
        st.write("**Ventanas de Tiempo [Inicio, Fin]:**")
        st.dataframe(
            [{"Punto": k, "Ventana": f"[{v[0]}, {v[1]}]"} for k, v in scenario["ventanas"].items()],
            use_container_width=True, height=140
        )
        
    elif mission == 4:
        st.write("**Lista de Objetos Disponibles:**")
        st.dataframe(
            [{"Objeto": k, "Valor": v[0], "Peso": v[1]} for k, v in scenario["items"].items()],
            use_container_width=True, height=150
        )
        
    elif mission == 5:
        c1, c2 = st.columns(2)
        c1.metric("Punto Origen", scenario["origen"])
        c2.metric("Punto Destino", scenario["destino"])
        st.write("**Conexiones disponibles (Nodos y Pesos):**")
        st.dataframe(
            [{"Conexión": f"{a} <-> {b}", "Distancia": w} for key, w in scenario["aristas"].items() for a, b in [tuple(key)]],
            use_container_width=True, height=140
        )
        
    elif mission == 6:
        st.metric("🚗 Vehículos Disponibles", f"{scenario['k']} unidades")
        st.write("**Puntos a repartir:**", ", ".join(scenario["entregas"].keys()))
        
    elif mission == 7:
        st.metric("🎯 Presupuesto Máximo de Distancia", f"{scenario['presupuesto']} km")
        st.write("**Premios por punto:**")
        st.dataframe(
            [{"Punto": k, "Premio": v} for k, v in scenario["premio"].items()],
            use_container_width=True, height=140
        )

    st.markdown("---")
    
    # CAMPOS DE ENTRADA Y EVALUACIÓN
    if mission in (1, 3):
        inp = st.text_input("Ingresa tu ruta ordenada (separada por espacios):", value="", key=f"in_{mission}")
        if st.button("Evaluar Ruta", type="primary"):
            order = parse_tokens(inp)
            puntos = scenario["entregas"]
            if set(order) != set(puntos.keys()) or len(order) != len(puntos):
                st.error("Ruta inválida: debes incluir cada punto exactamente una vez.")
            else:
                if mission == 1:
                    d = rx.longitud_ruta(order, puntos)
                    score = rx.puntuar_min(d, rx.longitud_ruta(rx.ruta_vecino_mas_cercano(puntos), puntos))
                    st.success(f"Puntuación Obtenida: {score}/100 | Distancia total: {d:.2f} km")
                else:
                    dist, tard, _ = rx._sim_vrptw(order, puntos, scenario["ventanas"], scenario["velocidad"])
                    costo = dist + scenario["pen"] * tard
                    edd = sorted(puntos.keys(), key=lambda k: scenario["ventanas"][k][1])
                    distb, tardb, _ = rx._sim_vrptw(edd, puntos, scenario["ventanas"], scenario["velocidad"])
                    score = rx.puntuar_min(costo, distb + scenario["pen"] * tardb)
                    st.success(f"Puntuación Obtenida: {score}/100 | Distancia: {dist:.2f} km | Tardanza: {tard:.2f} h")

    elif mission == 2:
        text = st.text_area("Ingresa los viajes (una línea por vehículo):", value="", height=90, key="in_2")
        if st.button("Evaluar Asignación", type="primary"):
            viajes = [parse_tokens(ln) for ln in text.splitlines() if ln.strip()]
            all_nodes = [n for v in viajes for n in v]
            puntos = scenario["entregas"]
            if len(all_nodes) != len(set(all_nodes)) or set(all_nodes) != set(puntos.keys()):
                st.error("Error en datos: cada punto debe ser visitado exactamente una vez.")
            else:
                cap, dem = scenario["capacidad"], scenario["demanda"]
                excesos = [i + 1 for i, v in enumerate(viajes) if sum(dem[n] for n in v) > cap]
                if excesos:
                    st.error(f"Excediste la capacidad de {cap} u. en el/los viaje(s): {excesos}")
                else:
                    dist = sum(rx.longitud_ruta(v, puntos) for v in viajes)
                    base = sum(rx.longitud_ruta(v, puntos) for v in rx._heuristica_cvrp(puntos, dem, cap))
                    score = rx.puntuar_min(dist, base)
                    st.success(f"Puntuación Obtenida: {score}/100 | Distancia Total: {dist:.2f} km")

    elif mission == 4:
        inp = st.text_input("Ingresa los objetos a llevar (ej: A C E):", value="", key="in_4")
        if st.button("Evaluar Mochila", type="primary"):
            sel = parse_tokens(inp)
            if not set(sel) <= set(scenario["items"].keys()):
                st.error("Identificador de objeto inválido.")
            else:
                peso = sum(scenario["items"][k][1] for k in sel)
                if peso > scenario["capacidad"]:
                    st.error(f"Sobrepeso: Carga total {peso} kg supera el límite de {scenario['capacidad']} kg.")
                else:
                    valor = sum(scenario["items"][k][0] for k in sel)
                    opt, _ = rx.knapsack_optimo(scenario["items"], scenario["capacidad"])
                    score = rx.puntuar_max(valor, opt)
                    st.success(f"Puntuación Obtenida: {score}/100 | Valor Total: {valor}")

    elif mission == 5:
        inp = st.text_input("Ingresa la ruta de nodos (ej: A B D):", value="", key="in_5")
        if st.button("Evaluar Camino", type="primary"):
            path = parse_tokens(inp)
            if not path or path[0] != scenario["origen"] or path[-1] != scenario["destino"]:
                st.error(f"Camino inválido: debe comenzar en {scenario['origen']} y terminar en {scenario['destino']}.")
            else:
                try:
                    cost = sum(dict(scenario["grafo"][u])[v] for u, v in zip(path, path[1:]))
                    opt_cost, _ = rx.dijkstra(scenario["grafo"], scenario["origen"], scenario["destino"])
                    score = rx.puntuar_min(cost, opt_cost)
                    st.success(f"Puntuación Obtenida: {score}/100 | Distancia Recorrida: {cost:.2f}")
                except KeyError:
                    st.error("Conexión no válida entre uno o más nodos consecutivos.")

    elif mission == 6:
        text = st.text_area(f"Ingresa las rutas para cada uno de los {scenario['k']} vehículos (una línea por vehículo):", value="", height=90, key="in_6")
        if st.button("Evaluar Flota", type="primary"):
            grupos = [parse_tokens(ln) for ln in text.splitlines() if ln.strip()]
            puntos, k = scenario["entregas"], scenario["k"]
            if len(grupos) != k:
                st.error(f"Debes ingresar exactamente {k} rutas (una por línea).")
            else:
                all_nodes = [n for g in grupos for n in g]
                if set(all_nodes) != set(puntos.keys()) or len(all_nodes) != len(puntos):
                    st.error("Cada punto debe ser asignado exactamente a un vehículo.")
                else:
                    makes = max(rx._largos_grupos(grupos, puntos))
                    makesb = max(rx._largos_grupos(rx._heuristica_flota(puntos, k), puntos))
                    score = rx.puntuar_min(makes, makesb)
                    st.success(f"Puntuación Obtenida: {score}/100 | Ruta más larga (Makespan): {makes:.2f} km")

    elif mission == 7:
        inp = st.text_input("Ingresa la ruta seleccionada (ej: A B E):", value="", key="in_7")
        if st.button("Evaluar Premio", type="primary"):
            order = parse_tokens(inp)
            puntos = scenario["entregas"]
            if not set(order) <= set(puntos.keys()):
                st.error("Contiene puntos no existentes.")
            else:
                dist = rx.longitud_ruta(order, puntos) if order else 0.0
                if dist > scenario["presupuesto"] + 1e-9:
                    st.error(f"Presupuesto excedido: Recorriste {dist:.2f} km del máximo permitido ({scenario['presupuesto']} km).")
                else:
                    val = sum(scenario["premio"][k] for k in order)
                    opt_val, _, _ = rx._orienteering_optimo(puntos, scenario["premio"], scenario["presupuesto"], int(stars))
                    score = rx.puntuar_max(val, opt_val)
                    st.success(f"Puntuación Obtenida: {score}/100 | Premio Recolectado: {val} | Distancia: {dist:.2f} km")
