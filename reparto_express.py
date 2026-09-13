#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import argparse
import heapq
import itertools
import math
import random
import sys
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

ALMACEN: Tuple[int, int] = (0, 0)

def clamp(x: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, x))

def distancia(a: Tuple[float, float], b: Tuple[float, float]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])

def longitud_ruta(orden: Sequence[str], puntos: Dict[str, Tuple[int, int]], inicio: Tuple[int, int] = ALMACEN, fin: Tuple[int, int] = ALMACEN) -> float:
    total = 0.0
    actual = inicio
    for nombre in orden:
        total += distancia(actual, puntos[nombre])
        actual = puntos[nombre]
    total += distancia(actual, fin)
    return total

def _nombre(i: int) -> str:
    if i < 26:
        return chr(ord("A") + i)
    return chr(ord("A") + i % 26) + str(i // 26)

def gen_puntos_unicos(n: int, tam: int, semilla: Optional[int]) -> Dict[str, Tuple[int, int]]:
    rng = random.Random(semilla)
    puntos: Dict[str, Tuple[int, int]] = {}
    usados = {ALMACEN}
    i = 0
    while len(puntos) < n:
        p = (rng.randint(1, tam), rng.randint(1, tam))
        if p in usados:
            continue
        usados.add(p)
        puntos[_nombre(i)] = p
        i += 1
    return puntos

def stars_params(stars: int, base_n: int, base_tam: int) -> Tuple[int, int]:
    s = clamp(stars, 1, 5)
    mult_n = {1: 0.6, 2: 0.8, 3: 1.0, 4: 1.35, 5: 1.8}[s]
    mult_t = {1: 0.85, 2: 0.95, 3: 1.0, 4: 1.15, 5: 1.3}[s]
    n = max(3, int(round(base_n * mult_n)))
    tam = max(10, int(round(base_tam * mult_t)))
    return n, tam

def ruta_vecino_mas_cercano(puntos: Dict[str, Tuple[int, int]], inicio=ALMACEN) -> List[str]:
    pendientes = set(puntos)
    orden: List[str] = []
    actual = inicio
    while pendientes:
        siguiente = min(pendientes, key=lambda n: distancia(actual, puntos[n]))
        orden.append(siguiente)
        actual = puntos[siguiente]
        pendientes.remove(siguiente)
    return orden

def mejora_2opt(orden: Sequence[str], puntos: Dict[str, Tuple[int, int]]) -> List[str]:
    mejor = list(orden)
    mejor_dist = longitud_ruta(mejor, puntos)
    mejorado = True
    while mejorado:
        mejorado = False
        for i in range(len(mejor) - 1):
            for j in range(i + 1, len(mejor)):
                cand = mejor[:i] + mejor[i : j + 1][::-1] + mejor[j + 1 :]
                d = longitud_ruta(cand, puntos)
                if d + 1e-9 < mejor_dist:
                    mejor, mejor_dist = cand, d
                    mejorado = True
    return mejor

def ruta_experta(puntos: Dict[str, Tuple[int, int]]) -> List[str]:
    return mejora_2opt(ruta_vecino_mas_cercano(puntos), puntos)

def tsp_optimo(puntos: Dict[str, Tuple[int, int]]) -> Tuple[List[str], float]:
    nombres = list(puntos)
    if len(nombres) <= 1:
        return nombres, longitud_ruta(nombres, puntos)
    mejor: Optional[List[str]] = None
    mejor_dist = math.inf
    for perm in itertools.permutations(nombres):
        d = longitud_ruta(perm, puntos)
        if d < mejor_dist:
            mejor_dist = d
            mejor = list(perm)
    return (mejor or []), mejor_dist

def knapsack_optimo(items: Dict[str, Tuple[int, int]], capacidad: int) -> Tuple[int, set]:
    nombres = list(items)
    dp = [0] * (capacidad + 1)
    take = [[False] * (capacidad + 1) for _ in nombres]
    for idx, nombre in enumerate(nombres):
        valor, peso = items[nombre]
        for c in range(capacidad, peso - 1, -1):
            if dp[c - peso] + valor > dp[c]:
                dp[c] = dp[c - peso] + valor
                take[idx][c] = True
    sel: set = set()
    c = capacidad
    for idx in range(len(nombres) - 1, -1, -1):
        if take[idx][c]:
            nombre = nombres[idx]
            sel.add(nombre)
            c -= items[nombre][1]
    return dp[capacidad], sel

def dijkstra(grafo: Dict[str, List[Tuple[str, float]]], origen: str, destino: str) -> Tuple[float, List[str]]:
    dist = {n: math.inf for n in grafo}
    prev: Dict[str, Optional[str]] = {n: None for n in grafo}
    dist[origen] = 0.0
    pq: List[Tuple[float, str]] = [(0.0, origen)]
    while pq:
        d, u = heapq.heappop(pq)
        if d > dist[u]:
            continue
        if u == destino:
            break
        for v, w in grafo[u]:
            nd = d + w
            if nd < dist[v]:
                dist[v] = nd
                prev[v] = u
                heapq.heappush(pq, (nd, v))
    if math.isinf(dist[destino]):
        return math.inf, []
    path: List[str] = []
    cur: Optional[str] = destino
    while cur is not None:
        path.append(cur)
        cur = prev[cur]
    path.reverse()
    return dist[destino], path

def puntuar_min(jugador: float, baseline: float) -> int:
    if jugador <= 0: return 100
    return max(0, min(100, round(baseline / jugador * 100)))

def puntuar_max(jugador: float, optimo: float) -> int:
    if optimo <= 0: return 100
    return max(0, min(100, round(jugador / optimo * 100)))

def preparar_tsp(semilla: Optional[int], stars: int) -> Dict:
    n, tam = stars_params(stars, base_n=5, base_tam=20)
    n = clamp(n, 4, 12)
    return {"entregas": gen_puntos_unicos(n, tam, semilla), "tam": tam, "stars": stars}

def preparar_cvrp(semilla: Optional[int], stars: int) -> Dict:
    rng = random.Random(semilla)
    n, tam = stars_params(stars, base_n=6, base_tam=20)
    n = clamp(n, 5, 14)
    entregas = gen_puntos_unicos(n, tam, semilla)
    d_lo = {1: 1, 2: 1, 3: 2, 4: 2, 5: 3}[stars]
    d_hi = {1: 4, 2: 5, 3: 6, 4: 7, 5: 9}[stars]
    demanda = {k: rng.randint(d_lo, d_hi) for k in entregas}
    total = sum(demanda.values())
    ratio = {1: 0.55, 2: 0.50, 3: 0.45, 4: 0.40, 5: 0.35}[stars]
    cap = max(max(demanda.values()) + 2, int(round(total * ratio)))
    return {"entregas": entregas, "demanda": demanda, "capacidad": cap, "tam": tam, "stars": stars}

def _heuristica_cvrp(entregas, demanda, capacidad):
    pendientes = set(entregas)
    viajes = []
    while pendientes:
        viaje, carga, actual = [], 0, ALMACEN
        while True:
            candidatos = [n for n in pendientes if carga + demanda[n] <= capacidad]
            if not candidatos:
                break
            s = min(candidatos, key=lambda n: distancia(actual, entregas[n]))
            viaje.append(s)
            carga += demanda[s]
            actual = entregas[s]
            pendientes.remove(s)
        viajes.append(viaje)
    return viajes

def preparar_vrptw(semilla: Optional[int], stars: int) -> Dict:
    rng = random.Random(semilla)
    n, tam = stars_params(stars, base_n=5, base_tam=20)
    n = clamp(n, 4, 12)
    entregas = gen_puntos_unicos(n, tam, semilla)
    base_in = {1: 0, 2: 0, 3: 0, 4: 1, 5: 2}[stars]
    in_max = {1: 5, 2: 6, 3: 6, 4: 7, 5: 8}[stars]
    ancho_lo = {1: 8, 2: 7, 3: 6, 4: 5, 5: 4}[stars]
    ancho_hi = {1: 12, 2: 10, 3: 9, 4: 8, 5: 6}[stars]
    ventanas = {}
    for k in entregas:
        ini = rng.randint(base_in, in_max)
        ancho = rng.randint(ancho_lo, ancho_hi)
        ventanas[k] = (ini, ini + ancho)
    vel = {1: 6.0, 2: 5.5, 3: 5.0, 4: 4.7, 5: 4.3}[stars]
    pen = {1: 3.0, 2: 4.0, 3: 5.0, 4: 6.5, 5: 8.0}[stars]
    return {"entregas": entregas, "ventanas": ventanas, "velocidad": vel, "pen": pen, "tam": tam, "stars": stars}

def _sim_vrptw(orden, e, v, vel):
    t = 0.0
    actual = ALMACEN
    dist = 0.0
    tard = 0.0
    lleg = {}
    for k in orden:
        d = distancia(actual, e[k])
        dist += d
        t += d / vel
        ini, fin = v[k]
        if t < ini: t = float(ini)
        if t > fin: tard += t - fin
        lleg[k] = t
        actual = e[k]
    dist += distancia(actual, ALMACEN)
    return dist, tard, lleg

def preparar_mochila(semilla: Optional[int], stars: int) -> Dict:
    rng = random.Random(semilla)
    n = clamp(int(round({1: 5, 2: 6, 3: 7, 4: 9, 5: 11}[stars])), 5, 14)
    items: Dict[str, Tuple[int, int]] = {}
    v_lo, v_hi = {1: (5, 18), 2: (5, 22), 3: (5, 25), 4: (8, 35), 5: (10, 45)}[stars]
    p_lo, p_hi = {1: (1, 7), 2: (2, 9), 3: (2, 10), 4: (3, 12), 5: (3, 14)}[stars]
    for i in range(n):
        items[_nombre(i)] = (rng.randint(v_lo, v_hi), rng.randint(p_lo, p_hi))
    peso_total = sum(p for _, p in items.values())
    ratio = {1: 0.60, 2: 0.55, 3: 0.50, 4: 0.45, 5: 0.40}[stars]
    cap = max(5, int(round(peso_total * ratio)))
    return {"items": items, "capacidad": cap, "stars": stars}

def preparar_dijkstra(semilla: Optional[int], stars: int) -> Dict:
    rng = random.Random(semilla)
    n = clamp(int(round({1: 6, 2: 7, 3: 8, 4: 10, 5: 12}[stars])), 6, 14)
    tam = clamp(int(round({1: 14, 2: 16, 3: 18, 4: 20, 5: 22}[stars])), 12, 26)
    puntos = gen_puntos_unicos(n, tam, semilla)
    nombres = list(puntos)
    extra_edges = {1: 2, 2: 3, 3: 4, 4: 6, 5: 8}[stars]
    aristas: Dict[frozenset, float] = {}
    conectados = [nombres[0]]
    for nombre in nombres[1:]:
        vecino = rng.choice(conectados)
        w = round(distancia(puntos[nombre], puntos[vecino]), 1)
        aristas[frozenset((nombre, vecino))] = w
        conectados.append(nombre)
    intentos = 0
    while len(aristas) < (n - 1) + extra_edges and intentos < 200:
        a, b = rng.sample(nombres, 2)
        key = frozenset((a, b))
        if key not in aristas:
            w = round(distancia(puntos[a], puntos[b]), 1)
            if stars >= 4:
                w = round(w * rng.uniform(0.8, 1.25), 1)
            aristas[key] = w
        intentos += 1
    grafo: Dict[str, List[Tuple[str, float]]] = {k: [] for k in nombres}
    for key, w in aristas.items():
        a, b = tuple(key)
        grafo[a].append((b, w))
        grafo[b].append((a, w))
    origen, destino = nombres[0], nombres[-1]
    return {"puntos": puntos, "aristas": aristas, "grafo": grafo, "origen": origen, "destino": destino, "tam": tam, "stars": stars}

def preparar_flota(semilla: Optional[int], stars: int) -> Dict:
    n, tam = stars_params(stars, base_n=7, base_tam=20)
    n = clamp(n, 6, 18)
    k = {1: 3, 2: 3, 3: 2, 4: 2, 5: 2}[stars]
    return {"entregas": gen_puntos_unicos(n, tam, semilla), "k": k, "tam": tam, "stars": stars}

def _heuristica_flota(entregas: Dict[str, Tuple[int, int]], k: int) -> List[List[str]]:
    nombres = sorted(entregas, key=lambda n: math.atan2(entregas[n][1], entregas[n][0]))
    grupos: List[List[str]] = [[] for _ in range(k)]
    for i, n in enumerate(nombres):
        grupos[i % k].append(n)
    return grupos

def _largos_grupos(grupos: List[List[str]], entregas: Dict[str, Tuple[int, int]]) -> List[float]:
    largos = []
    for g in grupos:
        if not g:
            largos.append(0.0)
            continue
        sub = {n: entregas[n] for n in g}
        orden = ruta_experta(sub)
        largos.append(longitud_ruta(orden, entregas))
    return largos

def preparar_orienteering(semilla: Optional[int], stars: int) -> Dict:
    rng = random.Random(semilla)
    n, tam = stars_params(stars, base_n=7, base_tam=20)
    n = clamp(n, 6, 14)
    entregas = gen_puntos_unicos(n, tam, semilla)
    premio_lo, premio_hi = {1: (10, 35), 2: (10, 45), 3: (10, 50), 4: (15, 70), 5: (20, 90)}[stars]
    premio = {k: rng.randint(premio_lo, premio_hi) for k in entregas}
    ruta_total = longitud_ruta(ruta_experta(entregas), entregas)
    ratio = {1: 0.75, 2: 0.70, 3: 0.60, 4: 0.50, 5: 0.42}[stars]
    pres = round(ruta_total * ratio, 1)
    return {"entregas": entregas, "premio": premio, "presupuesto": pres, "tam": tam, "stars": stars}

def _orienteering_optimo(entregas, premio, presupuesto, stars: int) -> Tuple[int, List[str], float]:
    nombres = list(entregas)
    rmax = {1: 6, 2: 7, 3: 8, 4: 9, 5: 10}[stars]
    rmax = min(rmax, len(nombres))
    best_val, best_ord, best_dist = 0, [], 0.0
    for r in range(1, rmax + 1):
        for sub in itertools.combinations(nombres, r):
            val = sum(premio[n] for n in sub)
            if val <= best_val: continue
            sub_pts = {n: entregas[n] for n in sub}
            ord2 = ruta_experta(sub_pts)
            dist = longitud_ruta(ord2, sub_pts)
            if dist <= presupuesto + 1e-9:
                best_val, best_ord, best_dist = val, ord2, dist
    return best_val, best_ord, best_dist
