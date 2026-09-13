import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import networkx as nx
import random

from reparto_express import (
    generate_basic_scenario, generate_knapsack_scenario, generate_graph_scenario,
    evaluate_mission_1_sorting, evaluate_mission_2_search, evaluate_mission_3_tsp,
    evaluate_knapsack, evaluate_dijkstra, evaluate_mst, evaluate_orienteering
)

st.set_page_config(page_title="Reparto Express", layout="wide")

st.title("Reparto Express — Sistema de Optimización")
st.caption("Selecciona la misión, ajusta los parámetros y evalúa tu solución con precisión estricta.")

# Sidebar Controls
with st.sidebar:
    st.header("Configuración de Escenario")
    mission = st.selectbox("Misión", [
        "1 — Ordenamiento", 
        "2 — Búsqueda", 
        "3 — Agente Viajero (TSP)", 
        "4 — Knapsack (Mochila)", 
        "5 — Dijkstra (Ruta Corta)", 
        "6 — Red Óptima (MST)", 
        "7 — Orienteering"
    ])
    difficulty = st.slider("Dificultad (estrellas)", 1, 5, 3)
    seed = st.number_input("Semilla (Seed)", min_value=1, max_value=9999, value=6, step=1)
    st.button("Generar escenario", use_container_width=True)

# Helper function to plot graphs (reusable for missions 3, 5, 6, 7)
def plot_graph(G, pos, highlight_nodes=None):
    fig, ax = plt.subplots(figsize=(6, 4))
    node_colors = ['#EF4444' if n in (highlight_nodes or []) else '#FACC15' for n in G.nodes()]
    nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_size=300, ax=ax)
    nx.draw_networkx_labels(G, pos, font_color='black', font_weight='bold', font_size=9, ax=ax)
    nx.draw_networkx_edges(G, pos, edge_color='#4B5563', ax=ax)
    edge_labels = nx.get_edge_attributes(G, 'weight')
    nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_size=8, font_color="black", 
                                 bbox=dict(facecolor='white', edgecolor='none', alpha=0.7, pad=0.5), ax=ax)
    ax.set_facecolor("#0E1117")
    fig.patch.set_facecolor("#0E1117")
    return fig

# ==========================================
# VISTAS DE MISIONES
# ==========================================

if mission.startswith("1"):
    st.info("🎯 **Misión 1 (Ordenamiento)**: Ordena los siguientes paquetes desde la prioridad más alta a la más baja.")
    packages = generate_basic_scenario(seed, difficulty)
    st.dataframe(pd.DataFrame(packages), use_container_width=True, hide_index=True)
    user_input = st.text_input("Ingresa los IDs de los paquetes en orden (ej: PKG-123 PKG-456):", key=f"m1_{seed}_{difficulty}")
    if st.button("Evaluar Orden", type="primary"):
        res = evaluate_mission_1_sorting(packages, user_input)
        st.success(res["message"]) if res["valid"] else st.error(res["message"])

elif mission.startswith("2"):
    st.info("🎯 **Misión 2 (Búsqueda)**: Encuentra el ID del paquete que coincida exactamente con el peso solicitado.")
    packages = generate_basic_scenario(seed, difficulty)
    target_weight = random.Random(seed).choice(packages)["weight"]
    st.metric("Peso a buscar", f"{target_weight} kg")
    st.dataframe(pd.DataFrame(packages), use_container_width=True, hide_index=True)
    user_input = st.text_input("Ingresa el ID del paquete encontrado (ej: PKG-123):", key=f"m2_{seed}_{difficulty}")
    if st.button("Evaluar Búsqueda", type="primary"):
        res = evaluate_mission_2_search(packages, target_weight, user_input)
        st.success(res["message"]) if res["valid"] else st.error(res["message"])

elif mission.startswith("3"):
    st.info("🎯 **Misión 3 (TSP)**: Encuentra la ruta más corta que inicie en el almacén, visite TODOS los puntos y regrese al almacén.")
    G, pos, _, _, _, depot, _ = generate_graph_scenario(seed, difficulty)
    col1, col2 = st.columns([1.2, 1])
    with col1: st.pyplot(plot_graph(G, pos, highlight_nodes=[depot]))
    with col2:
        st.metric("Almacén de origen/destino", depot)
        edges_data = [{"Conexión": f"{u} <-> {v}", "Distancia": d["weight"]} for u, v, d in G.edges(data=True)]
        st.dataframe(pd.DataFrame(edges_data), use_container_width=True, hide_index=True)
        user_input = st.text_input("Ingresa la ruta (ej: A B C D A):", key=f"m3_{seed}_{difficulty}")
        if st.button("Evaluar Ruta Completa", type="primary"):
            res = evaluate_mission_3_tsp(G, depot, user_input)
            st.success(res["message"]) if res["valid"] else st.error(res["message"])

