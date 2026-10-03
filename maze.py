import os
import sys
import time
import traceback
from collections import deque

# Constants to identify maze elements
WALL = '#'
PATH = ' '
START = 'S'
EXIT = 'E'
CHARACTER = '@'   # Only used when rendering, never written into the grid
VISITED = '.'     # Only used when rendering, never written into the grid
SOLUTION = '*'    # Only used when rendering, never written into the grid


class Maze:
    """Encapsulates the maze grid and all queries/state about it.

    Coordinates are always (row, col) -> row = y, col = x.
    """

    # Order of the moves: up, down, left, right. It defines the exploration
    # order of BFS/DFS (so it changes which path DFS finds first).
    MOVES = [(-1, 0), (1, 0), (0, -1), (0, 1)]

    def __init__(self, grid, start_pos, exit_pos):
        self._grid = grid            # list of lists: grid[row][col]
        self._start = start_pos      # (row, col)
        self._exit = exit_pos        # (row, col)

        self._visited = set()        # fast lookup: "was (r, c) already visited?"
        self._visit_order = []       # order in which positions were visited
        self._current = None         # current character position (row, col)

        self._history = []           # chronological log of the search
        self._parent = {}            # parent[pos] = previous pos (for path rebuild)
        self._solution = []          # path found by the last solve()

    # ------------------------------------------------------------------
    # Dimensions
    # ------------------------------------------------------------------
    def num_rows(self):
        return len(self._grid)

    def num_cols(self):
        # Uses the widest row, since lines in the file may have different lengths
        return max((len(row) for row in self._grid), default=0)

    def dimensions(self):
        return self.num_rows(), self.num_cols()

    # ------------------------------------------------------------------
    # Position queries
    # ------------------------------------------------------------------
    def in_bounds(self, row, col):
        return 0 <= row < self.num_rows() and 0 <= col < len(self._grid[row])

    def get_cell(self, row, col):
        if not self.in_bounds(row, col):
            return WALL   # outside the grid behaves like a wall
        return self._grid[row][col]

    def is_start(self, row, col):
        return (row, col) == self._start

    def is_exit(self, row, col):
        return (row, col) == self._exit

    def is_wall(self, row, col):
        return self.get_cell(row, col) == WALL

    def is_path(self, row, col):
        # Start and exit are also walkable cells
        return self.get_cell(row, col) in (PATH, START, EXIT)

    def get_start(self):
        return self._start

    def get_exit(self):
        return self._exit

    def neighbors(self, row, col):
        """Returns the walkable neighbors of (row, col) (4 directions)."""
        result = []
        for d_row, d_col in self.MOVES:
            r, c = row + d_row, col + d_col
            if self.is_path(r, c):   # False for walls and out-of-bounds cells
                result.append((r, c))
        return result

    def successors(self, pos):
        """Successor function: states reachable from pos (every step costs 1)."""
        return self.neighbors(*pos)

    def goal_test(self, pos):
        """Goal test: is pos the exit?"""
        return self.is_exit(*pos)

    # ------------------------------------------------------------------
    # Visited positions
    # ------------------------------------------------------------------
    def visit(self, row, col):
        """Marks (row, col) as visited. Returns False if already visited or not walkable."""
        pos = (row, col)
        if not self.is_path(row, col) or pos in self._visited:
            return False
        self._visited.add(pos)
        self._visit_order.append(pos)
        return True

    def was_visited(self, row, col):
        return (row, col) in self._visited

    def get_visited(self):
        return list(self._visit_order)

    def reset_visits(self):
        self._visited.clear()
        self._visit_order.clear()
        self._history.clear()
        self._parent.clear()
        self._solution = []
        self._current = None

    # ------------------------------------------------------------------
    # Character (current position) - does NOT modify the grid
    # ------------------------------------------------------------------
    def place_character(self, row, col):
        if not self.is_path(row, col):
            raise ValueError(f"Cannot place character on non-walkable cell {(row, col)}")
        self._current = (row, col)

    def get_character_pos(self):
        return self._current

    def restart(self):
        """Clears everything and puts the character back at the start."""
        self.reset_visits()
        self.place_character(*self._start)
        self.visit(*self._start)

    def move(self, d_row, d_col):
        """Tries to move the character. Returns True if it moved."""
        if self._current is None:
            return False
        r, c = self._current[0] + d_row, self._current[1] + d_col
        if not self.is_path(r, c):   # wall or outside the grid
            return False
        self._current = (r, c)
        self.visit(r, c)             # leaves the blue trail
        return True

    # ------------------------------------------------------------------
    # History
    # ------------------------------------------------------------------
    def record_step(self, pos, came_from):
        """Registers a step of the search in the history and in the parent map."""
        self._history.append(pos)
        if pos not in self._parent:
            self._parent[pos] = came_from   # None for the start

    def get_history(self):
        """Returns the chronological list of steps (every position the search touched)."""
        return list(self._history)

    def get_solution(self):
        return list(self._solution)

    def build_path(self):
        """Rebuilds the path from START to EXIT following the parent map backwards."""
        if self._exit not in self._parent:
            return []
        path = []
        pos = self._exit
        while pos is not None:
            path.append(pos)
            pos = self._parent.get(pos)
        path.reverse()
        return path

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------
    def solve(self, method="bfs", on_step=None):
        """Searches the maze from START to EXIT with 'bfs' or 'dfs'.

        on_step: optional callback (e.g. view.update) called at each step so
        the view can animate the search.
        Returns the list of positions from START to EXIT, or [] if unreachable.
        """
        if self._start is None or self._exit is None:
            return []
        self.reset_visits()
        if method == "bfs":
            path = self._bfs(on_step)
        elif method == "dfs":
            path = self._dfs(on_step)
        else:
            raise ValueError("method must be 'bfs' or 'dfs'")
        self._solution = path
        if on_step and path:
            on_step(self)   # draw the final path
        return path

    def _bfs(self, on_step):
        queue = deque([self._start])
        self.visit(*self._start)               # BFS marks when ENTERING the queue
        self.record_step(self._start, None)
        while queue:
            pos = queue.popleft()
            self.place_character(*pos)
            if on_step:
                on_step(self)
            if self.goal_test(pos):
                return self.build_path()
            for nb in self.successors(pos):
                if self.visit(*nb):            # True only if never seen before
                    self.record_step(nb, pos)
                    queue.append(nb)
        return []

    def _dfs(self, on_step):
        stack = [(self._start, None)]          # (position, who pushed it)
        while stack:
            pos, parent = stack.pop()
            if self.was_visited(*pos):         # DFS marks when LEAVING the stack
                continue
            self.visit(*pos)
            self.record_step(pos, parent)
            self.place_character(*pos)
            if on_step:
                on_step(self)
            if self.goal_test(pos):
                return self.build_path()
            for nb in reversed(self.successors(pos)):   # reversed -> explores in MOVES order
                if not self.was_visited(*nb):
                    stack.append((nb, pos))
        return []

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------
    def render(self, show_visited=True):
        """Builds a string of the maze with overlays (path + visited + character)
        without changing the original grid."""
        solution = set(self._solution)
        lines = []
        for r, row in enumerate(self._grid):
            chars = []
            for c, ch in enumerate(row):
                if (r, c) == self._current:
                    chars.append(CHARACTER)
                elif ch == WALL:
                    chars.append('#')
                elif ch == START:
                    chars.append('S')
                elif ch == EXIT:
                    chars.append('E')
                elif (r, c) in solution:
                    chars.append(SOLUTION)
                elif show_visited and (r, c) in self._visited:
                    chars.append(VISITED)
                elif ch == PATH:
                    chars.append(' ')
                else:
                    chars.append(ch)
            lines.append("".join(chars))
        return "\n".join(lines)


