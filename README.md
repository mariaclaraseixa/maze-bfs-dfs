# Busca em largura (BFS) e em profundidade (DFS) em labirinto

Implementação dos métodos de busca em largura e em profundidade para encontrar o caminho entre o início e a chegada de um labirinto.

## Requisitos

- Python 3.8 ou superior
- pygame para a interface gráfica: `python -m pip install pygame`

Sem o pygame, o programa usa o modo terminal automaticamente.

## Formato dos labirintos

Os arquivos `1_maze.txt` até `10_maze.txt` ficam na mesma pasta do `maze.py`.

Formato numérico: `1` parede, `0` livre, `2` início, `3` chegada. As linhas podem ter espaços (`0 1 0 2`) ou não (`0102`).

Formato com símbolos: `#` parede, espaço livre, `S` início, `E` chegada.

## Como executar

    python maze.py             # interface gráfica
    python maze.py --terminal  # modo terminal

Digite o número do labirinto (1 a 10). O programa imprime, para BFS e DFS, o número de passos, as células exploradas e o caminho do início até a chegada.

## Controles

Interface gráfica: setas ou WASD movem o personagem, `1` anima a BFS, `2` anima a DFS (o caminho encontrado fica em laranja), `R` reinicia e `ESC` sai.

Modo terminal: `w/a/s/d` + Enter para mover, `1` BFS, `2` DFS, `r` reinicia e `q` sai.

## Implementação

- `Maze.successors(pos)`: função sucessor (4 direções, custo 1 por passo)
- `Maze.goal_test(pos)`: teste de objetivo
- `Maze._bfs`: busca em largura com fila. Encontra o caminho mais curto.
- `Maze._dfs`: busca em profundidade com pilha. Encontra um caminho, não necessariamente o mais curto.

Se não existir caminho entre o início e a chegada, o programa informa `no solution`.
