import numpy as np
from scipy.ndimage import distance_transform_cdt
from PIL import Image, ImageDraw

def find_largest_square(canvas, resolution=10):
    """
    Encontra o maior quadrado vazio no canvas usando Transformada de Distância.
    
    Args:
        canvas: Objeto Canvas contendo as dimensões e obstáculos.
        resolution: Pixels por unidade de medida do canvas.
        
    Returns:
        tuple: (center_x, center_y, radius) onde radius é metade do lado do quadrado.
    """
    width_px = int(canvas.x_dimension * resolution)
    height_px = int(canvas.y_dimension * resolution)
    
    # Cria uma imagem preenchida com 1 (espaço livre)
    # Usamos 'L' (8-bit pixels, black and white)
    # 1 representa livre, 0 representa obstáculo
    img = Image.new('L', (width_px, height_px), 1)
    draw = ImageDraw.Draw(img)
    
    # Desenha polígonos (preenche com 0)
    for polygon in canvas.polygons:
        # Converte coordenadas para pixels
        # Invertemos o eixo Y porque em imagens o (0,0) é no topo-esquerdo
        transformed_pixels = [(x * resolution, height_px - (y * resolution)) for x, y in polygon.points]
        draw.polygon(transformed_pixels, outline=0, fill=0)
        
    # Desenha círculos (preenche com 0)
    for circle in canvas.circles:
        cx, cy = circle.center
        r = circle.radius
        
        # Bounding box do círculo em pixels
        # Invertendo Y: centro (cx, cy) -> (cx, H - cy)
        # Topo do círculo (Y mat = cy + r) -> Y img = H - (cy + r) = H - cy - r
        # Base do círculo (Y mat = cy - r) -> Y img = H - (cy - r) = H - cy + r
        
        x0 = (cx - r) * resolution
        y0 = height_px - (cy + r) * resolution
        x1 = (cx + r) * resolution
        y1 = height_px - (cy - r) * resolution
        
        draw.ellipse([x0, y0, x1, y1], outline=0, fill=0)
        
    # Converte para array numpy
    grid = np.array(img)
    
    # Calcula a Transformada de Distância (Chessboard = L_infinity)
    # A função calcula a distância até o zero mais próximo.
    dt = distance_transform_cdt(grid, metric='chessboard')
    
    # Ajusta a distância para considerar as bordas do canvas como obstáculos
    # Para cada pixel (y, x), a distância máxima possível sem sair do canvas
    # é limitada pela distância até a borda mais próxima.
    # Borda esquerda: x
    # Borda direita: width_px - 1 - x
    # Borda superior: y
    # Borda inferior: height_px - 1 - y
    
    # Cria arrays de coordenadas
    rows, cols = np.indices(dt.shape)
    
    # Distância para as bordas verticais (min entre x e W-1-x)
    dist_x = np.minimum(cols, width_px - 1 - cols)
    # Distância para as bordas horizontais (min entre y e H-1-y)
    dist_y = np.minimum(rows, height_px - 1 - rows)
    
    # Distância para a borda mais próxima (L_infinity)
    dist_border = np.minimum(dist_x, dist_y)
    
    # A distância válida é o mínimo entre a distância aos obstáculos internos e a distância às bordas
    # Adicionamos +1 ao dist_border para alinhar com a lógica do CDT onde 1 significa "livre" (distância 1 do obstáculo)
    dt_final = np.minimum(dt, dist_border + 1)
    
    # Encontra o valor máximo e sua posição
    max_dist_px = np.max(dt_final)
    argmax = np.argmax(dt_final)
    # argmax retorna o índice no array achatado, precisamos converter para (row, col)
    # row = y, col = x
    y_px, x_px = np.unravel_index(argmax, dt.shape)
    
    # Converte de volta para unidades do canvas
    # Consideramos que o valor dt representa o "raio" em pixels, mas como estamos em uma grade discreta,
    # dt=1 significa raio 0.5 (apenas o pixel). dt=k significa raio k-0.5.
    radius = (max_dist_px - 0.5) / resolution
    
    # Centro em unidades
    # Adicionamos 0.5 para centralizar no pixel
    center_x = (x_px + 0.5) / resolution
    # Reverte a inversão do Y
    # y_px = height_px - (y_canvas * resolution) -> y_canvas = (height_px - y_px) / res
    # Ajustando para o centro do pixel:
    center_y = (height_px - (y_px + 0.5)) / resolution
    
    return center_x, center_y, radius