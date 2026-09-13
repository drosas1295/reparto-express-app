import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import networkx as nx

from reparto_express import (
    generate_knapsack_scenario,
    generate_graph_scenario,
    evaluate_knapsack,
    evaluate_dijkstra,
    evaluate_orienteering
)

st.set_page_config(page_title="Reparto Express", layout="wide")

# Configuración Visual Superior
st.title("Reparto Express — Sistema de Optimización")
st.caption("Selecciona la misión, ajusta los parámetros y evalúa tu solución con precisión estricta.")

# Sidebar Controls
with st.sidebar:
    st.header("Configuración de Escenario")
    mission = st.selectbox("Misión", ["4 — Knapsack", "5 — Dijkstra", "7 — Orienteering"])
    difficulty = st.slider("Dificultad (estrellas)", 1, 5, 3)
    seed = st.number_input("Semilla (Seed)", min_value=1, max_value=9999, value=6, step=1)
    st.button("Generar escenario", use_container_width=True)

# Misión 4: Knapsack
if mission.startswith("4"):
    st.info("🎯 **Misión 4 (Knapsack)**: Selecciona los objetos que maximicen el valor total sin exceder la capacidad de peso permitida (Ejemplo: A C E).")
    items, capacity = generate_knapsack_scenario(seed, difficulty)

    col_left, col_right = st.columns([1, 1.2])

    with col_left:
        st.subheader("📦 Capacidad de la Mochila")
        st.markdown(f"# **{capacity} kg**")

    with col_right:
        st.subheader("Datos de la Misión y Respuesta")
        df_items = pd.DataFrame([
            {"Objeto": k, "Valor": v["value"], "Peso": v["weight"]} for k, v in items.items()
        ])
        st.dataframe(df_items, use_container_width=True, hide_index=True)

        user_input = st.text_input("Ingresa los objetos a llevar (ej: A B D):", key=f"input_m4_{seed}_{difficulty}")
        
        if st.button("Evaluar Mochila", type="primary"):
            selected = user_input.replace(",", " ").split()
            result = evaluate_knapsack(items, capacity, selected)
            
            if result["valid"]:
                st.success(result["message"])
            else:
                st.error(result["message"])

# Misión 5: Dijkstra
elif mission.startswith("5"):
    st.info("🎯 **Misión 5 (Dijkstra)**: Encuentra la ruta con la menor distancia/costo para conectar el punto de Origen con el Destino (Ejemplo: A B D F).")
    G, pos, _, origin, destination, _, _ = generate_graph_scenario(seed, difficulty)

    col_left, col_right = st.columns([1.2, 1])

    with col_left:
        fig, ax = plt.subplots(figsize=(6, 4))
        nx.draw_networkx_nodes(G, pos, node_color='#FACC15', node_size=300, ax=ax)
        nx.draw_networkx_labels(G, pos, font_color='black', font_weight='bold', ax=ax)
        nx.draw_networkx_edges(G, pos, edge_color='#4B5563', ax=ax)
        edge_labels = nx.get_edge_attributes(G, 'weight')
        nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_size=8, ax=ax)
        ax.set_facecolor("#0E1117")
        fig.patch.set_facecolor("#0E1117")
        st.pyplot(fig)

    with col_right:
        st.subheader("Datos de la Misión y Respuesta")
        c1, c2 = st.columns(2)
        c1.metric("Punto Origen", origin)
        c2.metric("Punto Destino", destination)

        edges_data = [{"Conexión": f"{u} <-> {v}", "Distancia": d["weight"]} for u, v, d in G.edges(data=True)]
        st.dataframe(pd.DataFrame(edges_data), use_container_width=True, hide_index=True)

        user_input = st.text_input("Ingresa la ruta de nodos (ej: A B D):", key=f"input_m5_{seed}_{difficulty}")

        if st.button("Evaluar Camino", type="primary"):
            result = evaluate_dijkstra(G, origin, destination, user_input)
            if result["valid"]:
                st.success(result["message"])
            else:
                st.error(result["message"])

# Misión 7: Orienteering
elif mission.startswith("7"):
    st.info("🎯 **Misión 7 (Orienteering)**: Tienes un límite estricto de kilómetros. Elige qué puntos visitar para obtener el mayor premio posible sin exceder el presupuesto.")
    G, pos, rewards, _, _, depot, max_dist = generate_graph_scenario(seed, difficulty)

    col_left, col_right = st.columns([1.2, 1])

    with col_left:
        fig, ax = plt.subplots(figsize=(6, 4))
        node_colors = ['#EF4444' if n == depot else '#FACC15' for n in G.nodes()]
        nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_size=350, ax=ax)
        labels = {n: f"{n} (+{rewards[n]})" if n != depot else f"{n} (Almacén)" for n in G.nodes()}
        nx.draw_networkx_labels(G, pos, labels=labels, font_size=8, font_weight='bold', ax=ax)
        nx.draw_networkx_edges(G, pos, edge_color='#4B5563', ax=ax)
        ax.set_facecolor("#0E1117")
        fig.patch.set_facecolor("#0E1117")
        st.pyplot(fig)

    with col_right:
        st.subheader("Datos de la Misión y Respuesta")
        st.metric("Presupuesto Máximo de Distancia", f"{max_dist} km")

        rew_df = pd.DataFrame([{"Punto": k, "Premio": v} for k, v in rewards.items() if k != depot])
        st.dataframe(rew_df, use_container_width=True, hide_index=True)

        user_input = st.text_input("Ingresa los puntos a visitar (ej: A B E):", key=f"input_m7_{seed}_{difficulty}")

        if st.button("Evaluar Premio", type="primary"):
            result = evaluate_orienteering(G, rewards, depot, max_dist, user_input)
            if result["valid"]:
                st.success(result["message"])
            else:
                st.error(result["message"])
