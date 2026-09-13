import random
import math
import networkx as nx
import itertools

# ==========================================
# 1. GENERADORES DE ESCENARIOS
# ==========================================

def generate_basic_scenario(seed, difficulty):
    """Genera listas de paquetes para las misiones 1, 2 y 3."""
    random.seed(seed)
    num_items = 5 + (difficulty * 2)
    packages = []
    for i in range(num_items):
        packages.append({
            "id": f"PKG-{random.randint(100, 999)}",
            "weight": random.randint(1, 20),
            "priority": random.randint(1, 5)
        })
    return packages

def generate_knapsack_scenario(seed, difficulty):
    """Genera datos deterministas para la Misión 4 (Knapsack)."""
    random.seed(seed)
    num_items = 4 + difficulty
    capacity = 15 + difficulty * 3
    labels = [chr(65 + i) for i in range(num_items)]
    items = {label: {"value": random.randint(10, 50), "weight": random.randint(2, 12)} for label in labels}
    return items, capacity

def generate_graph_scenario(seed, difficulty):
    """Genera grafos euclidianos conexos para Misiones 5, 6 y 7."""
    random.seed(seed)
    num_nodes = 5 + difficulty
    labels = [chr(65 + i) for i in range(num_nodes)]
    
    positions = {label: (random.randint(1, 20), random.randint(1, 20)) for label in labels}
    G = nx.Graph()
    for label in labels:
        G.add_node(label, pos=positions[label])

    # Árbol de expansión para garantizar conectividad
    for i in range(1, num_nodes):
        target = labels[random.randint(0, i - 1)]
        u_pos, v_pos = positions[labels[i]], positions[target]
        dist = round(math.hypot(u_pos[0] - v_pos[0], u_pos[1] - v_pos[1]), 1)
        G.add_edge(labels[i], target, weight=max(1.0, dist))

    # Conexiones adicionales
    for i in range(num_nodes):
        for j in range(i + 1, num_nodes):
            if not G.has_edge(labels[i], labels[j]) and random.random() < 0.35:
                u_pos, v_pos = positions[labels[i]], positions[labels[j]]
                dist = round(math.hypot(u_pos[0] - v_pos[0], u_pos[1] - v_pos[1]), 1)
                G.add_edge(labels[i], labels[j], weight=max(1.0, dist))

    rewards = {label: random.randint(15, 50) for label in labels}
    depot = labels[-1]
    rewards[depot] = 0
    max_dist = round(sum(d["weight"] for _, _, d in G.edges(data=True)) / (1.8 + (difficulty * 0.2)), 1)

    return G, positions, rewards, labels[0], labels[1], depot, max_dist

# ==========================================
# 2. EVALUADORES Y SOLVERS
# ==========================================

def evaluate_mission_1_sorting(packages, user_input):
    """Misión 1: Ordenar paquetes por prioridad (mayor a menor)."""
    correct_order = [p["id"] for p in sorted(packages, key=lambda x: x["priority"], reverse=True)]
    user_order = [x.strip() for x in user_input.replace(",", " ").split() if x.strip()]
    
    if user_order == correct_order:
        return {"valid": True, "score": 100, "message": "✅ ¡Perfecto! Ordenaste los paquetes correctamente."}
    return {"valid": False, "score": 0, "message": f"❌ Orden incorrecto. El correcto era: {' '.join(correct_order)}"}

def evaluate_mission_2_search(packages, target_weight, user_input):
    """Misión 2: Encontrar el ID del paquete con un peso específico."""
    correct_pkg = next((p["id"] for p in packages if p["weight"] == target_weight), None)
    if user_input.strip() == correct_pkg:
        return {"valid": True, "score": 100, "message": "✅ ¡Exacto! Encontraste el paquete correcto."}
    return {"valid": False, "score": 0, "message": f"❌ Incorrecto. El paquete buscado era: {correct_pkg}"}

