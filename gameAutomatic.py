"""
gameAutomatic.py
Ambiente completo herdado do AllGame.py + 3 agentes comparáveis.

Agentes:
  - random     : ações uniformemente aleatórias
  - bfs        : BFS guloso direto ao Cálice
  - item_hunter: BFS para Espada → depois BFS para Cálice

Uso:
  python gameAutomatic.py --runs 200 --outdir data
  python gameAutomatic.py --runs 200 --outdir data --agent bfs
  python gameAutomatic.py --runs 200 --outdir data --agent item_hunter
"""

import random
import math
import argparse
import os
from collections import deque
from perlin_noise import PerlinNoise
from GameAnalytics import GameAnalytics

# ==========================================
# ARGPARSE
# ==========================================
parser = argparse.ArgumentParser()
parser.add_argument("--runs",   type=int, default=1)
parser.add_argument("--outdir", type=str, default="data")
parser.add_argument("--agent",  type=str, default="random",
                    choices=["random", "bfs", "item_hunter"])
parser.add_argument("--max_steps", type=int, default=2000)
args = parser.parse_args()

# ==========================================
# CONFIG (espelho do AllGame.py)
# ==========================================
LARGURA, ALTURA   = 800, 600
CELL_SIZE         = 12
COLS, ROWS        = LARGURA // CELL_SIZE, ALTURA // CELL_SIZE
NUMERO_BARCOS     = 5
VISION_RADIUS     = 10

# ==========================================
# ESTADO GLOBAL
# ==========================================
grid_biome    = []
grid_cave     = []
grid_trees    = []
grid_items    = []
grid_boats    = []
grid_explored = []
active_enemies = []

player = {
    "x": 0, "y": 0,
    "score": 0,
    "in_boat": False,
    "hp": 100,
    "has_sword": False,
    "won": False
}

analytics: GameAnalytics = None

# ==========================================
# FOG OF WAR
# ==========================================
def update_fog():
    px, py = player["x"], player["y"]
    for y in range(max(0, py - VISION_RADIUS), min(ROWS, py + VISION_RADIUS + 1)):
        for x in range(max(0, px - VISION_RADIUS), min(COLS, px + VISION_RADIUS + 1)):
            if (x-px)**2 + (y-py)**2 < VISION_RADIUS**2:
                grid_explored[y][x] = True

# ==========================================
# PATHFINDING — BFS walkable (terra + caverna aberta)
# Retorna o primeiro passo em direção a target, ou None
# ==========================================
def get_next_step(start, target):
    sx, sy = start
    tx, ty = target

    if (sx, sy) == (tx, ty):
        return None

    queue   = deque([(sx, sy)])
    parents = {}
    visited = {(sx, sy)}

    while queue:
        cx, cy = queue.popleft()
        if (cx, cy) == (tx, ty):
            break
        for dx, dy in [(-1,0),(1,0),(0,-1),(0,1)]:
            nx, ny = cx+dx, cy+dy
            if (nx, ny) in visited:
                continue
            if not (0 <= nx < COLS and 0 <= ny < ROWS):
                continue
            h        = grid_biome[ny][nx]
            is_water = h < -0.05
            is_wall  = (h >= 0.3 and grid_cave[ny][nx] == 1)
            has_tree = grid_trees[ny][nx]
            if not is_water and not is_wall and not has_tree:
                visited.add((nx, ny))
                parents[(nx, ny)] = (cx, cy)
                queue.append((nx, ny))

    if (tx, ty) not in parents:
        return None

    # Reconstrói primeiro passo
    step = (tx, ty)
    while parents[step] != (sx, sy):
        step = parents[step]
    return step

