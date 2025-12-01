import numpy as np
from PIL import Image, ImageDraw
from typing import Tuple, Any

def largest_rectangle_area(heights: np.ndarray) -> Tuple[int, int, int, int]:
    """
    Calcula o maior retângulo possível em um histograma.

    Esta função utiliza um algoritmo baseado em pilha para encontrar a maior área retangular
    em um histograma em tempo linear O(N).

    Args:
        heights (np.ndarray): Array numpy contendo as alturas das barras do histograma.

    Returns:
        Tuple[int, int, int, int]: Uma tupla contendo:
            - max_area (int): A área máxima encontrada.
            - height (int): A altura do retângulo.
            - x_start (int): O índice inicial (coluna) do retângulo.
            - width (int): A largura do retângulo.
    """
    stack = [-1]
    max_area = 0
    best_rect = (0, 0, 0, 0) # area, height, x_start, width
    
    # Adiciona 0 no final para garantir que todos os elementos sejam processados
    heights_extended = np.append(heights, 0)
    
    for i, h in enumerate(heights_extended):
        while stack[-1] != -1 and heights_extended[stack[-1]] >= h:
            height = heights_extended[stack.pop()]
            width = i - stack[-1] - 1
            area = height * width
            if area > max_area:
                max_area = area
                # x_start é stack[-1] + 1
                best_rect = (area, height, stack[-1] + 1, width)
        stack.append(i)
        
    return best_rect

def find_largest_rectangle_raster(canvas: Any, resolution: int = 10) -> Tuple[float, float, float, float]:
    """
    Encontra o maior retângulo vazio no canvas utilizando rasterização.

    Esta função converte o canvas vetorial (polígonos e círculos) em uma grade discreta (imagem)
    e aplica o algoritmo de "Maior Retângulo em Histograma" iterativamente para cada linha da imagem.
    É uma abordagem aproximada cuja precisão depende da resolução escolhida.

    Args:
        canvas (Canvas): O objeto Canvas contendo as dimensões e a lista de obstáculos (polígonos e círculos).
        resolution (int, optional): A resolução da rasterização em pixels por unidade de medida. 
                                    Padrão é 10. Valores maiores aumentam a precisão e o tempo de execução.

    Returns:
        Tuple[float, float, float, float]: Uma tupla contendo:
            - center_x (float): A coordenada X do centro do maior retângulo vazio.
            - center_y (float): A coordenada Y do centro do maior retângulo vazio.
            - width (float): A largura do retângulo encontrado.
            - height (float): A altura do retângulo encontrado.
    """
    width_px = int(canvas.x_dimension * resolution)
    height_px = int(canvas.y_dimension * resolution)
    
    # Cria uma imagem preenchida com 1 (espaço livre)
    img = Image.new('L', (width_px, height_px), 1)
    draw = ImageDraw.Draw(img)
    
    # Desenha polígonos (preenche com 0)
    for polygon in canvas.polygons:
        transformed_pixels = [(x * resolution, height_px - (y * resolution)) for x, y in polygon.points]
        draw.polygon(transformed_pixels, outline=0, fill=0)
        
    # Desenha círculos (preenche com 0)
    for circle in canvas.circles:
        cx, cy = circle.center
        r = circle.radius
        x0 = (cx - r) * resolution
        y0 = height_px - (cy + r) * resolution
        x1 = (cx + r) * resolution
        y1 = height_px - (cy - r) * resolution
        draw.ellipse([x0, y0, x1, y1], outline=0, fill=0)
        
    # Converte para array numpy (0 = obstáculo, 1 = livre)
    grid = np.array(img)
    
    # Algoritmo do Maior Retângulo em Matriz Binária
    max_area_global = 0
    best_rect_global = None # (x_px, y_px_bottom, w_px, h_px)
    
    # Histograma acumulado
    heights = np.zeros(width_px, dtype=int)
    
    for row in range(height_px):
        # Atualiza histograma: se grid[row][col] é 1, soma 1, senão zera
        # grid[row] é uma linha. Onde for 0, heights vira 0. Onde for 1, heights += 1.
        # Note: grid tem 0 para obstáculo e 1 para livre.
        # Se grid[row][c] == 0 -> heights[c] = 0
        # Se grid[row][c] == 1 -> heights[c] += 1
        
        # Vetorizado:
        mask = (grid[row] == 1)
        heights[mask] += 1
        heights[~mask] = 0
        
        area, h, x_start, w = largest_rectangle_area(heights)
        
        if area > max_area_global:
            max_area_global = area
            # row é a linha inferior do retângulo (y_bottom na imagem, que cresce para baixo)
            # y_top na imagem seria row - h + 1
            best_rect_global = (x_start, row, w, h)
            
    if best_rect_global is None:
        return 0.0, 0.0, 0.0, 0.0

    x_px_start, y_px_bottom, w_px, h_px = best_rect_global
    
    # Converter para coordenadas do Canvas
    width = w_px / resolution
    height = h_px / resolution
    
    x_min = x_px_start / resolution
    center_x = x_min + width / 2
    
    # y_px_bottom é a linha mais baixa na imagem (maior índice).
    # y_center_img = row - h_px / 2
    y_center_img = y_px_bottom - h_px / 2 + 0.5 # +0.5 para centralizar no pixel
    center_y = (height_px - y_center_img) / resolution
    
    return center_x, center_y, width, height

# Alias para manter compatibilidade
find_largest_rectangle = find_largest_rectangle_raster