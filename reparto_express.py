import random
import math
import networkx as nx
import itertools

# ==========================================
# GENERADORES DE ESCENARIOS
# ==========================================

def generate_knapsack_scenario(seed, difficulty):
    """Genera datos deterministas para la Misión 4."""
    random.seed(seed)
    num_items = 3 + difficulty
    capacity = 15 + difficulty * 4
    
    labels = [chr(65 + i) for i in range(num_items)]
    items = {}
    for label in labels:
        items[label] = {
            "value": random.randint(10, 50),
            "weight": random.randint(2, 12)
        }
    return items, capacity

def generate_graph_scenario(seed, difficulty):
    """Genera grafos euclidianos conexos para Misiones 5 y 7."""
    random.seed(seed)
    num_nodes = 5 + difficulty
    labels = [chr(65 + i) for i in range(num_nodes)]
    
    positions = {}
    for label in labels:
        positions[label] = (random.randint(1, 20), random.randint(1, 20))

    G = nx.Graph()
    for label in labels:
        G.add_node(label, pos=positions[label])

    # Garantizar conectividad mediante árbol de expansión
    for i in range(1, num_nodes):
        target = labels[random.randint(0, i - 1)]
        u_pos, v_pos = positions[labels[i]], positions[target]
        dist = round(math.hypot(u_pos[0] - v_pos[0], u_pos[1] - v_pos[1]), 1)
        G.add_edge(labels[i], target, weight=max(1.0, dist))

    # Añadir conexiones secundarias
    for i in range(num_nodes):
        for j in range(i + 1, num_nodes):
            if not G.has_edge(labels[i], labels[j]) and random.random() < 0.35:
                u_pos, v_pos = positions[labels[i]], positions[labels[j]]
                dist = round(math.hypot(u_pos[0] - v_pos[0], u_pos[1] - v_pos[1]), 1)
                G.add_edge(labels[i], labels[j], weight=max(1.0, dist))

    rewards = {label: random.randint(15, 50) for label in labels}
    depot = labels[-1]
    rewards[depot] = 0 # El almacén no otorga premio

    # Calcular presupuesto razonable para orienteering
    max_dist = round(sum(d["weight"] for u, v, d in G.edges(data=True)) / (1.8 + (difficulty * 0.2)), 1)

    return G, positions, rewards, labels[0], labels[1], depot, max_dist


# ==========================================
# EVALUADORES Y SOLVERS
# ==========================================

def evaluate_knapsack(items_dict, capacity, user_selected_ids):
    """Evalúa la Misión 4: Knapsack."""
    user_ids = [idx.strip().upper() for idx in user_selected_ids if idx.strip()]
    invalid_ids = [idx for idx in user_ids if idx not in items_dict]
    
    if invalid_ids:
        return {
            "valid": False, "score": 0, "user_value": 0, "user_weight": 0, "opt_value": 0,
            "message": f"❌ Objeto(s) no válido(s): {', '.join(invalid_ids)}"
        }

    user_weight = sum(items_dict[idx]["weight"] for idx in user_ids)
    user_value = sum(items_dict[idx]["value"] for idx in user_ids)

    # Solver Exacto
    item_keys = list(items_dict.keys())
    opt_value = 0
    for r in range(len(item_keys) + 1):
        for combo in itertools.combinations(item_keys, r):
            w = sum(items_dict[k]["weight"] for k in combo)
            v = sum(items_dict[k]["value"] for k in combo)
            if w <= capacity and v > opt_value:
                opt_value = v

    if user_weight > capacity:
        return {
            "valid": False, "score": 0, "user_value": user_value, "user_weight": user_weight, "opt_value": opt_value,
            "message": f"❌ Presupuesto de peso excedido: {user_weight} kg cargados de {capacity} kg permitidos."
        }

    score = 100 if opt_value == 0 else min(100, int(round((user_value / opt_value) * 100)))

    return {
        "valid": True, "score": score, "user_value": user_value, "user_weight": user_weight, "opt_value": opt_value,
        "message": f"✅ Puntuación Obtenida: {score}/100 | Valor: {user_value}/{opt_value} | Peso: {user_weight}/{capacity} kg"
    }


def evaluate_dijkstra(graph, origin, destination, user_path_str):
    """Evalúa la Misión 5: Dijkstra."""
    nodes = [n.strip().upper() for n in user_path_str.replace("->", " ").replace("-", " ").split() if n.strip()]

    if not nodes or nodes[0] != origin or nodes[-1] != destination:
        return {
            "valid": False, "score": 0, "user_dist": 0.0, "opt_dist": 0.0,
            "message": f"❌ La ruta debe iniciar en '{origin}' y finalizar en '{destination}'."
        }

    user_dist = 0.0
    for i in range(len(nodes) - 1):
        u, v = nodes[i], nodes[i+1]
        if graph.has_edge(u, v):
            user_dist += graph[u][v]["weight"]
        else:
            return {
                "valid": False, "score": 0, "user_dist": 0.0, "opt_dist": 0.0,
                "message": f"❌ Conexión inexistente en el grafo entre '{u}' y '{v}'."
            }

    try:
        opt_dist = nx.dijkstra_path_length(graph, origin, destination, weight="weight")
    except nx.NetworkXNoPath:
        return {"valid": False, "score": 0, "user_dist": 0.0, "opt_dist": 0.0, "message": "❌ No existe ruta disponible."}

    if abs(user_dist - opt_dist) < 1e-4:
        score = 100
    else:
        score = max(0, int(round((opt_dist / user_dist) * 100)))

    return {
        "valid": True, "score": score, "user_dist": round(user_dist, 2), "opt_dist": round(opt_dist, 2),
        "message": f"✅ Puntuación Obtenida: {score}/100 | Distancia: {user_dist:.2f} km (Óptima: {opt_dist:.2f} km)"
    }


def evaluate_orienteering(graph, rewards, depot, max_distance, user_nodes_str):
    """Evalúa la Misión 7: Orienteering Problem."""
    raw_nodes = [n.strip().upper() for n in user_nodes_str.replace("->", " ").replace("-", " ").split() if n.strip()]
    
    visited_nodes = []
    for n in raw_nodes:
        if n != depot and n not in visited_nodes:
            visited_nodes.append(n)

    full_route = [depot] + visited_nodes + [depot]

    total_dist = 0.0
    for i in range(len(full_route) - 1):
        u, v = full_route[i], full_route[i+1]
        if graph.has_edge(u, v):
            total_dist += graph[u][v]["weight"]
        else:
            return {
                "valid": False, "score": 0, "user_reward": 0, "total_dist": 0.0,
                "message": f"❌ Tramo no conectado en el mapa: '{u}' a '{v}'."
            }

    if total_dist > max_distance:
        return {
            "valid": False, "score": 0, "user_reward": 0, "total_dist": round(total_dist, 2),
            "message": f"❌ Presupuesto excedido: Recorriste {total_dist:.2f} km del máximo permitido ({max_distance:.2f} km)."
        }

    user_reward = sum(rewards.get(n, 0) for n in visited_nodes)

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
                rew = sum(rewards.get(n, 0) for n in perm)
                if rew > opt_reward:
                    opt_reward = rew

    score = 100 if opt_reward == 0 else min(100, int(round((user_reward / opt_reward) * 100)))

    return {
        "valid": True, "score": score, "user_reward": user_reward, "opt_reward": opt_reward, "total_dist": round(total_dist, 2),
        "message": f"✅ Puntuación Obtenida: {score}/100 | Premio: {user_reward}/{opt_reward} | Distancia: {total_dist:.2f}/{max_distance:.2f} km"
    }