# ==========================================
# GERAÇÃO DE MUNDO (herdada do AllGame.py)
# ==========================================
def generate_world():
    global grid_biome, grid_cave, grid_trees, grid_items
    global grid_boats, grid_explored, active_enemies

    active_enemies        = []
    player["won"]         = False
    player["has_sword"]   = False
    player["hp"]          = 100
    player["score"]       = 0
    player["in_boat"]     = False

    noise_height = PerlinNoise(octaves=4,  seed=random.randint(1, 10000))
    noise_forest = PerlinNoise(octaves=10, seed=random.randint(1, 10000))
    noise_danger = PerlinNoise(octaves=6,  seed=random.randint(1, 10000))

    # Cellular automata para cavernas
    grid_cave = [[random.choice([0,1]) for _ in range(COLS)] for _ in range(ROWS)]
    for _ in range(5):
        new_cave = [[0]*COLS for _ in range(ROWS)]
        for y in range(ROWS):
            for x in range(COLS):
                walls = sum(
                    grid_cave[ny][nx]
                    for ny in range(max(0,y-1), min(ROWS,y+2))
                    for nx in range(max(0,x-1), min(COLS,x+2))
                )
                new_cave[y][x] = 1 if walls > 4 else 0
        grid_cave = new_cave

    grid_biome    = [[0.0]*COLS for _ in range(ROWS)]
    grid_trees    = [[False]*COLS for _ in range(ROWS)]
    grid_items    = [[None]*COLS for _ in range(ROWS)]
    grid_boats    = [[False]*COLS for _ in range(ROWS)]
    grid_explored = [[False]*COLS for _ in range(ROWS)]

    valid_spots = []

    for y in range(ROWS):
        for x in range(COLS):
            h = noise_height([x/COLS, y/ROWS])
            grid_biome[y][x] = h

            is_water      = h < -0.05
            is_mountain   = h >= 0.3
            is_cave_wall  = is_mountain and grid_cave[y][x] == 1
            is_cave_floor = is_mountain and grid_cave[y][x] == 0
            is_ground     = not is_water and not is_mountain

            if is_ground and noise_forest([x/COLS, y/ROWS]) > 0.1:
                grid_trees[y][x] = True

            if not is_cave_wall and not grid_trees[y][x] and not is_water:
                valid_spots.append((x, y))

                danger_val = noise_danger([x/COLS, y/ROWS])
                if danger_val > 0.30:
                    e_type = "SKELETON" if is_cave_floor else "GOBLIN"
                    active_enemies.append({
                        "x": x, "y": y,
                        "type": e_type,
                        "id": len(active_enemies)
                    })
                elif random.random() < 0.05:
                    roll = random.random()
                    if   roll < 0.4: grid_items[y][x] = "MACA"
                    elif roll < 0.7: grid_items[y][x] = "FLOR"
                    else:            grid_items[y][x] = "COBRE"

    _spawn_player()
    _place_boats()

    # Itens especiais — longe do player (embaralha e pega do fim da lista)
    random.shuffle(valid_spots)
    if valid_spots:
        cx, cy = valid_spots.pop()
        grid_items[cy][cx] = "CALICE"
    if valid_spots:
        sx, sy = valid_spots.pop()
        grid_items[sy][sx] = "ESPADA"

    update_fog()
    analytics.log_event("SPAWN_PLAYER", player["x"], player["y"])

def _spawn_player():
    while True:
        x = random.randint(0, COLS-1)
        y = random.randint(0, ROWS-1)
        if -0.05 <= grid_biome[y][x] < 0.3 and not grid_trees[y][x]:
            player["x"], player["y"] = x, y
            return

def _place_boats():
    """Garante pelo menos 1 barco adjacente ao player (espelho do AllGame)."""
    boats_placed = 0
    queue   = deque([(player["x"], player["y"])])
    visited = {(player["x"], player["y"])}
    starter = False

    while queue and not starter:
        cx, cy = queue.popleft()
        for dx, dy in [(-1,0),(1,0),(0,-1),(0,1)]:
            nx, ny = cx+dx, cy+dy
            if not (0 <= nx < COLS and 0 <= ny < ROWS):
                continue
            h = grid_biome[ny][nx]
            if h < -0.05:
                grid_boats[ny][nx] = True
                boats_placed += 1
                starter = True
                break
            if not (h >= 0.3 and grid_cave[ny][nx] == 1) and not grid_trees[ny][nx]:
                if (nx, ny) not in visited:
                    visited.add((nx, ny))
                    queue.append((nx, ny))

    attempts = 0
    while boats_placed < NUMERO_BARCOS and attempts < 2000:
        bx = random.randint(1, COLS-2)
        by = random.randint(1, ROWS-2)
        if grid_biome[by][bx] < -0.05 and not grid_boats[by][bx]:
            grid_boats[by][bx] = True
            boats_placed += 1
        attempts += 1

# ==========================================
# MECÂNICAS DE TURNO (espelho do AllGame.py)
# ==========================================
def _move_enemies():
    if player["in_boat"] or player["won"]:
        return
    for enemy in active_enemies:
        dist = math.sqrt((enemy["x"]-player["x"])**2 + (enemy["y"]-player["y"])**2)
        if dist >= 8:
            continue
        step = get_next_step((enemy["x"], enemy["y"]), (player["x"], player["y"]))
        if not step:
            continue
        nx, ny = step
        occupied = any(
            e["id"] != enemy["id"] and e["x"] == nx and e["y"] == ny
            for e in active_enemies
        )
        if (nx, ny) == (player["x"], player["y"]):
            if not player["has_sword"]:
                player["hp"] -= 10
                analytics.log_event("PLAYER_HIT", player["x"], player["y"],
                                    extra=enemy["type"])
        elif not occupied:
            enemy["x"], enemy["y"] = nx, ny

