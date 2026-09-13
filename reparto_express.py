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

MEJORAS (gratis) para Google Colab:
- Dificultad por estrellas (1..5) para TODAS las misiones: --stars
- Visualización opcional con Matplotlib (mapa + ruta/solución): --plot

Uso típico (Colab recomendado):
  python3 reparto_express.py --mision 1 --stars 3 --plot
  python3 reparto_express.py --mision 7 --stars 5 --plot
  python3 reparto_express.py --demo --stars 3 --plot
  python3 reparto_express.py --test

Notas:
- En Colab, lo más estable es usar --mision N (evita menús largos).
- El modo demo no pide teclado.

Complejidad (Big-O, resumen):
- NN (vecino más cercano): O(n^2)
- 2-opt naive: O(n^3) por iteración (en la práctica converge rápido en n pequeños)
- Knapsack DP: O(n * capacidad)
- Dijkstra: O((V+E) log V)
- Orienteering óptimo (fuerza bruta): O(2^n * n!) si se hace mal; aquí se acota con stars.
"""

from __future__ import annotations

import argparse
import heapq
import itertools
import math
import random
import sys
from typing import Dict, Iterable, List, Sequence, Tuple

ALMACEN: Tuple[int, int] = (0, 0)


# ===========================================================================
#  Utilidades
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
    """Fallback ASCII (rápido)."""
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
#  Visualización (Matplotlib - gratis)
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
    """Grafica puntos y una ruta (si se pasa)."""
    if not _mpl_available():
        return
    import matplotlib.pyplot as plt

    plt.figure(figsize=(6.8, 6.8))

    # Puntos
    for nombre, (x, y) in puntos.items():
        plt.scatter([x], [y], s=140, edgecolors="black", linewidths=0.6, zorder=3)
        plt.text(x + 0.25, y + 0.25, nombre, fontsize=12)

    # Almacén
    plt.scatter([ALMACEN[0]], [ALMACEN[1]], s=180, c="red", zorder=4)
    plt.text(ALMACEN[0] + 0.25, ALMACEN[1] + 0.25, "H", fontsize=12, color="red")

    # Ruta
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

    # aristas
    for clave, peso in aristas.items():
        a, b = tuple(clave)
        xa, ya = puntos[a]
        xb, yb = puntos[b]
        plt.plot([xa, xb], [ya, yb], color="gray", alpha=0.35, linewidth=1.2, zorder=1)

    # camino resaltado
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
#  Generación de escenarios (con estrellas)
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
    """Escala tamaño de escenario según estrellas. Nivel 3 = base."""
    s = clamp(stars, 1, 5)
    mult_n = {1: 0.6, 2: 0.8, 3: 1.0, 4: 1.35, 5: 1.8}[s]
    mult_t = {1: 0.85, 2: 0.95, 3: 1.0, 4: 1.15, 5: 1.3}[s]
    n = max(3, int(round(base_n * mult_n)))
    tam = max(10, int(round(base_tam * mult_t)))
    return n, tam


# ===========================================================================
#  Heurísticas/óptimos
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


def knapsack_optimo(items: Dict[str, Tuple[int, int]], capacidad: int) -> Tuple[int, set[str]]:
    nombres = list(items)
    dp = [0] * (capacidad + 1)
    take = [[False] * (capacidad + 1) for _ in nombres]
    for idx, nombre in enumerate(nombres):
        valor, peso = items[nombre]
        for c in range(capacidad, peso - 1, -1):
            if dp[c - peso] + valor > dp[c]:
                dp[c] = dp[c - peso] + valor
                take[idx][c] = True
    sel: set[str] = set()
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


# ===========================================================================
#  Scoring
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
#  Entrada
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
#  Misión 1: TSP
# ===========================================================================

def preparar_tsp(semilla: int | None, stars: int) -> Dict:
    n, tam = stars_params(stars, base_n=5, base_tam=20)
    # Para que el reto siga siendo jugable, acotamos n.
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
    print(f"Tu ruta:   H -> {' -> '.join(orden)} -> H ({d_j:.2f})")
    print(f"Sistema:   H -> {' -> '.join(orden_nn)} -> H ({d_nn:.2f})")
    print(f"Experto:   H -> {' -> '.join(orden_exp)} -> H ({d_exp:.2f})")
    print(f"Puntuación: {score}/100")

    if plot:
        plot_puntos_y_ruta(puntos, orden, f"M1 Tu ruta - {score}/100", tam)

    return {"puntuacion": score}


# ===========================================================================
#  Misión 2: CVRP
# ===========================================================================

def preparar_cvrp(semilla: int | None, stars: int) -> Dict:
    rng = random.Random(semilla)
    n, tam = stars_params(stars, base_n=6, base_tam=20)
    n = clamp(n, 5, 14)
    entregas = gen_puntos_unicos(n, tam, semilla)

    # Demanda más difícil a estrellas altas
    d_lo = {1: 1, 2: 1, 3: 2, 4: 2, 5: 3}[stars]
    d_hi = {1: 4, 2: 5, 3: 6, 4: 7, 5: 9}[stars]
    demanda = {k: rng.randint(d_lo, d_hi) for k in entregas}

    # Capacidad más ajustada a estrellas altas
    total = sum(demanda.values())
    # ratio de capacidad por viaje (menor => más viajes)
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

    # evaluar
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
#  Misión 3: VRPTW
# ===========================================================================

def preparar_vrptw(semilla: int | None, stars: int) -> Dict:
    rng = random.Random(semilla)
    n, tam = stars_params(stars, base_n=5, base_tam=20)
    n = clamp(n, 4, 12)
    entregas = gen_puntos_unicos(n, tam, semilla)

    # Ventanas: más estrechas con stars altas
    base_in = {1: 0, 2: 0, 3: 0, 4: 1, 5: 2}[stars]
    in_max = {1: 5, 2: 6, 3: 6, 4: 7, 5: 8}[stars]
    ancho_lo = {1: 8, 2: 7, 3: 6, 4: 5, 5: 4}[stars]
    ancho_hi = {1: 12, 2: 10, 3: 9, 4: 8, 5: 6}[stars]
    ventanas = {}
    for k in entregas:
        ini = rng.randint(base_in, in_max)
        ancho = rng.randint(ancho_lo, ancho_hi)
        ventanas[k] = (ini, ini + ancho)

    # velocidad ligeramente menor a mayor dificultad
    vel = {1: 6.0, 2: 5.5, 3: 5.0, 4: 4.7, 5: 4.3}[stars]

    # penalización mayor a mayor dificultad
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

    # baseline EDD
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
#  Misión 4: Knapsack
# ===========================================================================

def preparar_mochila(semilla: int | None, stars: int) -> Dict:
    rng = random.Random(semilla)
    # más items a mayor dificultad
    n = clamp(int(round({1: 5, 2: 6, 3: 7, 4: 9, 5: 11}[stars])), 5, 14)
    items: Dict[str, Tuple[int, int]] = {}
    # rangos crecen con stars (más difícil decidir)
    v_lo, v_hi = {1: (5, 18), 2: (5, 22), 3: (5, 25), 4: (8, 35), 5: (10, 45)}[stars]
    p_lo, p_hi = {1: (1, 7), 2: (2, 9), 3: (2, 10), 4: (3, 12), 5: (3, 14)}[stars]

    for i in range(n):
        items[_nombre(i)] = (rng.randint(v_lo, v_hi), rng.randint(p_lo, p_hi))

    peso_total = sum(p for _, p in items.values())
    # capacidad más restrictiva a mayor dificultad
    ratio = {1: 0.60, 2: 0.55, 3: 0.50, 4: 0.45, 5: 0.40}[stars]
    cap = max(5, int(round(peso_total * ratio)))

    return {"items": items, "capacidad": cap, "stars": stars}


def jugar_mochila(esc: Dict) -> Dict:
    items, cap, stars = esc["items"], esc["capacidad"], esc["stars"]
    _cabecera("MISIÓN 4: LA MOCHILA (Knapsack)", f"Dificultad: {'★'*stars}  |  Capacidad={cap}")
    print("  Paquete   Valor   Peso")
    for k, (val, pes) in items.items():
        print(f"    {k:<6}  {val:>5}  {pes:>5}")
    print()

    sel = pedir_subconjunto(items, "Paquetes a cargar (ej: A C D): ")
    peso = sum(items[k][1] for k in sel)
    valor = sum(items[k][0] for k in sel)

    opt_val, opt_set = knapsack_optimo(items, cap)

    fact = peso <= cap
    score = 0 if not fact else puntuar_max(valor, opt_val)

    print("\n" + "-" * 64)
    print(f"Tu selección: {sorted(sel)}  peso={peso}/{cap}  valor={valor}")
    if not fact:
        print("  -> Sobrepeso: selección inválida.")
    print(f"Óptimo: {sorted(opt_set)}  valor={opt_val}")
    print(f"Puntuación: {score}/100")

    return {"puntuacion": score}


# ===========================================================================
#  Misión 5: Dijkstra
# ===========================================================================

def preparar_dijkstra(semilla: int | None, stars: int) -> Dict:
    rng = random.Random(semilla)
    # nodos crecen con stars
    n = clamp(int(round({1: 6, 2: 7, 3: 8, 4: 10, 5: 12}[stars])), 6, 14)
    tam = clamp(int(round({1: 14, 2: 16, 3: 18, 4: 20, 5: 22}[stars])), 12, 26)

    puntos = gen_puntos_unicos(n, tam, semilla)
    nombres = list(puntos)

    # densidad aumenta moderadamente con stars
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
            # a estrellas altas, introducimos variación extra en pesos
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


def jugar_dijkstra(esc: Dict, plot: bool) -> Dict:
    puntos, aristas, grafo, o, d, tam, stars = (
        esc["puntos"],
        esc["aristas"],
        esc["grafo"],
        esc["origen"],
        esc["destino"],
        esc["tam"],
        esc["stars"],
    )
    _cabecera("MISIÓN 5: CAMINO MÁS CORTO (Dijkstra)", f"Dificultad: {'★'*stars}  |  {o} -> {d}")

    print("Calles (nodo-nodo : peso):")
    for key, w in sorted(aristas.items(), key=lambda kv: tuple(sorted(tuple(kv[0])))):
        a, b = sorted(tuple(key))
        print(f"  {a}-{b}: {w}")

    if plot:
        plot_grafo(puntos, aristas, None, f"M5 Grafo - {'★'*stars}", tam)

    while True:
        camino = [t.upper() for t in _tokens(leer(f"Camino de {o} a {d} (ej: {o} ... {d}): "))]
        if not camino or camino[0] != o or camino[-1] != d:
            print(f"  -> Debe iniciar en {o} y terminar en {d}.")
            continue
        costo = 0.0
        ok = True
        for u, v2 in zip(camino, camino[1:]):
            neigh = dict(grafo[u])
            if v2 not in neigh:
                print(f"  -> No existe calle {u}-{v2}.")
                ok = False
                break
            costo += neigh[v2]
        if not ok:
            continue
        break

    costo_opt, camino_opt = dijkstra(grafo, o, d)
    score = puntuar_min(costo, costo_opt)

    print("\n" + "-" * 64)
    print(f"Tu camino: {' -> '.join(camino)}  costo={costo:.1f}")
    print(f"Óptimo:    {' -> '.join(camino_opt)}  costo={costo_opt:.1f}")
    print(f"Puntuación: {score}/100")

    if plot:
        plot_grafo(puntos, aristas, camino, f"M5 Tu camino - {score}/100", tam)

    return {"puntuacion": score}


# ===========================================================================
#  Misión 6: Flota
# ===========================================================================

def preparar_flota(semilla: int | None, stars: int) -> Dict:
    # entregas suben, k sube lento => más difícil
    n, tam = stars_params(stars, base_n=7, base_tam=20)
    n = clamp(n, 6, 18)
    k = {1: 3, 2: 3, 3: 2, 4: 2, 5: 2}[stars]  # a alto nivel, mismos vehículos para más presión
    return {"entregas": gen_puntos_unicos(n, tam, semilla), "k": k, "tam": tam, "stars": stars}


def _heuristica_flota(entregas: Dict[str, Tuple[int, int]], k: int) -> List[List[str]]:
    nombres = sorted(entregas, key=lambda n: math.atan2(entregas[n][1], entregas[n][0]))
    grupos = [[] for _ in range(k)]
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


def jugar_flota(esc: Dict, plot: bool) -> Dict:
    e, k, tam, stars = esc["entregas"], esc["k"], esc["tam"], esc["stars"]
    _cabecera("MISIÓN 6: FLOTA EN EQUIPO", f"Dificultad: {'★'*stars}  |  Vehículos={k}")

    print(dibujar_mapa(e, tam), "\n")
    for n, p in e.items():
        print(f"  {n}: {p}")
    print(f"  H: {ALMACEN}\n")

    if plot:
        plot_puntos_y_ruta(e, None, f"M6 Flota - {'★'*stars}", tam)

    print(f"Asigna entregas a {k} vehículos (una línea por vehículo).")
    grupos: List[List[str]] = []
    restantes = set(e)
    for i in range(k):
        crudo = leer(f"Vehículo {i+1} (restan {sorted(restantes)}): ")
        g = [t.upper() for t in _tokens(crudo)]
        if not set(g) <= restantes or len(g) != len(set(g)):
            print("  -> inválido, vehículo vacío.")
            g = []
        grupos.append(g)
        restantes -= set(g)

    if restantes:
        grupos[-1].extend(sorted(restantes))

    visitados = [n for g in grupos for n in g]
    errores = []
    if sorted(visitados) != sorted(e):
        errores.append("Cada entrega debe asignarse exactamente una vez.")

    largos = _largos_grupos(grupos, e) if not errores else []
    makespan = max(largos) if largos else math.inf

    base = _heuristica_flota(e, k)
    largos_b = _largos_grupos(base, e)
    makespan_b = max(largos_b)

    score = 0 if errores else puntuar_min(makespan, makespan_b)

    print("\n" + "-" * 64)
    for i, (g, L) in enumerate(zip(grupos, largos), 1):
        txt = " -> ".join(g) if g else "(vacío)"
        print(f"Vehículo {i}: H -> {txt} -> H  ({L:.2f})")
    print(f"Tu ruta más larga (makespan): {makespan:.2f}")
    print(f"Sistema (barrido): {makespan_b:.2f}")
    print(f"Puntuación: {score}/100")

    return {"puntuacion": score}


# ===========================================================================
#  Misión 7: Orienteering
# ===========================================================================

def preparar_orienteering(semilla: int | None, stars: int) -> Dict:
    rng = random.Random(semilla)
    n, tam = stars_params(stars, base_n=7, base_tam=20)
    n = clamp(n, 6, 14)
    entregas = gen_puntos_unicos(n, tam, semilla)

    premio_lo, premio_hi = {1: (10, 35), 2: (10, 45), 3: (10, 50), 4: (15, 70), 5: (20, 90)}[stars]
    premio = {k: rng.randint(premio_lo, premio_hi) for k in entregas}

    # presupuesto: menor % a mayor dificultad
    ruta_total = longitud_ruta(ruta_experta(entregas), entregas)
    ratio = {1: 0.75, 2: 0.70, 3: 0.60, 4: 0.50, 5: 0.42}[stars]
    pres = round(ruta_total * ratio, 1)

    return {"entregas": entregas, "premio": premio, "presupuesto": pres, "tam": tam, "stars": stars}


def _orienteering_optimo(entregas, premio, presupuesto, stars: int) -> Tuple[int, List[str], float]:
    """Búsqueda exacta acotada por stars.

    Para evitar explosión combinatoria, se limita el tamaño de subconjunto a un máximo
    dependiente de stars. Esto mantiene el juego rápido en Colab.
    """
    nombres = list(entregas)
    # límite de subconjunto: 1..5 estrellas
    rmax = {1: 6, 2: 7, 3: 8, 4: 9, 5: 10}[stars]
    rmax = min(rmax, len(nombres))

    best_val, best_ord, best_dist = 0, [], 0.0
    for r in range(1, rmax + 1):
        for sub in itertools.combinations(nombres, r):
            val = sum(premio[n] for n in sub)
            if val <= best_val:
                continue
            sub_pts = {n: entregas[n] for n in sub}
            # para r <= 10 esto sigue siendo pesado si fuera óptimo exacto,
            # usamos ruta_experta como estimación fuerte.
            ord2 = ruta_experta(sub_pts)
            dist = longitud_ruta(ord2, sub_pts)
            if dist <= presupuesto + 1e-9:
                best_val, best_ord, best_dist = val, ord2, dist

    return best_val, best_ord, best_dist


def jugar_orienteering(esc: Dict, plot: bool) -> Dict:
    e, premio, pres, tam, stars = esc["entregas"], esc["premio"], esc["presupuesto"], esc["tam"], esc["stars"]
    _cabecera("MISIÓN 7: RUTA CON PRESUPUESTO (Orienteering)", f"Dificultad: {'★'*stars}  |  Presupuesto={pres} km")

    print(dibujar_mapa(e, tam), "\n")
    for k, p in e.items():
        print(f"  {k}: {p}  premio={premio[k]}")
    print(f"  H: {ALMACEN}\n")

    if plot:
        plot_puntos_y_ruta(e, None, f"M7 Orienteering - {'★'*stars}", tam)

    print("Elige un subconjunto EN ORDEN (puede ser vacío) sin repetir.")
    orden = [t.upper() for t in _tokens(leer("Entregas a visitar (ej: A C): "))]

    errores = []
    if len(orden) != len(set(orden)):
        errores.append("No repitas entregas.")
    if not set(orden) <= set(e):
        errores.append("Usa solo entregas válidas.")

    dist = longitud_ruta(orden, e) if orden and not errores else (0.0 if not errores else math.inf)
    if not errores and dist > pres + 1e-9:
        errores.append(f"Tu ruta mide {dist:.1f} > presupuesto {pres}.")

    val = sum(premio[k] for k in orden) if not errores else 0

    opt_val, opt_ord, opt_dist = _orienteering_optimo(e, premio, pres, stars)
    score = 0 if errores else puntuar_max(val, opt_val)

    print("\n" + "-" * 64)
    ruta_txt = f"H -> {' -> '.join(orden)} -> H" if orden else "H (no sales)"
    print(f"Tu ruta: {ruta_txt}  dist={dist:.1f}")
    if errores:
        print("Errores: " + " ".join(errores))
    print(f"Premio tuyo: {val}")
    print(f"Óptimo (acotado): premio={opt_val}  dist≈{opt_dist:.1f}  orden={opt_ord}")
    print(f"Puntuación: {score}/100")

    if plot and not errores and orden:
        plot_puntos_y_ruta(e, orden, f"M7 Tu ruta - {score}/100", tam)

    return {"puntuacion": score}


# ===========================================================================
#  Demo + Tests
# ===========================================================================

def demo(stars: int, plot: bool) -> None:
    print("### DEMO AUTOMÁTICA - REPARTO EXPRESS 2.2 ###\n")

    # En demo usamos heurísticas del sistema (sin teclado)
    esc1 = preparar_tsp(semilla=1, stars=stars)
    ord1 = ruta_experta(esc1["entregas"])
    d1 = longitud_ruta(ord1, esc1["entregas"])
    base1 = longitud_ruta(ruta_vecino_mas_cercano(esc1["entregas"]), esc1["entregas"])
    s1 = puntuar_min(d1, base1)
    print(f"[1] TSP ★{stars}: experto={d1:.1f} | score_vs_NN={s1}/100")
    if plot:
        plot_puntos_y_ruta(esc1["entregas"], ord1, f"Demo M1 TSP ★{stars}", esc1["tam"])

    esc2 = preparar_cvrp(semilla=2, stars=stars)
    viajes = _heuristica_cvrp(esc2["entregas"], esc2["demanda"], esc2["capacidad"])
    d2 = sum(longitud_ruta(v, esc2["entregas"]) for v in viajes)
    print(f"[2] CVRP ★{stars}: heurística dist={d2:.1f}")

    esc3 = preparar_vrptw(semilla=3, stars=stars)
    edd = sorted(esc3["entregas"], key=lambda k: esc3["ventanas"][k][1])
    dist3, tard3, _ = _sim_vrptw(edd, esc3["entregas"], esc3["ventanas"], esc3["velocidad"])
    cost3 = dist3 + esc3["pen"] * tard3
    print(f"[3] VRPTW ★{stars}: EDD costo={cost3:.1f} tard={tard3:.1f}")

    esc4 = preparar_mochila(semilla=4, stars=stars)
    opt4, _ = knapsack_optimo(esc4["items"], esc4["capacidad"])
    print(f"[4] Knapsack ★{stars}: óptimo valor={opt4}")

    esc5 = preparar_dijkstra(semilla=5, stars=stars)
    c5, p5 = dijkstra(esc5["grafo"], esc5["origen"], esc5["destino"])
    print(f"[5] Dijkstra ★{stars}: costo óptimo={c5:.1f}  path={p5}")
    if plot:
        plot_grafo(esc5["puntos"], esc5["aristas"], p5, f"Demo M5 Dijkstra ★{stars}", esc5["tam"])

    esc6 = preparar_flota(semilla=6, stars=stars)
    grupos6 = _heuristica_flota(esc6["entregas"], esc6["k"])
    makes6 = max(_largos_grupos(grupos6, esc6["entregas"]))
    print(f"[6] Flota ★{stars}: makespan heurística={makes6:.1f}")

    esc7 = preparar_orienteering(semilla=7, stars=stars)
    opt7, ord7, dist7 = _orienteering_optimo(esc7["entregas"], esc7["premio"], esc7["presupuesto"], stars)
    print(f"[7] Orienteering ★{stars}: opt(acotado) premio={opt7} dist≈{dist7:.1f} orden={ord7}\n")


def autotest() -> int:
    fallos = 0

    def check(cond: bool, msg: str) -> None:
        nonlocal fallos
        if cond:
            print(f"  OK   {msg}")
        else:
            fallos += 1
            print(f"  FALLO {msg}")

    check(abs(distancia((0, 0), (3, 4)) - 5.0) < 1e-9, "distancia")

    for s in [1, 3, 5]:
        esc = preparar_tsp(semilla=42, stars=s)
        nn = ruta_vecino_mas_cercano(esc["entregas"])
        exp = ruta_experta(esc["entregas"])
        check(longitud_ruta(exp, esc["entregas"]) <= longitud_ruta(nn, esc["entregas"]) + 1e-9, f"TSP experto<=NN ★{s}")

    print("\n" + ("TODAS LAS PRUEBAS PASARON" if fallos == 0 else f"HUBO {fallos} FALLOS"))
    return fallos


# ===========================================================================
#  Main
# ===========================================================================

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(add_help=True)
    p.add_argument("--demo", action="store_true")
    p.add_argument("--test", action="store_true")
    p.add_argument("--plot", action="store_true", help="Matplotlib render")
    p.add_argument("--stars", type=int, default=3, help="Dificultad 1..5")
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--mision", type=int, default=None, help="1..7")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    stars = clamp(int(args.stars), 1, 5)

    if args.test:
        sys.exit(1 if autotest() else 0)

    # En Colab suele no haber TTY; si no especifican mision, hacemos demo.
    if args.demo or (not sys.stdin.isatty() and args.mision is None):
        demo(stars=stars, plot=args.plot)
        return

    m = args.mision
    if m is None:
        print("Usa: --mision N (1..7) --stars S (1..5) [--plot] [--seed 123]")
        return

    seed = args.seed

    if m == 1:
        esc = preparar_tsp(seed, stars)
        jugar_tsp(esc, plot=args.plot)
    elif m == 2:
        esc = preparar_cvrp(seed, stars)
        jugar_cvrp(esc, plot=args.plot)
    elif m == 3:
        esc = preparar_vrptw(seed, stars)
        jugar_vrptw(esc, plot=args.plot)
    elif m == 4:
        esc = preparar_mochila(seed, stars)
        jugar_mochila(esc)
    elif m == 5:
        esc = preparar_dijkstra(seed, stars)
        jugar_dijkstra(esc, plot=args.plot)
    elif m == 6:
        esc = preparar_flota(seed, stars)
        jugar_flota(esc, plot=args.plot)
    elif m == 7:
        esc = preparar_orienteering(seed, stars)
        jugar_orienteering(esc, plot=args.plot)
    else:
        print("La misión debe estar entre 1 y 7")


if __name__ == "__main__":
    main()
