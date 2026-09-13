# reparto_express.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Reparto Express 2.2 (Colab-friendly) - Simulador de Logística
===============================================================

Juego educativo de optimización con 7 misiones:
1) Ruta Clásica (TSP)
2) Carga Limitada (CVRP)
3) Ventanas de Tiempo (VRPTW)
4) La Mochila (Knapsack 0/1)
5) Camino más Corto (Dijkstra)
6) Flota en Equipo (minimizar la ruta más larga)
7) Ruta con Presupuesto (Orienteering)

MEJORAS para Google Colab y CLI:
- Dificultad por estrellas (1..5) para TODAS las misiones: --stars
- Visualización opcional con Matplotlib (mapa + ruta/solución): --plot

Uso típico:
  python3 reparto_express.py --mision 1 --stars 3 --plot
  python3 reparto_express.py --mision 7 --stars 5 --plot
  python3 reparto_express.py --demo --stars 3 --plot
  python3 reparto_express.py --test
"""

from __future__ import annotations

import argparse
import heapq
import itertools
import math
import random
import sys
from typing import Dict, Iterable, List, Sequence, Tuple, Set

ALMACEN: Tuple[int, int] = (0, 0)


# ===========================================================================
# Utilidades Matemáticas y Geométricas
# ===========================================================================

def clamp(x: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, x))


def distancia(a: Tuple[float, float], b: Tuple[float, float]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def longitud_ruta(
    orden: Sequence[str],
    puntos: Dict[str, Tuple[int, int]],
    inicio: Tuple[int, int] = ALMACEN,
    fin: Tuple[int, int] = ALMACEN,
) -> float:
    if not orden:
        return 0.0
    total = 0.0
    actual = inicio
    for nombre in orden:
        total += distancia(actual, puntos[nombre])
        actual = puntos[nombre]
    total += distancia(actual, fin)
    return total


def dibujar_mapa(
    puntos: Dict[str, Tuple[int, int]],
    tam: int,
    extra: Dict[Tuple[int, int], str] | None = None,
) -> str:
    """Fallback ASCII para terminal sin entorno gráfico."""
    celda = {ALMACEN: "H"}
    if extra:
        celda.update(extra)
    for nombre, p in puntos.items():
        celda[p] = nombre[0]
    filas: List[str] = []
    for y in range(tam, -1, -1):
        filas.append(" ".join(celda.get((x, y), ".") for x in range(tam + 1)))
    return "\n".join(filas)


# ===========================================================================
# Visualización con Matplotlib
# ===========================================================================

def _mpl_available() -> bool:
    try:
        import matplotlib.pyplot as _  # noqa: F401
        return True
    except Exception:
        return False


def plot_puntos_y_ruta(
    puntos: Dict[str, Tuple[int, int]],
    orden: Sequence[str] | None,
    title: str,
    tam: int,
) -> None:
    if not _mpl_available():
        return
    import matplotlib.pyplot as plt

    plt.figure(figsize=(6.8, 6.8))

    for nombre, (x, y) in puntos.items():
        plt.scatter([x], [y], s=140, edgecolors="black", linewidths=0.6, zorder=3)
        plt.text(x + 0.25, y + 0.25, nombre, fontsize=12)

    plt.scatter([ALMACEN[0]], [ALMACEN[1]], s=180, c="red", zorder=4)
    plt.text(ALMACEN[0] + 0.25, ALMACEN[1] + 0.25, "H", fontsize=12, color="red")

    if orden:
        xs = [ALMACEN[0]] + [puntos[n][0] for n in orden] + [ALMACEN[0]]
        ys = [ALMACEN[1]] + [puntos[n][1] for n in orden] + [ALMACEN[1]]
        plt.plot(xs, ys, "-o", linewidth=2.2, alpha=0.85, zorder=2)

    plt.title(title)
    plt.grid(True, linestyle=":", alpha=0.35)
    plt.xlim(-1, tam + 1)
    plt.ylim(-1, tam + 1)
    plt.gca().set_aspect("equal", adjustable="box")
    plt.show()


def plot_grafo(
    puntos: Dict[str, Tuple[int, int]],
    aristas: Dict[frozenset, float],
    camino: Sequence[str] | None,
    title: str,
    tam: int,
) -> None:
    if not _mpl_available():
        return
    import matplotlib.pyplot as plt

    plt.figure(figsize=(7.2, 7.2))

    for clave, _ in aristas.items():
        a, b = tuple(clave)
        xa, ya = puntos[a]
        xb, yb = puntos[b]
        plt.plot([xa, xb], [ya, yb], color="gray", alpha=0.35, linewidth=1.2, zorder=1)

    if camino and len(camino) >= 2:
        for u, v in zip(camino, camino[1:]):
            xu, yu = puntos[u]
            xv, yv = puntos[v]
            plt.plot([xu, xv], [yu, yv], color="deepskyblue", linewidth=3.2, zorder=2)

    for nombre, (x, y) in puntos.items():
        plt.scatter([x], [y], s=140, edgecolors="black", linewidths=0.6, zorder=3)
        plt.text(x + 0.25, y + 0.25, nombre, fontsize=12)

    plt.title(title)
    plt.grid(True, linestyle=":", alpha=0.35)
    plt.xlim(-1, tam + 1)
    plt.ylim(-1, tam + 1)
    plt.gca().set_aspect("equal", adjustable="box")
    plt.show()


# ===========================================================================
# Generación de Escenarios
# ===========================================================================

def _nombre(i: int) -> str:
    if i < 26:
        return chr(ord("A") + i)
    return chr(ord("A") + i % 26) + str(i // 26)


def gen_puntos_unicos(n: int, tam: int, semilla: int | None) -> Dict[str, Tuple[int, int]]:
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


# ===========================================================================
# Algoritmos de Optimización
# ===========================================================================

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
    mejor: List[str] | None = None
    mejor_dist = math.inf
    for perm in itertools.permutations(nombres):
        d = longitud_ruta(perm, puntos)
        if d < mejor_dist:
            mejor_dist = d
            mejor = list(perm)
    return (mejor or []), mejor_dist


def knapsack_optimo(items: Dict[str, Tuple[int, int]], capacidad: int) -> Tuple[int, Set[str]]:
    nombres = list(items)
    dp = [0] * (capacidad + 1)
    take = [[False] * (capacidad + 1) for _ in nombres]
    for idx, nombre in enumerate(nombres):
        valor, peso = items[nombre]
        for c in range(capacidad, peso - 1, -1):
            if dp[c - peso] + valor > dp[c]:
                dp[c] = dp[c - peso] + valor
                take[idx][c] = True
    sel: Set[str] = set()
    c = capacidad
    for idx in range(len(nombres) - 1, -1, -1):
        if take[idx][c]:
            nombre = nombres[idx]
            sel.add(nombre)
            c -= items[nombre][1]
    return dp[capacidad], sel


def dijkstra(grafo: Dict[str, List[Tuple[str, float]]], origen: str, destino: str) -> Tuple[float, List[str]]:
    dist = {n: math.inf for n in grafo}
    prev: Dict[str, str | None] = {n: None for n in grafo}
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
    cur: str | None = destino
    while cur is not None:
        path.append(cur)
        cur = prev[cur]
    path.reverse()
    return dist[destino], path


def _orienteering_optimo(
    puntos: Dict[str, Tuple[int, int]],
    premio: Dict[str, int],
    presupuesto: float,
    stars: int,
) -> Tuple[int, List[str], float]:
    nombres = list(puntos.keys())
    mejor_val = 0
    mejor_ruta: List[str] = []
    mejor_dist = 0.0
    
    for r in range(1, len(nombres) + 1):
        for comb in itertools.combinations(nombres, r):
            val = sum(premio[k] for k in comb)
            if val < mejor_val:
                continue
            opt_ruta, d_min = tsp_optimo({k: puntos[k] for k in comb})
            if d_min <= presupuesto + 1e-9:
                if val > mejor_val or (val == mejor_val and d_min < mejor_dist):
                    mejor_val = val
                    mejor_ruta = opt_ruta
                    mejor_dist = d_min
    return mejor_val, mejor_ruta, mejor_dist


# ===========================================================================
# Sistema de Evaluación
# ===========================================================================

def puntuar_min(jugador: float, baseline: float) -> int:
    if jugador <= 0:
        return 100
    return max(0, min(100, round(baseline / jugador * 100)))


def puntuar_max(jugador: float, optimo: float) -> int:
    if optimo <= 0:
        return 100
    return max(0, min(100, round(jugador / optimo * 100)))


# ===========================================================================
# Interfaz de Entrada CLI
# ===========================================================================

class SalirJuego(Exception):
    pass


def leer(prompt: str) -> str:
    try:
        t = input(prompt)
    except (EOFError, KeyboardInterrupt):
        raise SalirJuego
    if t.strip().lower() in {"salir", "exit", "quit", "q"}:
        raise SalirJuego
    return t


def _tokens(texto: str) -> List[str]:
    return texto.replace(",", " ").split()


def pedir_permutacion(validos: Iterable[str], msg: str) -> List[str]:
    objetivo = set(validos)
    while True:
        e = [t.upper() for t in _tokens(leer(msg))]
        if set(e) != objetivo or len(e) != len(objetivo):
            print("  -> Usa cada punto exactamente una vez.")
            continue
        return e


def pedir_subconjunto(validos: Iterable[str], msg: str) -> List[str]:
    objetivo = set(validos)
    while True:
        e = [t.upper() for t in _tokens(leer(msg))]
        if len(e) != len(set(e)):
            print("  -> No repitas puntos.")
            continue
        if not set(e) <= objetivo:
            print("  -> Solo puedes usar los puntos mostrados.")
            continue
        return e


def _cabecera(titulo: str, subtitulo: str) -> None:
    print("=" * 64)
    print(titulo)
    print(subtitulo)
    print("=" * 64)


# ===========================================================================
# Misión 1: TSP
# ===========================================================================

def preparar_tsp(semilla: int | None, stars: int) -> Dict:
    n, tam = stars_params(stars, base_n=5, base_tam=20)
    n = clamp(n, 4, 12)
    return {"entregas": gen_puntos_unicos(n, tam, semilla), "tam": tam, "stars": stars}


def jugar_tsp(esc: Dict, plot: bool) -> Dict:
    puntos = esc["entregas"]
    tam = esc["tam"]
    stars = esc["stars"]

    _cabecera("MISIÓN 1: RUTA CLÁSICA (TSP)", f"Dificultad: {'★'*stars}  |  Visita todo y regresa")
    print(dibujar_mapa(puntos, tam), "\n")
    for k, v in puntos.items():
        print(f"  {k}: {v}")
    print(f"  H: {ALMACEN}\n")

    if plot:
        plot_puntos_y_ruta(puntos, None, f"M1 TSP - {'★'*stars}", tam)

    orden = pedir_permutacion(puntos, "Orden (ej: " + " ".join(sorted(puntos)) + "): ")

    d_j = longitud_ruta(orden, puntos)
    orden_nn = ruta_vecino_mas_cercano(puntos)
    d_nn = longitud_ruta(orden_nn, puntos)
    orden_exp = ruta_experta(puntos)
    d_exp = longitud_ruta(orden_exp, puntos)
    score = puntuar_min(d_j, d_nn)

    print("\n" + "-" * 64)
    print(f"Tu ruta:    H -> {' -> '.join(orden)} -> H ({d_j:.2f})")
    print(f"Sistema:    H -> {' -> '.join(orden_nn)} -> H ({d_nn:.2f})")
    print(f"Experto:    H -> {' -> '.join(orden_exp)} -> H ({d_exp:.2f})")
    print(f"Puntuación: {score}/100")

    if plot:
        plot_puntos_y_ruta(puntos, orden, f"M1 Tu ruta - {score}/100", tam)

    return {"puntuacion": score}


# ===========================================================================
# Misión 2: CVRP
# ===========================================================================

def preparar_cvrp(semilla: int | None, stars: int) -> Dict:
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


def jugar_cvrp(esc: Dict, plot: bool) -> Dict:
    e, dem, cap, tam, stars = esc["entregas"], esc["demanda"], esc["capacidad"], esc["tam"], esc["stars"]

    _cabecera("MISIÓN 2: CARGA LIMITADA (CVRP)", f"Dificultad: {'★'*stars}  |  Capacidad={cap}")
    print(dibujar_mapa(e, tam), "\n")
    for k, p in e.items():
        print(f"  {k}: {p}  demanda={dem[k]}")
    print(f"  H: {ALMACEN}\n")

    if plot:
        plot_puntos_y_ruta(e, None, f"M2 CVRP - {'★'*stars}", tam)

    print("Escribe UN viaje por línea. Línea vacía para terminar.")
    viajes: List[List[str]] = []
    restantes = set(e)
    while restantes:
        crudo = leer(f"Viaje {len(viajes)+1} (restan {sorted(restantes)}): ")
        v = [t.upper() for t in _tokens(crudo)]
        if not v:
            if viajes:
                break
            print("  -> El primer viaje no puede estar vacío.")
            continue
        if not set(v) <= restantes or len(v) != len(set(v)):
            print("  -> Usa solo puntos restantes, sin repetir.")
            continue
        carga = sum(dem[x] for x in v)
        if carga > cap:
            print(f"  -> Carga {carga} supera capacidad {cap}.")
            continue
        viajes.append(v)
        restantes -= set(v)

    visitados = [n for vv in viajes for n in vv]
    errores = []
    if sorted(visitados) != sorted(e):
        errores.append("Debes entregar cada punto exactamente una vez.")
    for i, vv in enumerate(viajes, 1):
        if sum(dem[x] for x in vv) > cap:
            errores.append(f"Viaje {i} excede capacidad.")

    dist_j = sum(longitud_ruta(vv, e) for vv in viajes)
    base = _heuristica_cvrp(e, dem, cap)
    dist_b = sum(longitud_ruta(vv, e) for vv in base)
    score = 0 if errores else puntuar_min(dist_j, dist_b)

    print("\n" + "-" * 64)
    print(f"Tu distancia total: {dist_j:.2f}")
    print(f"Sistema (heurística): {dist_b:.2f}")
    if errores:
        print("Errores: " + " ".join(errores))
    print(f"Puntuación: {score}/100")

    return {"puntuacion": score}


# ===========================================================================
# Misión 3: VRPTW
# ===========================================================================

def preparar_vrptw(semilla: int | None, stars: int) -> Dict:
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
        if t < ini:
            t = float(ini)
        if t > fin:
            tard += t - fin
        lleg[k] = t
        actual = e[k]
    dist += distancia(actual, ALMACEN)
    return dist, tard, lleg


def jugar_vrptw(esc: Dict, plot: bool) -> Dict:
    e, v, vel, pen, tam, stars = esc["entregas"], esc["ventanas"], esc["velocidad"], esc["pen"], esc["tam"], esc["stars"]
    _cabecera("MISIÓN 3: VENTANAS DE TIEMPO (VRPTW)", f"Dificultad: {'★'*stars}  |  vel={vel}  pen={pen}")

    print(dibujar_mapa(e, tam), "\n")
    for k, p in e.items():
        ini, fin = v[k]
        print(f"  {k}: {p}  ventana=[{ini},{fin}]")
    print(f"  H: {ALMACEN}\n")

    if plot:
        plot_puntos_y_ruta(e, None, f"M3 VRPTW - {'★'*stars}", tam)

    orden = pedir_permutacion(e, "Orden de visita: ")

    dist, tard, lleg = _sim_vrptw(orden, e, v, vel)
    costo = dist + pen * tard

    edd = sorted(e, key=lambda k: v[k][1])
    dist_b, tard_b, _ = _sim_vrptw(edd, e, v, vel)
    costo_b = dist_b + pen * tard_b

    score = puntuar_min(costo, costo_b)

    print("\n" + "-" * 64)
    for k in orden:
        ini, fin = v[k]
        marca = "OK" if lleg[k] <= fin else "TARDE"
        print(f"  {k}: llegada {lleg[k]:.1f}  ventana=[{ini},{fin}]  {marca}")
    print(f"Costo tuyo: {costo:.2f}  (dist={dist:.2f}, tard={tard:.2f})")
    print(f"Costo sistema(EDD): {costo_b:.2f}  (tard={tard_b:.2f})")
    print(f"Puntuación: {score}/100")

    if plot:
        plot_puntos_y_ruta(e, orden, f"M3 Tu ruta - {score}/100", tam)

    return {"puntuacion": score}


# ===========================================================================
# Misión 4: Knapsack
# ===========================================================================

def preparar_mochila(semilla: int | None, stars: int) -> Dict:
    rng = random.Random(semilla)
    n = clamp(int(round({1: 5, 2: 6, 3: 7, 4: 9, 5: 11}[stars])), 5, 14)
    items: Dict[str, Tuple[int, int]] = {}
    v_lo, v_hi = {1: (5, 18), 2: (5, 22), 3: (5, 25), 4: (8, 35), 5: (10, 45)}[stars]
    p_lo, p_hi = {1: (2, 8), 2: (2, 10), 3: (3, 12), 4: (3, 15), 5: (4, 18)}[stars]
    
    for i in range(n):
        val = rng.randint(v_lo, v_hi)
        peso = rng.randint(p_lo, p_hi)
        items[_nombre(i)] = (val, peso)
        
    total_peso = sum(p for _, p in items.values())
    capacidad = max(max(p for _, p in items.values()) + 1, int(total_peso * 0.45))
    return {"items": items, "capacidad": capacidad, "stars": stars}


def jugar_mochila(esc: Dict, plot: bool) -> Dict:
    items, cap, stars = esc["items"], esc["capacidad"], esc["stars"]
    _cabecera("MISIÓN 4: LA MOCHILA (KNAPSACK 0/1)", f"Dificultad: {'★'*stars}  |  Capacidad={cap} kg")

    print(f"{'Objeto':<8} {'Valor':<8} {'Peso (kg)':<10}")
    print("-" * 28)
    for k, (v, p) in items.items():
        print(f"{k:<8} {v:<8} {p:<10}")

    sel = pedir_subconjunto(items.keys(), "\nSelecciona objetos (ej: A C E): ")
    peso_total = sum(items[k][1] for k in sel)
    valor_total = sum(items[k][0] for k in sel)

    v_opt, sel_opt = knapsack_optimo(items, cap)

    if peso_total > cap:
        print(f"\n¡SOBREPESO! Carga total ({peso_total} kg) excede la capacidad ({cap} kg).")
        score = 0
    else:
        score = puntuar_max(valor_total, v_opt)

    print("\n" + "-" * 64)
    print(f"Tu elección:     {sorted(sel)} | Valor={valor_total} | Peso={peso_total}/{cap} kg")
    print(f"Óptimo sistema: {sorted(sel_opt)} | Valor={v_opt}")
    print(f"Puntuación:     {score}/100")

    return {"puntuacion": score}


# ===========================================================================
# Misión 5: Dijkstra
# ===========================================================================

def preparar_dijkstra(semilla: int | None, stars: int) -> Dict:
    rng = random.Random(semilla)
    n, tam = stars_params(stars, base_n=6, base_tam=20)
    n = clamp(n, 5, 12)
    puntos = gen_puntos_unicos(n, tam, semilla)
    nombres = list(puntos.keys())
    
    aristas: Dict[frozenset, float] = {}
    grafo: Dict[str, List[Tuple[str, float]]] = {k: [] for k in nombres}

    for i in range(len(nombres) - 1):
        u, v = nombres[i], nombres[i + 1]
        w = round(distancia(puntos[u], puntos[v]), 2)
        aristas[frozenset([u, v])] = w
        grafo[u].append((v, w))
        grafo[v].append((u, w))

    prob = {1: 0.3, 2: 0.4, 3: 0.5, 4: 0.6, 5: 0.7}[stars]
    for u, v in itertools.combinations(nombres, 2):
        if frozenset([u, v]) not in aristas and rng.random() < prob:
            w = round(distancia(puntos[u], puntos[v]), 2)
            aristas[frozenset([u, v])] = w
            grafo[u].append((v, w))
            grafo[v].append((u, w))

    origen, destino = nombres[0], nombres[-1]
    return {"puntos": puntos, "aristas": aristas, "grafo": grafo, "origen": origen, "destino": destino, "tam": tam, "stars": stars}


def jugar_dijkstra(esc: Dict, plot: bool) -> Dict:
    puntos, aristas, grafo, origen, destino, tam, stars = (
        esc["puntos"], esc["aristas"], esc["grafo"], esc["origen"], esc["destino"], esc["tam"], esc["stars"]
    )
    _cabecera("MISIÓN 5: CAMINO MÁS CORTO (DIJKSTRA)", f"Dificultad: {'★'*stars}  |  Conectar {origen} -> {destino}")

    print("Conexiones disponibles:")
    for clave, peso in aristas.items():
        u, v = tuple(clave)
        print(f"  {u} <-> {v} : {peso}")

    if plot:
        plot_grafo(puntos, aristas, None, f"M5 Grafo - {'★'*stars}", tam)

    while True:
        crudo = leer(f"\nIngresa el camino desde {origen} hasta {destino} (ej: {origen} ... {destino}): ")
        camino = [t.upper() for t in _tokens(crudo)]
        if not camino or camino[0] != origen or camino[-1] != destino:
            print(f"  -> El camino debe empezar en {origen} y terminar en {destino}.")
            continue
        break

    valido = True
    dist_total = 0.0
    for u, v in zip(camino, camino[1:]):
        vecinos = dict(grafo.get(u, []))
        if v not in vecinos:
            valido = False
            break
        dist_total += vecinos[v]

    opt_dist, opt_path = dijkstra(grafo, origen, destino)

    if not valido:
        print("\n¡CAMINO INVÁLIDO! Existe un salto entre nodos no conectados directamente.")
        score = 0
    else:
        score = puntuar_min(dist_total, opt_dist)

    print("\n" + "-" * 64)
    print(f"Tu camino:     {' -> '.join(camino)} | Distancia={dist_total:.2f}")
    print(f"Camino óptimo: {' -> '.join(opt_path)} | Distancia={opt_dist:.2f}")
    print(f"Puntuación:    {score}/100")

    if plot and valido:
        plot_grafo(puntos, aristas, camino, f"M5 Tu Camino - {score}/100", tam)

    return {"puntuacion": score}


# ===========================================================================
# Misión 6: Flota en Equipo
# ===========================================================================

def preparar_flota(semilla: int | None, stars: int) -> Dict:
    n, tam = stars_params(stars, base_n=8, base_tam=20)
    n = clamp(n, 6, 15)
    k = {1: 2, 2: 2, 3: 3, 4: 3, 5: 4}[stars]
    entregas = gen_puntos_unicos(n, tam, semilla)
    return {"entregas": entregas, "k": k, "tam": tam, "stars": stars}


def _largos_grupos(grupos: List[List[str]], puntos: Dict[str, Tuple[int, int]]) -> List[float]:
    return [longitud_ruta(g, puntos) if g else 0.0 for g in grupos]


def _heuristica_flota(puntos: Dict[str, Tuple[int, int]], k: int) -> List[List[str]]:
    pendientes = set(puntos)
    grupos: List[List[str]] = [[] for _ in range(k)]
    idx = 0
    while pendientes:
        actual = ALMACEN if not grupos[idx] else puntos[grupos[idx][-1]]
        sig = min(pendientes, key=lambda n: distancia(actual, puntos[n]))
        grupos[idx].append(sig)
        pendientes.remove(sig)
        idx = (idx + 1) % k
    return grupos


def jugar_flota(esc: Dict, plot: bool) -> Dict:
    e, k, tam, stars = esc["entregas"], esc["k"], esc["tam"], esc["stars"]
    _cabecera("MISIÓN 6: FLOTA EN EQUIPO", f"Dificultad: {'★'*stars}  |  Vehículos={k}")

    print(dibujar_mapa(e, tam), "\n")
    for nombre, p in e.items():
        print(f"  {nombre}: {p}")

    if plot:
        plot_puntos_y_ruta(e, None, f"M6 Flota - {'★'*stars}", tam)

    print(f"\nAsigna los puntos entre los {k} vehículos (una línea por vehículo).")
    grupos: List[List[str]] = []
    restantes = set(e)

    for i in range(k):
        crudo = leer(f"Vehículo {i+1} (restan {sorted(restantes)}): ")
        v = [t.upper() for t in _tokens(crudo)]
        if not set(v) <= restantes or len(v) != len(set(v)):
            print("  -> Transgresión de reglas: puntos no válidos o repetidos.")
            return {"puntuacion": 0}
        grupos.append(v)
        restantes -= set(v)

    if restantes:
        print(f"\nError: Quedaron puntos sin asignar: {restantes}")
        return {"puntuacion": 0}

    largos = _largos_grupos(grupos, e)
    makespan = max(largos)

    h_grupos = _heuristica_flota(e, k)
    h_makespan = max(_largos_grupos(h_grupos, e))

    score = puntuar_min(makespan, h_makespan)

    print("\n" + "-" * 64)
    for idx, (g, l) in enumerate(zip(grupos, largos), 1):
        print(f"Vehículo {idx}: H -> {' -> '.join(g)} -> H | Ruta={l:.2f}")
    print(f"Ruta más larga (Makespan): {makespan:.2f}")
    print(f"Referencia Heurística:    {h_makespan:.2f}")
    print(f"Puntuación:               {score}/100")

    return {"puntuacion": score}


# ===========================================================================
# Misión 7: Orienteering Problem
# ===========================================================================

def preparar_orienteering(semilla: int | None, stars: int) -> Dict:
    rng = random.Random(semilla)
    n, tam = stars_params(stars, base_n=7, base_tam=20)
    n = clamp(n, 5, 10)
    entregas = gen_puntos_unicos(n, tam, semilla)
    premio = {k: rng.randint(10, 100) for k in entregas}
    d_total = sum(distancia(ALMACEN, p) for p in entregas.values())
    ratio = {1: 0.6, 2: 0.5, 3: 0.45, 4: 0.4, 5: 0.35}[stars]
    presupuesto = round(d_total * ratio, 1)
    return {"entregas": entregas, "premio": premio, "presupuesto": presupuesto, "tam": tam, "stars": stars}


def jugar_orienteering(esc: Dict, plot: bool) -> Dict:
    e, premio, pres, tam, stars = esc["entregas"], esc["premio"], esc["presupuesto"], esc["tam"], esc["stars"]
    _cabecera("MISIÓN 7: RUTA CON PRESUPUESTO (ORIENTEERING)", f"Dificultad: {'★'*stars}  |  Presupuesto Max={pres} km")

    print(dibujar_mapa(e, tam), "\n")
    for k, p in e.items():
        print(f"  {k}: {p}  Premio={premio[k]}")

    if plot:
        plot_puntos_y_ruta(e, None, f"M7 Orienteering - {'★'*stars}", tam)

    orden = pedir_subconjunto(e.keys(), "\nElige y ordena los puntos a visitar (ej: A D F): ")

    dist_total = longitud_ruta(orden, e)
    valor_total = sum(premio[k] for k in orden)

    opt_val, opt_ruta, opt_dist = _orienteering_optimo(e, premio, pres, stars)

    if dist_total > pres + 1e-9:
        print(f"\n¡PRESUPUESTO EXCEDIDO! Distancia recorida ({dist_total:.2f} km) supera el límite ({pres} km).")
        score = 0
    else:
        score = puntuar_max(valor_total, opt_val)

    print("\n" + "-" * 64)
    print(f"Tu ruta:     H -> {' -> '.join(orden)} -> H | Premio={valor_total} | Distancia={dist_total:.2f}/{pres} km")
    print(f"Ruta óptima: H -> {' -> '.join(opt_ruta)} -> H | Premio={opt_val} | Distancia={opt_dist:.2f} km")
    print(f"Puntuación:  {score}/100")

    if plot and dist_total <= pres:
        plot_puntos_y_ruta(e, orden, f"M7 Tu Ruta - {score}/100", tam)

    return {"puntuacion": score}


# ===========================================================================
# Pruebas Unitarias Automatizadas
# ===========================================================================

def ejecutar_tests() -> None:
    print("Iniciando Verificación de Pruebas Unitarias...")
    
    # Test 1: Distancia Euclidiana
    assert math.isclose(distancia((0, 0), (3, 4)), 5.0), "Error en cálculo de distancia"
    
    # Test 2: Knapsack Óptimo
    items = {"A": (60, 10), "B": (100, 20), "C": (120, 30)}
    val, sel = knapsack_optimo(items, 50)
    assert val == 220 and sel == {"B", "C"}, "Error en algoritmo de Mochila"
    
    # Test 3: Dijkstra
    g = {
        "A": [("B", 1.0), ("C", 4.0)],
        "B": [("A", 1.0), ("C", 2.0), ("D", 5.0)],
        "C": [("A", 4.0), ("B", 2.0), ("D", 1.0)],
        "D": [("B", 5.0), ("C", 1.0)]
    }
    d_cost, path = dijkstra(g, "A", "D")
    assert math.isclose(d_cost, 4.0) and path == ["A", "B", "C", "D"], "Error en algoritmo Dijkstra"
    
    # Test 4: TSP Óptimo
    pts = {"A": (0, 1), "B": (1, 1), "C": (1, 0)}
    r_opt, d_opt = tsp_optimo(pts)
    assert len(r_opt) == 3, "Error en dimensión de solución TSP"
    
    print("¡Todas las pruebas unitarias pasaron exitosamente!")


# ===========================================================================
# Ejecución Principal y Bucle CLI
# ===========================================================================

def main() -> None:
    parser = argparse.ArgumentParser(description="Reparto Express 2.2 - Simulador de Optimización Logística")
    parser.add_argument("--mision", type=int, choices=range(1, 8), help="Número de misión a ejecutar (1 a 7)")
    parser.add_argument("--stars", type=int, default=3, choices=range(1, 6), help="Nivel de dificultad (1 a 5 estrellas)")
    parser.add_argument("--seed", type=int, default=42, help="Semilla del generador aleatorio")
    parser.add_argument("--plot", action="store_true", help="Activa la visualización de gráficos Matplotlib")
    parser.add_argument("--demo", action="store_true", help="Ejecuta demostración automática sin intervención de teclado")
    parser.add_argument("--test", action="store_true", help="Ejecuta suite de pruebas unitarias")

    args = parser.parse_args()

    if args.test:
        ejecutar_tests()
        sys.exit(0)

    misiones_preparar = {
        1: preparar_tsp, 2: preparar_cvrp, 3: preparar_vrptw,
        4: preparar_mochila, 5: preparar_dijkstra, 6: preparar_flota, 7: preparar_orienteering
    }

    misiones_jugar = {
        1: jugar_tsp, 2: jugar_cvrp, 3: jugar_vrptw,
        4: jugar_mochila, 5: jugar_dijkstra, 6: jugar_flota, 7: jugar_orienteering
    }

    try:
        if args.mision:
            esc = misiones_preparar[args.mision](args.seed, args.stars)
            misiones_jugar[args.mision](esc, args.plot)
        elif args.demo:
            print("=== MODO DEMOSTRACIÓN AUTOMÁTICA ===")
            for m in range(1, 8):
                esc = misiones_preparar[m](args.seed, args.stars)
                print(f"\n[Misión {m} Cargada Correctamente]")
            print("\nDemostración completada sin errores.")
        else:
            print("Selecciona una misión especificando el parámetro --mision N (1..7)")
            print("Ejemplo: python3 reparto_express.py --mision 1 --stars 3 --plot")

    except SalirJuego:
        print("\nEjecución finalizada por el usuario.")


if __name__ == "__main__":
    main()