def try_move(dx, dy, action_name):
    if player["won"] or player["hp"] <= 0:
        return

    tx, ty = player["x"]+dx, player["y"]+dy
    if not (0 <= tx < COLS and 0 <= ty < ROWS):
        return

    analytics.log_action(action_name)

    h        = grid_biome[ty][tx]
    is_water = h < -0.05
    is_wall  = h >= 0.3 and grid_cave[ty][tx] == 1
    has_tree = grid_trees[ty][tx]

    # Combate
    enemy_hit = next((e for e in active_enemies if e["x"]==tx and e["y"]==ty), None)
    if enemy_hit:
        damage = 40 if player["has_sword"] else 20
        player["score"] += damage
        active_enemies.remove(enemy_hit)
        analytics.log_event("KILL_ENEMY", tx, ty, extra=enemy_hit["type"])
        analytics.enemies_killed += 1
        _move_enemies()
        analytics.next_step()
        _log_positions()
        return

    # Movimento
    moved = False
    if player["in_boat"]:
        if not is_wall and not has_tree:
            if not is_water:
                player["in_boat"] = False
                grid_boats[player["y"]][player["x"]] = True
            player["x"], player["y"] = tx, ty
            moved = True
    else:
        if grid_boats[ty][tx]:
            player["in_boat"] = True
            grid_boats[ty][tx] = False
            player["x"], player["y"] = tx, ty
            moved = True
        elif not is_water and not is_wall and not has_tree:
            player["x"], player["y"] = tx, ty
            moved = True

            item = grid_items[ty][tx]
            if item:
                if item == "MACA":
                    player["hp"] = min(100, player["hp"]+20)
                    analytics.log_event("COLLECT_MACA", tx, ty)
                elif item == "ESPADA":
                    player["has_sword"] = True
                    analytics.log_event("COLLECT_ESPADA", tx, ty)
                elif item == "CALICE":
                    player["won"]    = True
                    player["score"] += 1000
                    analytics.log_event("WIN", tx, ty)
                elif item == "COBRE":
                    player["score"] += 5
                elif item == "FLOR":
                    player["score"] += 2
                grid_items[ty][tx] = None

    if moved:
        update_fog()
        _move_enemies()

    analytics.next_step()
    _log_positions()

def _log_positions():
    analytics.log_position("player", player["x"], player["y"])
    for e in active_enemies:
        analytics.log_position(f"enemy_{e['id']}", e["x"], e["y"])

# ==========================================
# AGENTES
# ==========================================

# --- Utilidade compartilhada ---
def _find_item_on_map(item_name):
    """Varre o grid_items e retorna (x, y) do item, ou None."""
    for y in range(ROWS):
        for x in range(COLS):
            if grid_items[y][x] == item_name:
                return (x, y)
    return None

def _random_action():
    return random.choice([
        (0,-1,"UP"),(0,1,"DOWN"),(-1,0,"LEFT"),(1,0,"RIGHT")
    ])

# --- Agente 1: Random ---
def agent_random():
    try_move(*_random_action())

# --- Agente 2: BFS guloso direto ao Cálice ---
def agent_bfs():
    target = _find_item_on_map("CALICE")
    if target is None:
        # Cálice não visível ainda — explora aleatoriamente
        try_move(*_random_action())
        return

    step = get_next_step((player["x"], player["y"]), target)
    if step:
        dx = step[0] - player["x"]
        dy = step[1] - player["y"]
        action = {(-1,0):"LEFT",(1,0):"RIGHT",(0,-1):"UP",(0,1):"DOWN"}.get((dx,dy),"UP")
        try_move(dx, dy, action)
    else:
        try_move(*_random_action())

# --- Agente 3: Item Hunter — Espada primeiro, depois Cálice ---
def agent_item_hunter():
    # Fase 1: busca Espada se ainda não tem
    if not player["has_sword"]:
        target = _find_item_on_map("ESPADA")
    else:
        target = _find_item_on_map("CALICE")

    if target is None:
        # Ainda não explorou a região do item — explora
        try_move(*_random_action())
        return

    step = get_next_step((player["x"], player["y"]), target)
    if step:
        dx = step[0] - player["x"]
        dy = step[1] - player["y"]
        action = {(-1,0):"LEFT",(1,0):"RIGHT",(0,-1):"UP",(0,1):"DOWN"}.get((dx,dy),"UP")
        try_move(dx, dy, action)
    else:
        try_move(*_random_action())

AGENTS = {
    "random":      agent_random,
    "bfs":         agent_bfs,
    "item_hunter": agent_item_hunter,
}

# ==========================================
# LOOP PRINCIPAL HEADLESS
# ==========================================
def run_headless():
    global analytics

    agent_fn = AGENTS[args.agent]

    for run in range(args.runs):
        analytics = GameAnalytics(match_id=run, agent=args.agent)
        analytics.log_event("AGENT_TYPE", extra=args.agent)

        generate_world()
        _log_positions()

        while not player["won"] and player["hp"] > 0 and analytics.step < args.max_steps:
            agent_fn()

        analytics.save(
            outdir    = args.outdir,
            win       = player["won"],
            score     = player["score"],
            hp_final  = player["hp"],
        )

        status = "WIN" if player["won"] else ("DEAD" if player["hp"] <= 0 else "TIMEOUT")
        print(f"[{args.agent}] run={run:>4}  steps={analytics.step:>5}  "
              f"score={player['score']:>6}  hp={player['hp']:>3}  {status}")

if __name__ == "__main__":
    run_headless()