def evaluate_mission_3_tsp(graph, depot, user_path_str):
    """Misión 3: Agente Viajero (TSP) - Visitar todos y volver al origen."""
    nodes = [n.strip().upper() for n in user_path_str.replace("->", " ").replace("-", " ").split() if n.strip()]
    
    if not nodes or nodes[0] != depot or nodes[-1] != depot:
        return {"valid": False, "score": 0, "message": f"❌ La ruta debe iniciar y terminar en el almacén '{depot}'."}
    
    visited = set(nodes)
    if len(visited) != len(graph.nodes):
        return {"valid": False, "score": 0, "message": "❌ Debes visitar TODOS los nodos del mapa."}

    user_dist = 0.0
    for i in range(len(nodes) - 1):
        if graph.has_edge(nodes[i], nodes[i+1]):
            user_dist += graph[nodes[i]][nodes[i+1]]["weight"]
        else:
            return {"valid": False, "score": 0, "message": f"❌ Conexión inexistente: '{nodes[i]}' a '{nodes[i+1]}'."}

    # Aproximación óptima usando heurística simple para puntuar
    approx_tsp = nx.approximation.traveling_salesman_problem(graph, weight="weight")
    opt_dist = sum(graph[approx_tsp[i]][approx_tsp[i+1]]["weight"] for i in range(len(approx_tsp)-1))
    
    score = min(100, max(0, int(round((opt_dist / user_dist) * 100))))
    return {"valid": True, "score": score, "message": f"✅ Puntuación: {score}/100 | Distancia: {user_dist:.2f} km"}

def evaluate_knapsack(items_dict, capacity, user_selected_ids):
    """Misión 4: Mochila 0/1 (Knapsack)."""
    user_ids = [idx.strip().upper() for idx in user_selected_ids if idx.strip()]
    invalid_ids = [idx for idx in user_ids if idx not in items_dict]
    if invalid_ids:
        return {"valid": False, "score": 0, "message": f"❌ Objeto(s) no válido(s): {', '.join(invalid_ids)}"}

    user_weight = sum(items_dict[idx]["weight"] for idx in user_ids)
    user_value = sum(items_dict[idx]["value"] for idx in user_ids)

    # Solver Exacto
    opt_value = 0
    item_keys = list(items_dict.keys())
    for r in range(len(item_keys) + 1):
        for combo in itertools.combinations(item_keys, r):
            if sum(items_dict[k]["weight"] for k in combo) <= capacity:
                opt_value = max(opt_value, sum(items_dict[k]["value"] for k in combo))

    if user_weight > capacity:
        return {"valid": False, "score": 0, "message": f"❌ Peso excedido: {user_weight} kg cargados de {capacity} kg."}

    score = 100 if opt_value == 0 else min(100, int(round((user_value / opt_value) * 100)))
    return {"valid": True, "score": score, "message": f"✅ Puntuación: {score}/100 | Valor: {user_value}/{opt_value} | Peso: {user_weight}/{capacity} kg"}

def evaluate_dijkstra(graph, origin, destination, user_path_str):
    """Misión 5: Ruta más corta (Dijkstra)."""
    nodes = [n.strip().upper() for n in user_path_str.replace("->", " ").replace("-", " ").split() if n.strip()]
    if not nodes or nodes[0] != origin or nodes[-1] != destination:
        return {"valid": False, "score": 0, "message": f"❌ La ruta debe iniciar en '{origin}' y finalizar en '{destination}'."}

    user_dist = 0.0
    for i in range(len(nodes) - 1):
        if graph.has_edge(nodes[i], nodes[i+1]):
            user_dist += graph[nodes[i]][nodes[i+1]]["weight"]
        else:
            return {"valid": False, "score": 0, "message": f"❌ Conexión inexistente: '{nodes[i]}' a '{nodes[i+1]}'."}

    try:
        opt_dist = nx.dijkstra_path_length(graph, origin, destination, weight="weight")
    except nx.NetworkXNoPath:
        return {"valid": False, "score": 0, "message": "❌ No existe ruta disponible."}

    score = 100 if abs(user_dist - opt_dist) < 1e-4 else max(0, int(round((opt_dist / user_dist) * 100)))
    return {"valid": True, "score": score, "message": f"✅ Puntuación: {score}/100 | Distancia: {user_dist:.2f} km (Óptima: {opt_dist:.2f} km)"}