elif mission.startswith("4"):
    st.info("🎯 **Misión 4 (Knapsack)**: Selecciona los objetos que maximicen el valor sin exceder la capacidad de peso.")
    items, capacity = generate_knapsack_scenario(seed, difficulty)
    col1, col2 = st.columns([1, 1.2])
    with col1: st.metric("📦 Capacidad", f"{capacity} kg")
    with col2:
        df_items = pd.DataFrame([{"Objeto": k, "Valor": v["value"], "Peso": v["weight"]} for k, v in items.items()])
        st.dataframe(df_items, use_container_width=True, hide_index=True)
        user_input = st.text_input("Ingresa los objetos a llevar (ej: A B D):", key=f"m4_{seed}_{difficulty}")
        if st.button("Evaluar Mochila", type="primary"):
            res = evaluate_knapsack(items, capacity, user_input)
            st.success(res["message"]) if res["valid"] else st.error(res["message"])

elif mission.startswith("5"):
    st.info("🎯 **Misión 5 (Dijkstra)**: Encuentra la ruta con la menor distancia/costo para conectar el punto de Origen con el Destino.")
    G, pos, _, origin, destination, _, _ = generate_graph_scenario(seed, difficulty)
    col1, col2 = st.columns([1.2, 1])
    with col1: st.pyplot(plot_graph(G, pos, highlight_nodes=[origin, destination]))
    with col2:
        c1, c2 = st.columns(2)
        c1.metric("Punto Origen", origin)
        c2.metric("Punto Destino", destination)
        edges_data = [{"Conexión": f"{u} <-> {v}", "Distancia": d["weight"]} for u, v, d in G.edges(data=True)]
        st.dataframe(pd.DataFrame(edges_data), use_container_width=True, hide_index=True)
        user_input = st.text_input("Ingresa la ruta de nodos (ej: A B D):", key=f"m5_{seed}_{difficulty}")
        if st.button("Evaluar Camino", type="primary"):
            res = evaluate_dijkstra(G, origin, destination, user_input)
            st.success(res["message"]) if res["valid"] else st.error(res["message"])

elif mission.startswith("6"):
    st.info("🎯 **Misión 6 (MST)**: Conecta todos los puntos del mapa gastando la menor cantidad de kilómetros de cable. No crees ciclos cerrados.")
    G, pos, _, _, _, _, _ = generate_graph_scenario(seed, difficulty)
    col1, col2 = st.columns([1.2, 1])
    with col1: st.pyplot(plot_graph(G, pos))
    with col2:
        edges_data = [{"Conexión": f"{u} <-> {v}", "Distancia": d["weight"]} for u, v, d in G.edges(data=True)]
        st.dataframe(pd.DataFrame(edges_data), use_container_width=True, hide_index=True)
        user_input = st.text_input("Ingresa los pares de nodos a conectar (ej: AB BC CD):", key=f"m6_{seed}_{difficulty}")
        if st.button("Evaluar Red", type="primary"):
            res = evaluate_mst(G, user_input)
            st.success(res["message"]) if res["valid"] else st.error(res["message"])

elif mission.startswith("7"):
    st.info("🎯 **Misión 7 (Orienteering)**: Tienes un presupuesto límite. Visita los puntos que otorguen el mayor premio sin exceder los kilómetros permitidos.")
    G, pos, rewards, _, _, depot, max_dist = generate_graph_scenario(seed, difficulty)
    col1, col2 = st.columns([1.2, 1])
    with col1: st.pyplot(plot_graph(G, pos, highlight_nodes=[depot]))
    with col2:
        st.metric("Presupuesto Máximo", f"{max_dist} km")
        rew_df = pd.DataFrame([{"Punto": k, "Premio": v} for k, v in rewards.items() if k != depot])
        st.dataframe(rew_df, use_container_width=True, hide_index=True)
        user_input = st.text_input("Ingresa los puntos a visitar (ej: A B E):", key=f"m7_{seed}_{difficulty}")
        if st.button("Evaluar Premio", type="primary"):
            res = evaluate_orienteering(G, rewards, depot, max_dist, user_input)
            st.success(res["message"]) if res["valid"] else st.error(res["message"])
