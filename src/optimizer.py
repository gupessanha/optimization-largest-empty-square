import numpy as np
import copy
from scipy.optimize import differential_evolution
from shapely.geometry import Polygon as ShapelyPolygon, Point, box
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
        
    # --- Soft Constraints (Penalidade Gradual) ---
    total_overlap_area = 0.0
    
    # Calcular sobreposição entre todas as formas (O(N^2))
    for i in range(num_shapes):
        for j in range(i + 1, num_shapes):
            if current_shapes[i].intersects(current_shapes[j]):
                total_overlap_area += current_shapes[i].intersection(current_shapes[j]).area
    
    # Calcular área fora do canvas
    W, H = canvas_dims
    canvas_box = box(0, 0, W, H)
    total_out_area = 0.0
    for shape in current_shapes:
        if not canvas_box.contains(shape):
            total_out_area += shape.difference(canvas_box).area

    # Se houver erro, o custo é dominado pelo erro
    if total_overlap_area > 0 or total_out_area > 0:
        # Penalidade base + proporcional ao erro
        return 1000 + (total_overlap_area * 10) + (total_out_area * 10)
        
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
    # Backup dos objetos originais para restaurar propriedades (cor) e recuperação de falhas
    original_polygons_backup = copy.deepcopy(canvas.polygons)
    original_circles_backup = copy.deepcopy(canvas.circles)
    
    # Referências para o loop de otimização (podem ser modificadas pelo Greedy)
    original_polygons = list(canvas.polygons)
    original_circles = list(canvas.circles)
    
    # --- FASE 1: Inicialização Gulosa (4 Cantos) ---
    initial_positions_greedy = []
    
    if use_greedy:
        print("Executando GreedyPacker (Heurística 4 Cantos)...")
        corners = ['BL', 'BR', 'TL', 'TR']
        
        # Sempre usar o backup para garantir formas originais sem rotação acumulada
        shapes_to_pack = original_polygons_backup + original_circles_backup
        
        best_greedy_score = float('inf')
        best_greedy_config = None

        for corner in corners:
            # Instancia novo packer para cada tentativa (limpa placed_geometries)
            packer = GreedyPacker(canvas.x_dimension, canvas.y_dimension, step=1.0)
            
            # Executa packing para o canto específico
            packed_items = packer.pack(shapes_to_pack, corner=corner)
            
            # Construir vetor de posições e templates temporários para avaliação
            current_pos_vector = []
            current_templates = []
            current_poly_points = [] 
            
            # Processar itens (packed_items está ordenado por índice original)
            
            # Polígonos
            for i in range(len(original_polygons_backup)):
                item = packed_items[i]
                x, y = item['pos']
                current_pos_vector.extend([x, y])
                
                # Calcular template rotacionado para avaliação
                final_geom = item['final_geom']
                # Template relativo ao ponto de inserção (x,y)
                # Nota: O DE usa centroide, mas aqui estamos definindo o estado inicial.
                # Se passarmos esses pontos para o objective_function, ele vai reconstruir:
                # new_points = [(px + x, py + y) for px, py in template]
                # Então template deve ser points - (x,y)
                relative_geom = affinity.translate(final_geom, xoff=-x, yoff=-y)
                template_points = list(relative_geom.exterior.coords)
                current_templates.append(template_points)
                
                # Salvar pontos absolutos
                current_poly_points.append(list(final_geom.exterior.coords))

            # Círculos
            offset = len(original_polygons_backup)
            for i in range(len(original_circles_backup)):
                item = packed_items[offset + i]
                x, y = item['pos']
                current_pos_vector.extend([x, y])
                current_templates.append((original_circles_backup[i].radius, 'circle'))
            
            # Avaliar configuração
            score = objective_function(np.array(current_pos_vector), current_templates, (canvas.x_dimension, canvas.y_dimension), resolution)
            print(f"  Canto {corner}: Score = {score:.2f}")
            
            if score < best_greedy_score:
                best_greedy_score = score
                best_greedy_config = {
                    'pos_vector': current_pos_vector,
                    'poly_points': current_poly_points,
                    'corner': corner
                }

        print(f"Melhor estratégia: {best_greedy_config['corner']} (Score: {best_greedy_score:.2f})")
        
        # Aplicar a melhor configuração
        initial_positions_greedy = best_greedy_config['pos_vector']
        
        # Atualizar polígonos no canvas com as rotações vencedoras
        for i, points in enumerate(best_greedy_config['poly_points']):
            canvas.polygons[i].points = points
            # print(f"Polígono {i} atualizado para configuração do canto {best_greedy_config['corner']}.")

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
        new_poly = Polygon(new_points, color=original_poly.color)
        
        try:
            canvas.add_polygon(new_poly)
        except ValueError as e:
            print(f"Erro ao adicionar polígono {i} otimizado: {e}")
            
            # Tentativa de Recuperação 1: Ajuste de Limites (Clamping)
            if "fora dos limites" in str(e):
                print(f"Tentando ajustar posição do polígono {i} para dentro do canvas...")
                # Calcula bounds atuais
                xs = [p[0] for p in new_poly.points]
                ys = [p[1] for p in new_poly.points]
                min_x, max_x = min(xs), max(xs)
                min_y, max_y = min(ys), max(ys)
                
                dx = 0
                dy = 0
                
                if min_x < 0: dx = -min_x
                elif max_x > canvas.x_dimension: dx = canvas.x_dimension - max_x
                
                if min_y < 0: dy = -min_y
                elif max_y > canvas.y_dimension: dy = canvas.y_dimension - max_y
                
                if dx != 0 or dy != 0:
                    adjusted_points = [(p[0] + dx, p[1] + dy) for p in new_poly.points]
                    adjusted_poly = Polygon(adjusted_points, color=original_poly.color)
                    try:
                        canvas.add_polygon(adjusted_poly)
                        print(f"Polígono {i} ajustado com sucesso.")
                        current_idx += 1
                        continue
                    except ValueError as e2:
                        print(f"Falha no ajuste: {e2}")

            # Tentativa de Recuperação 2: Restaurar Original (se possível)
            print(f"Tentando restaurar polígono {i} original...")
            try:
                # Usa o backup profundo para garantir estado original
                canvas.add_polygon(original_polygons_backup[i])
                print(f"Polígono {i} restaurado para posição original.")
            except ValueError as e3:
                print(f"Não foi possível restaurar o polígono {i}: {e3}. O polígono será ignorado.")
        
        current_idx += 1
        
    # Reconstruir Círculos
    for i, original_circle in enumerate(original_circles):
        x, y = best_pos[2*current_idx], best_pos[2*current_idx+1]
        # template é (radius, 'circle')
        
        new_circle = Circle((x, y), original_circle.radius, color=original_circle.color)
        
        try:
            canvas.add_circle(new_circle)
        except ValueError as e:
            print(f"Erro ao adicionar círculo {i} otimizado: {e}")
            
            # Tentativa de Recuperação 1: Ajuste de Limites (Clamping)
            if "fora dos limites" in str(e) or "excede os limites" in str(e):
                print(f"Tentando ajustar posição do círculo {i} para dentro do canvas...")
                cx, cy = new_circle.center
                r = new_circle.radius
                
                # Clamp center
                new_cx = max(r, min(canvas.x_dimension - r, cx))
                new_cy = max(r, min(canvas.y_dimension - r, cy))
                
                adjusted_circle = Circle((new_cx, new_cy), r, color=original_circle.color)
                try:
                    canvas.add_circle(adjusted_circle)
                    print(f"Círculo {i} ajustado com sucesso.")
                    current_idx += 1
                    continue
                except ValueError as e2:
                    print(f"Falha no ajuste: {e2}")

            # Tentativa de Recuperação 2: Restaurar Original
            print(f"Tentando restaurar círculo {i} original...")
            try:
                canvas.add_circle(original_circles_backup[i])
                print(f"Círculo {i} restaurado para posição original.")
            except ValueError as e3:
                print(f"Não foi possível restaurar o círculo {i}: {e3}. O círculo será ignorado.")

        current_idx += 1
        
    return result.nit