def describe(method, path, maze):
    """One-line summary of a search result."""
    if not path:
        return f"{method.upper()}: no solution"
    return (f"{method.upper()}: {len(path) - 1} steps, "
            f"{len(maze.get_history())} cells explored")


# ======================================================================
# Views - they only READ the Maze through its public methods
# ======================================================================
class TerminalView:
    """Character-based view (fallback)."""

    HELP = "w/a/s/d = move | 1 = BFS | 2 = DFS | r = restart | q = quit"

    def _redraw(self, maze):
        os.system('cls' if os.name == 'nt' else 'clear')
        print(maze.render())

    def show(self, maze, title=None):
        """Draws the current state once."""
        if title:
            print(f"\n[*] {title}")
        print(maze.render())

    def update(self, maze):
        """Called at each step of a search (for animation)."""
        self._redraw(maze)
        time.sleep(0.05)

    def play(self, maze):
        keys = {'w': (-1, 0), 's': (1, 0), 'a': (0, -1), 'd': (0, 1)}
        moves = 0
        locked = False   # after winning or after a search, only 'r' / 'q' work
        msg = ""
        while True:
            self._redraw(maze)
            if msg:
                print(msg)
            try:
                cmd = input(self.HELP + "\n> ").strip().lower()
            except EOFError:
                return
            msg = ""
            if cmd == 'q':
                return
            if cmd == 'r':
                maze.restart()
                moves = 0
                locked = False
            elif cmd in ('1', '2'):
                method = 'bfs' if cmd == '1' else 'dfs'
                path = maze.solve(method, on_step=self.update)
                msg = describe(method, path, maze)
                locked = True
            elif locked:
                msg = "Press r to restart."
            else:
                for ch in cmd:
                    if ch in keys and maze.move(*keys[ch]):
                        moves += 1
                        if maze.goal_test(maze.get_character_pos()):
                            msg = f"You won in {moves} moves! (r restarts)"
                            locked = True
                            break

    def wait(self):
        pass

    def close(self):
        pass


