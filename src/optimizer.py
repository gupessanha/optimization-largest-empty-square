import numpy as np
from scipy.optimize import differential_evolution
from shapely.geometry import Polygon as ShapelyPolygon, Point
from shapely import affinity
from typing import List, Tuple, Any, Dict, Union

from solver import find_largest_rectangle
from greedy import GreedyPacker

def check_collision(shapes: List[Union[ShapelyPolygon, Point]], canvas_dims: Tuple[float, float]) -> bool:
    """
    Verifica se há colisão entre as formas ou com as bordas.

    Args:
        shapes (List[Union[ShapelyPolygon, Point]]): Lista de objetos geométricos Shapely.
        canvas_dims (Tuple[float, float]): Dimensões do canvas (largura, altura).

    Returns:
        bool: True se houver colisão, False caso contrário.
    """
    W, H = canvas_dims
    
    # Verifica limites do canvas e colisões entre pares
    for i, shape1 in enumerate(shapes):
        # Limites
        minx, miny, maxx, maxy = shape1.bounds
        if minx < 0 or miny < 0 or maxx > W or maxy > H:
            return True
            
        # Colisão entre formas
        for j, shape2 in enumerate(shapes):
            if i < j:
                if shape1.intersects(shape2):
                    return True
    return False

def objective_function(position_vector: np.ndarray, shape_templates: List[Any], canvas_dims: Tuple[float, float], resolution: int) -> float:
    """
    Função de custo para o otimizador Differential Evolution.

    Calcula a área do maior retângulo vazio dado um vetor de posições.
    Retorna o negativo da área para minimização.

    Args:
        position_vector (np.ndarray): Vetor plano contendo [x1, y1, x2, y2, ...] para todas as formas.
        shape_templates (List[Any]): Lista de templates das formas (pontos relativos ou raio).
        canvas_dims (Tuple[float, float]): Dimensões do canvas.
        resolution (int): Resolução da rasterização para cálculo da área.

    Returns:
        float: O negativo da área do maior retângulo vazio (ou penalidade alta se houver colisão).
    """
    # Reconstrói as formas nas novas posições
    current_shapes = []
    num_shapes = len(shape_templates)
    
    for i in range(num_shapes):
        x, y = position_vector[2*i], position_vector[2*i+1]
        template = shape_templates[i]
        
        if isinstance(template, tuple) and len(template) == 2: # Circle (radius, original_center_ignored)
            radius = template[0]
            shape = Point(x, y).buffer(radius)
        else: # Polygon points (relative to centroid 0,0)
            # template é uma lista de pontos centralizados em (0,0)
            # Transladar para (x,y)
            new_points = [(px + x, py + y) for px, py in template]
            shape = ShapelyPolygon(new_points)
            
        current_shapes.append(shape)
        
    # Verifica colisão (Hard Constraint)
    if check_collision(current_shapes, canvas_dims):
        return 1e9 # Penalidade alta
        
    # Se válido, calcula o maior retângulo
    # Precisamos criar um objeto 'MockCanvas' para passar para o solver
    class MockCanvas:
        def __init__(self, w, h):
            self.x_dimension = w
            self.y_dimension = h
            self.polygons = []
            self.circles = []
            
    mock_canvas = MockCanvas(canvas_dims[0], canvas_dims[1])
    
    for i, shape in enumerate(current_shapes):
        template = shape_templates[i]
        if isinstance(template, tuple): # Circle
            # shape é um Polygon (buffer result), mas precisamos passar Circle para o solver
            # O solver espera objetos com .center e .radius
            class MockCircle:
                def __init__(self, c, r): self.center = c; self.radius = r
            
            radius = template[0]
            # x, y já extraídos acima
            x, y = position_vector[2*i], position_vector[2*i+1]
            mock_canvas.circles.append(MockCircle((x, y), radius))
        else:
            # Polygon
            # O solver espera objetos com .points
            class MockPolygon:
                def __init__(self, p): self.points = p
            
            # Extrai pontos do shapely polygon
            points = list(shape.exterior.coords)
            mock_canvas.polygons.append(MockPolygon(points))
            
    # Chama o solver
    cx, cy, w, h = find_largest_rectangle(mock_canvas, resolution=resolution)
    area = w * h
    
    return -area # Maximizar área = Minimizar negativa

