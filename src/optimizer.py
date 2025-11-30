import numpy as np
from scipy.optimize import differential_evolution
from shapely.geometry import Polygon as ShapelyPolygon, Point
from shapely import affinity
from solver import find_largest_rectangle

def check_collision(shapes, canvas_dims):
    """
    Verifica se há colisão entre as formas ou com as bordas.
    Retorna True se houver colisão.
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

def objective_function(position_vector, shape_templates, canvas_dims, resolution=5):
    """
    Função de custo para o otimizador.
    position_vector: [x1, y1, x2, y2, ...]
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
            # Adiciona metadados para o solver (que espera objetos Canvas.Circle/Polygon)
            # Mas o solver usa shapely objects? Não, o solver usa Canvas objects.
            # Precisamos adaptar. O solver usa canvas.polygons e canvas.circles.
            # Vamos criar objetos dummy.
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
            
    # Chama o solver (usando resolução menor para ser mais rápido durante otimização)
    # Resolução 5 é um bom compromisso
    cx, cy, w, h = find_largest_rectangle(mock_canvas, resolution=resolution)
    area = w * h
    
    return -area # Maximizar área = Minimizar negativa

def optimize_layout(canvas, max_iter=10):
    """
    Otimiza a posição das formas no canvas.
    """
    # Backup dos objetos originais para restaurar propriedades (cor)
    original_polygons = list(canvas.polygons)
    original_circles = list(canvas.circles)
    
    # 1. Extrair templates das formas (centralizados em 0,0)
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
        
    # 2. Rodar Evolução Diferencial
    print("Iniciando otimização de layout (pode demorar)...")
    # Usamos workers=-1 para paralelizar se possível, mas com rasterização pode dar conflito de memória/GIL?
    # Vamos manter serial por segurança ou workers=1.
    result = differential_evolution(
        objective_function,
        bounds,
        args=(shape_templates, (canvas.x_dimension, canvas.y_dimension)),
        maxiter=max_iter,
        popsize=5, # População pequena para ser rápido no teste
        mutation=(0.5, 1),
        recombination=0.7,
        disp=True,
        workers=1 
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
        canvas.add_polygon(new_poly)
        
        current_idx += 1
        
    # Reconstruir Círculos
    for i, original_circle in enumerate(original_circles):
        x, y = best_pos[2*current_idx], best_pos[2*current_idx+1]
        # template é (radius, 'circle')
        
        new_circle = Circle((x, y), original_circle.radius, color=original_circle.color)
        canvas.add_circle(new_circle)
        
        current_idx += 1
        
    return True