class PygameView:
    """Graphical view using pygame (python -m pip install pygame)."""

    COLORS = {
        'wall':      (40, 40, 40),
        'path':      (235, 235, 235),
        'visited':   (160, 200, 255),
        'solution':  (250, 170, 60),
        'start':     (60, 180, 75),
        'exit':      (220, 50, 50),
        'character': (255, 200, 0),
        'grid':      (200, 200, 200),
        'bar':       (30, 30, 30),
    }
    HELP = "Arrows/WASD: move | 1: BFS | 2: DFS | R: restart | ESC: quit"
    BAR = 30   # height of the status bar under the maze

    def __init__(self, cell_size=48, step_delay_ms=60):
        import pygame   # imported here so terminal mode doesn't require pygame
        self.pg = pygame
        self.cell = cell_size
        self.delay = step_delay_ms
        self.screen = None
        self.font = None
        self.status = ""
        pygame.init()
        pygame.display.init()   # raises pygame.error when there is no display

    def _ensure_window(self, maze):
        if self.screen is None:
            rows, cols = maze.dimensions()
            width = max(cols * self.cell, 520)
            self.screen = self.pg.display.set_mode((width, rows * self.cell + self.BAR))
            self.pg.display.set_caption("Maze")
            self.font = self.pg.font.Font(None, 22)

    def _cell_color(self, maze, r, c):
        if maze.get_character_pos() == (r, c):
            return self.COLORS['character']
        if maze.is_start(r, c):
            return self.COLORS['start']
        if maze.is_exit(r, c):
            return self.COLORS['exit']
        if maze.is_wall(r, c):
            return self.COLORS['wall']
        if (r, c) in maze.get_solution():
            return self.COLORS['solution']
        if maze.was_visited(r, c):
            return self.COLORS['visited']
        return self.COLORS['path']

    def _draw(self, maze):
        self._ensure_window(maze)
        rows, cols = maze.dimensions()
        self.screen.fill(self.COLORS['bar'])
        for r in range(rows):
            for c in range(cols):
                rect = (c * self.cell, r * self.cell, self.cell, self.cell)
                self.pg.draw.rect(self.screen, self._cell_color(maze, r, c), rect)
                self.pg.draw.rect(self.screen, self.COLORS['grid'], rect, 1)
        text = self.font.render(self.status, True, (255, 255, 255))
        self.screen.blit(text, (8, rows * self.cell + 8))
        self.pg.display.flip()

    def _pump_events(self):
        # Only takes QUIT events, so key presses are not swallowed here
        for _ in self.pg.event.get(self.pg.QUIT):
            self.close()
            raise SystemExit

    def show(self, maze, title=None):
        if title is not None:
            self.status = title
        self._draw(maze)
        self._pump_events()

    def update(self, maze):
        """Called at each step of a search (for animation)."""
        self._draw(maze)
        self._pump_events()
        self.pg.time.delay(self.delay)

    def play(self, maze):
        pg = self.pg
        keys = {
            pg.K_UP: (-1, 0), pg.K_w: (-1, 0),
            pg.K_DOWN: (1, 0), pg.K_s: (1, 0),
            pg.K_LEFT: (0, -1), pg.K_a: (0, -1),
            pg.K_RIGHT: (0, 1), pg.K_d: (0, 1),
        }
        moves = 0
        locked = False   # after winning or after a search, only R / ESC work
        self.show(maze, self.HELP)

        while True:
            for event in pg.event.get():
                if event.type == pg.QUIT:
                    return
                if event.type != pg.KEYDOWN:
                    continue

                if event.key == pg.K_ESCAPE:
                    return
                elif event.key == pg.K_r:
                    maze.restart()
                    moves = 0
                    locked = False
                    self.show(maze, self.HELP)
                elif event.key in (pg.K_1, pg.K_2):
                    method = 'bfs' if event.key == pg.K_1 else 'dfs'
                    path = maze.solve(method, on_step=self.update)
                    pg.event.clear(pg.KEYDOWN)   # dro8p keys pressed during the animation
                    locked = True
                    self.show(maze, describe(method, path, maze) + "  (R restarts)")
                elif event.key in keys and not locked:
                    if maze.move(*keys[event.key]):
                        moves += 1
                        if maze.goal_test(maze.get_character_pos()):
                            locked = True
                            self.show(maze, f"You won in {moves} moves! (R restarts)")
                        else:
                            self.show(maze, self.HELP)
            pg.time.delay(15)

    def wait(self):
        pass

    def close(self):
        self.pg.quit()