def optimize_layout(canvas: Any, max_iter: int = 10, resolution: int = 5, use_greedy: bool = True) -> int:
    """
    Otimiza a posição das formas no canvas utilizando Differential Evolution.

    Args:
        canvas (Canvas): O objeto Canvas contendo as formas a serem otimizadas.
        max_iter (int, optional): Número máximo de iterações do otimizador. Padrão é 10.
        resolution (int, optional): Resolução da rasterização usada na função objetivo. Padrão é 5.
        use_greedy (bool, optional): Se True, utiliza o algoritmo GreedyPacker para gerar uma solução inicial. Padrão é True.

    Returns:
        int: Número de iterações realizadas.
    """
    # Backup dos objetos originais para restaurar propriedades (cor)
    original_polygons = list(canvas.polygons)
    original_circles = list(canvas.circles)
    
    # --- FASE 1: Inicialização Gulosa (Opcional) ---
    initial_positions_greedy = []
    
    if use_greedy:
        print("Executando GreedyPacker para solução inicial...")
        packer = GreedyPacker(canvas.x_dimension, canvas.y_dimension, step=1.0)
        
        # Combina listas para o packer
        shapes_to_pack = original_polygons + original_circles
        packed_items = packer.pack(shapes_to_pack)
        
        # Atualiza polígonos no canvas se houver rotação
        # O packer retorna itens na ordem original
        num_polys = len(original_polygons)
        
        for i, item in enumerate(packed_items):
            # item['pos'] é (x, y)
            x, y = item['pos']
            initial_positions_greedy.extend([x, y])
            
            if i < num_polys:
                # É um polígono. Verifica rotação.
                angle = item['rotation']
                if angle != 0:
                    # Atualiza o polígono original no canvas para refletir a rotação
                    # Precisamos atualizar canvas.polygons[i]
                    # O template será extraído deste polígono atualizado
                    
                    # item['final_geom'] é o objeto posicionado em (x,y)
                    # Trazemos de volta para (0,0) para extrair os pontos relativos corretos depois
                    final_geom = item['final_geom']
                    centered_geom = affinity.translate(final_geom, xoff=-x, yoff=-y)
                    
                    new_points = list(centered_geom.exterior.coords)
                    canvas.polygons[i].points = new_points
                    print(f"Polígono {i} rotacionado em {angle} graus.")

    # --- FASE 2: Preparação para DE ---
    
    # 1. Extrair templates das formas (centralizados em 0,0)
    # Importante: Se o Greedy rodou, os polígonos em canvas.polygons já podem estar rotacionados.
    shape_templates = []
    bounds = []
    
    # Polígonos
    for poly in canvas.polygons:
        # Calcula centroide
        pts = np.array(poly.points)
        centroid = np.mean(pts, axis=0)
        # Pontos relativos
        relative_pts = pts - centroid
        shape_templates.append(relative_pts.tolist())
        
        # Bounds para o centroide (0 a W, 0 a H)
        bounds.append((0, canvas.x_dimension))
        bounds.append((0, canvas.y_dimension))
        
    # Círculos
    for circle in canvas.circles:
        # Template é (raio, tipo)
        shape_templates.append((circle.radius, 'circle'))
        bounds.append((circle.radius, canvas.x_dimension - circle.radius))
        bounds.append((circle.radius, canvas.y_dimension - circle.radius))
        
    # Configuração da População Inicial
    init_pop = 'latinhypercube' # Padrão
    pop_size = 30
    
    if use_greedy and initial_positions_greedy:
        # Cria população inicial com a solução gulosa
        num_params = len(initial_positions_greedy)
        init_pop_array = np.zeros((pop_size, num_params))
        
        # Primeiro indivíduo é a solução gulosa
        init_pop_array[0] = initial_positions_greedy
        
        # Os demais são aleatórios dentro dos bounds
        # bounds é lista de tuplas [(min, max), ...]
        for j in range(1, pop_size):
            for k in range(num_params):
                low, high = bounds[k]
                init_pop_array[j, k] = np.random.uniform(low, high)
                
        init_pop = init_pop_array
        print("População inicial semeada com solução GreedyPacker.")

    # 2. Rodar Evolução Diferencial
    print(f"Iniciando otimização de layout (Resolução={resolution})...")
    
    result = differential_evolution(
        objective_function,
        bounds,
        args=(shape_templates, (canvas.x_dimension, canvas.y_dimension), resolution),
        maxiter=max_iter,
        popsize=pop_size,
        mutation=(0.5, 1),
        recombination=0.7,
        disp=True,
        workers=1,
        init=init_pop
    )
    
    print(f"Otimização concluída. Melhor área livre encontrada: {-result.fun:.2f}")
    
    # 3. Aplicar novas posições ao Canvas
    best_pos = result.x
    
    # Limpa listas atuais do canvas
    canvas.polygons = []
    canvas.circles = []
    canvas.geometry_objects = [] 
    
    current_idx = 0
    
    # Reconstruir Polígonos
    from main import Polygon, Circle # Importação local para evitar ciclo se main importar optimizer
    
    for i, original_poly in enumerate(original_polygons):
        x, y = best_pos[2*current_idx], best_pos[2*current_idx+1]
        template = shape_templates[current_idx]
        
        # Reconstrói pontos absolutos
        new_points = [(px + x, py + y) for px, py in template]
        
        # Cria novo objeto preservando cor
        # Nota: original_poly.color é preservado, mas se houve rotação, original_poly.points estava desatualizado?
        # Não, original_polygons foi copiado no início.
        # Mas shape_templates reflete a rotação aplicada no canvas.polygons.
        # Então new_points será a forma rotacionada na posição otimizada.
        new_poly = Polygon(new_points, color=original_poly.color)
        canvas.add_polygon(new_poly)
        
        current_idx += 1
        
    # Reconstruir Círculos
    for i, original_circle in enumerate(original_circles):
        x, y = best_pos[2*current_idx], best_pos[2*current_idx+1]
        # template é (radius, 'circle')
        
        new_circle = Circle((x, y), original_circle.radius, color=original_circle.color)
        canvas.add_circle(new_circle)
        
        current_idx += 1
        
    return result.nit