def evaluate_mst(graph, user_edges_str):
    """Misión 6: Árbol de Expansión Mínima (MST)."""
    # Formato esperado: AB CD EF
    raw_edges = [e.strip().upper() for e in user_edges_str.split() if len(e.strip()) == 2]
    user_dist = 0.0
    user_G = nx.Graph()
    
    for e in raw_edges:
        u, v = e[0], e[1]
        if graph.has_edge(u, v):
            user_dist += graph[u][v]["weight"]
            user_G.add_edge(u, v)
        else:
            return {"valid": False, "score": 0, "message": f"❌ La conexión {u}-{v} no existe en el mapa."}

    if not nx.is_connected(user_G) or len(user_G.nodes) != len(graph.nodes):
        return {"valid": False, "score": 0, "message": "❌ Tus conexiones no enlazan todos los puntos del mapa (No es un árbol que cubra todo)."}
    
    if len(user_G.edges) != len(graph.nodes) - 1:
        return {"valid": False, "score": 0, "message": "❌ Has creado ciclos cerrados. Un árbol de expansión no debe tener bucles."}

    mst = nx.minimum_spanning_tree(graph, weight="weight")
    opt_dist = sum(d["weight"] for u, v, d in mst.edges(data=True))
    
    score = 100 if abs(user_dist - opt_dist) < 1e-4 else max(0, int(round((opt_dist / user_dist) * 100)))
    return {"valid": True, "score": score, "message": f"✅ Puntuación: {score}/100 | Costo cableado: {user_dist:.2f} (Óptimo: {opt_dist:.2f})"}

def evaluate_orienteering(graph, rewards, depot, max_distance, user_nodes_str):
    """Misión 7: Orienteering (Rutas con límite de presupuesto)."""
    raw_nodes = [n.strip().upper() for n in user_nodes_str.replace("->", " ").replace("-", " ").split() if n.strip()]
    visited_nodes = []
    for n in raw_nodes:
        if n != depot and n not in visited_nodes:
            visited_nodes.append(n)

    full_route = [depot] + visited_nodes + [depot]
    total_dist = 0.0
    for i in range(len(full_route) - 1):
        if graph.has_edge(full_route[i], full_route[i+1]):
            total_dist += graph[full_route[i]][full_route[i+1]]["weight"]
        else:
            return {"valid": False, "score": 0, "message": f"❌ Tramo no conectado: '{full_route[i]}' a '{full_route[i+1]}'"}

    if total_dist > max_distance:
        return {"valid": False, "score": 0, "message": f"❌ Presupuesto excedido: {total_dist:.2f} km de {max_distance:.2f} km."}

    user_reward = sum(rewards.get(n, 0) for n in visited_nodes)

    # Solver Exacto Orienteering
    all_targets = [n for n in graph.nodes() if n != depot]
    opt_reward = 0
    for r in range(len(all_targets) + 1):
        for perm in itertools.permutations(all_targets, r):
            route = [depot] + list(perm) + [depot]
            d = 0.0
            possible = True
            for i in range(len(route) - 1):
                if graph.has_edge(route[i], route[i+1]):
                    d += graph[route[i]][route[i+1]]["weight"]
                else:
                    possible = False
                    break
            if possible and d <= max_distance:
                opt_reward = max(opt_reward, sum(rewards.get(n, 0) for n in perm))

    score = 100 if opt_reward == 0 else min(100, int(round((user_reward / opt_reward) * 100)))
    return {"valid": True, "score": score, "message": f"✅ Puntuación: {score}/100 | Premio: {user_reward}/{opt_reward} | Distancia: {total_dist:.2f}/{max_distance:.2f} km"}