def create_view(mode):
    if mode == "pygame":
        try:
            return PygameView()
        except ImportError:
            print("[-] pygame is not installed (python -m pip install pygame). "
                  "Falling back to terminal view.")
        except Exception as e:   # e.g. no display available
            print(f"[-] Could not start pygame ({e}). Falling back to terminal view.")
    return TerminalView()


# Numeric files (1 wall, 0 free, 2 start, 3 exit) are converted to the symbols above
NUMERIC = {'1': WALL, '0': PATH, '2': START, '3': EXIT}


def load(file_path):
    grid = []
    start_pos = None
    exit_pos = None

    with open(file_path, 'r', encoding='utf-8') as file:
        for line in file:
            raw = line.rstrip('\r\n')   # also removes '\r' from Windows files
            if not raw.strip():
                continue
            r_idx = len(grid)   # real row index (ignores skipped blank lines)
            if any(ch in raw for ch in '0123'):
                # numeric format: accepts both "0 1 0 2" and "0102"
                clean_line = raw.strip()
                chars = clean_line.split() if ' ' in clean_line else list(clean_line)
                char_list = [NUMERIC.get(ch, ch) for ch in chars]
            else:
                # symbol format: spaces are free cells, keep them
                char_list = list(raw)
            grid.append(char_list)

            for c_idx, char in enumerate(char_list):
                if char == START:
                    start_pos = (r_idx, c_idx)
                elif char == EXIT:
                    exit_pos = (r_idx, c_idx)

    return Maze(grid, start_pos, exit_pos)


def main():
    # Choose the visualization: pygame (default) or terminal (python maze.py --terminal)
    VIEW_MODE = "terminal" if "--terminal" in sys.argv else "pygame"

    print("=== MAZE LOADER SYSTEM ===")
    print("Available options: Mazes from 1 to 10")

    view = None
    try:
        choice = input("Enter the maze number you want to load (1-10): ").strip()

        if not choice.isdigit() or not (1 <= int(choice) <= 10):
            print("[-] Invalid input! Please enter a number between 1 and 10.")
            return

        file_name = f"{choice}_maze.txt"

        if not os.path.exists(file_name):
            print(f"[-] Error: File '{file_name}' not found. Please create it first.")
            return

        maze = load(file_name)
        rows, cols = maze.dimensions()

        print(f"\n[+] Successfully loaded: {file_name}")
        print(f"[*] Dimensions: {rows} rows x {cols} columns")
        print(f"[*] Start (S) coordinates: {maze.get_start()}")
        print(f"[*] Exit (E) coordinates:  {maze.get_exit()}\n")

        if maze.get_start() is None or maze.get_exit() is None:
            print("[-] This maze needs one start (S) and one exit (E).")
            return

        # Final result of each method: the path from start to exit
        for method in ("bfs", "dfs"):
            path = maze.solve(method)
            print(f"[*] {describe(method, path, maze)}")
            if path:
                print(f"    Path: {path}")

        view = create_view(VIEW_MODE)
        maze.restart()
        view.play(maze)

    except SystemExit:
        pass
    except Exception:
        traceback.print_exc()
    finally:
        if view is not None:
            try:
                view.close()
            except Exception:
                pass


if __name__ == "__main__":
    main()