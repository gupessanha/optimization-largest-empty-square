import matplotlib.pyplot as plt
import numpy as np
import random
import time
import math
import copy
from shapely.geometry import Polygon as ShapelyPolygon, Point
from typing import List, Tuple, Any, Optional

from solver import find_largest_rectangle
from optimizer import optimize_layout
from register import register_execution
from analytical_solver import AnalyticalSolver

class Polygon:
    """
    Representa um polígono no canvas.
    """
    def __init__(self, points: List[Tuple[float, float]], color: str = 'green'):
        """
        Inicializa um polígono.

        Args:
            points (List[Tuple[float, float]]): Lista de coordenadas (x, y) dos vértices.
            color (str, optional): Cor do polígono para plotagem. Padrão é 'green'.
        """
        self.points = points 
        self.color = color
        self.lines = []
        
class Circle:
    """
    Representa um círculo no canvas.
    """
    def __init__(self, center: Tuple[float, float], radius: float, color: str = 'green'):
        """
        Inicializa um círculo.

        Args:
            center (Tuple[float, float]): Coordenadas (x, y) do centro.
            radius (float): Raio do círculo.
            color (str, optional): Cor do círculo para plotagem. Padrão é 'green'.
        """
        self.center = center
        self.radius = radius
        self.color = color

class Canvas:
    """
    Representa a área de trabalho onde as formas são posicionadas.
    """
    def __init__(self, x_dimension: float, y_dimension: float):
        """
        Inicializa o canvas.

        Args:
            x_dimension (float): Largura do canvas.
            y_dimension (float): Altura do canvas.
        """
        self.x_dimension = x_dimension
        self.y_dimension = y_dimension
        self.polygons: List[Polygon] = []
        self.circles: List[Circle] = []
        self.geometry_objects: List[Any] = [] # Objetos Shapely
        
    def add_polygon(self, polygon: Polygon) -> bool:
        """
        Adiciona um polígono ao canvas se não houver colisão.

        Args:
            polygon (Polygon): O polígono a ser adicionado.

        Returns:
            bool: True se adicionado com sucesso.

        Raises:
            ValueError: Se o polígono for inválido ou colidir.
        """
        if len(polygon.points) < 3:
            raise ValueError("Um polígono deve ter pelo menos 3 pontos.")
        
        if any(not (0 <= x <= self.x_dimension and 0 <= y <= self.y_dimension) for x, y in polygon.points):
            raise ValueError("Pontos do polígono fora dos limites do canvas.")
        
        new_shape = ShapelyPolygon(polygon.points)
        
        for shape in self.geometry_objects:
            if new_shape.intersects(shape):
                raise ValueError("Colisão detectada! Polígono não adicionado.")
        
        self.geometry_objects.append(new_shape)
        self.polygons.append(polygon)
        return True
    
    
    def add_circle(self, circle: Circle) -> bool:
        """
        Adiciona um círculo ao canvas se não houver colisão.

        Args:
            circle (Circle): O círculo a ser adicionado.

        Returns:
            bool: True se adicionado com sucesso.

        Raises:
            ValueError: Se o círculo for inválido ou colidir.
        """
        if not (0 <= circle.center[0] <= self.x_dimension and 0 <= circle.center[1] <= self.y_dimension):
            raise ValueError("Centro do círculo fora dos limites do canvas.")
        
        if circle.radius <= 0:
            raise ValueError("O raio do círculo deve ser positivo.")
        
        if not (0 <= circle.center[0] - circle.radius and circle.center[0] + circle.radius <= self.x_dimension and
            0 <= circle.center[1] - circle.radius and circle.center[1] + circle.radius <= self.y_dimension):
            raise ValueError("O círculo excede os limites do canvas.")
        
        new_shape = Point(circle.center).buffer(circle.radius)
        
        for shape in self.geometry_objects:
            if new_shape.intersects(shape):
                raise ValueError("Colisão detectada! Círculo não adicionado.")
        
        self.geometry_objects.append(new_shape)
        self.circles.append(circle)
        return True
    
    def plot_workcanvas(self, filename: str = 'canvas.png') -> None:
        """
        Gera e salva uma imagem do canvas com as formas e o maior retângulo vazio.

        Args:
            filename (str, optional): Caminho do arquivo de saída. Padrão é 'canvas.png'.
        """
        fig, ax = plt.subplots(figsize=(self.x_dimension * 0.5, self.y_dimension * 0.5))
        ax.set_xlim(0, self.x_dimension)
        ax.set_ylim(0, self.y_dimension)
        ax.set_aspect('equal')
        ax.grid(True, which='both', linestyle='--', linewidth=0.5)
        ax.set_xticks(np.arange(0, self.x_dimension + 1, 1))
        ax.set_yticks(np.arange(0, self.y_dimension + 1, 1))
        ax.set_xlabel('X Axis')
        ax.set_ylabel('Y Axis')
        ax.set_title(f'Workspace {self.x_dimension}x{self.y_dimension}')

        for polygon in self.polygons:
            poly_patch = plt.Polygon(polygon.points, closed=True, fill=None, edgecolor=polygon.color)
            ax.add_patch(poly_patch)
            
        for circle in self.circles:
            circle_patch = plt.Circle(circle.center, circle.radius, fill=None, edgecolor=circle.color)
            ax.add_patch(circle_patch)

        # Encontra e desenha o maior retângulo vazio
        cx, cy, w, h = find_largest_rectangle(self, resolution=20)
        print(f"Maior retângulo encontrado: Centro=({cx:.2f}, {cy:.2f}), Largura={w:.2f}, Altura={h:.2f}, Área={w*h:.2f}")
        
        # Desenha o retângulo (Rectangle recebe canto inferior esquerdo, largura, altura)
        rect_patch = plt.Rectangle((cx - w/2, cy - h/2), w, h, 
                                     fill=True, color='orange', alpha=0.5, label='Maior Retângulo Vazio')
        ax.add_patch(rect_patch)
        ax.plot(cx, cy, 'x', color='black') # Marca o centro
        ax.legend()
        
        plt.savefig(filename)
        plt.close(fig) # Fecha a figura para liberar memória
   
def generate_random_shapes(canvas: Canvas, num_shapes: int, max_sides: int):
    """
    Gera formas aleatórias e as adiciona ao canvas.
    
    Args:
        canvas (Canvas): O canvas alvo.
        num_shapes (int): Quantidade de formas a gerar.
        max_sides (int): Número máximo de lados (0 para círculos).
    """
    colors = ['red', 'blue', 'green', 'purple', 'brown', 'cyan', 'magenta', 'orange', 'yellow', 'gray']
    
    count = 0
    attempts = 0
    max_attempts = num_shapes * 100 # Evita loop infinito
    
    while count < num_shapes and attempts < max_attempts:
        attempts += 1
        
        # Escolhe número de lados: 0 (círculo) ou 3 a max_sides
        if max_sides < 3:
            sides = 0
        else:
            # Lista de opções: 0 e 3..max_sides
            options = [0] + list(range(3, max_sides + 1))
            sides = random.choice(options)
            
        color = random.choice(colors)
        
        try:
            if sides == 0:
                # Círculo
                # Raio aleatório (limite superior arbitrário para não encher demais, ex: 15% da menor dimensão)
                max_radius = min(canvas.x_dimension, canvas.y_dimension) * 0.15
                radius = random.uniform(1, max_radius)
                
                # Centro (garantindo que cabe no canvas)
                # x entre radius e W-radius
                if canvas.x_dimension <= 2 * radius or canvas.y_dimension <= 2 * radius:
                    continue
                    
                cx = random.uniform(radius, canvas.x_dimension - radius)
                cy = random.uniform(radius, canvas.y_dimension - radius)
                
                circle = Circle(center=(cx, cy), radius=radius, color=color)
                canvas.add_circle(circle)
                
            else:
                # Polígono
                # Gera polígono convexo aleatório
                # Raio aproximado do polígono
                max_poly_radius = min(canvas.x_dimension, canvas.y_dimension) * 0.15
                poly_radius = random.uniform(2, max_poly_radius)
                
                # Centro
                if canvas.x_dimension <= 2 * poly_radius or canvas.y_dimension <= 2 * poly_radius:
                    continue

                cx = random.uniform(poly_radius, canvas.x_dimension - poly_radius)
                cy = random.uniform(poly_radius, canvas.y_dimension - poly_radius)
                
                # Gera ângulos aleatórios
                angles = sorted([random.uniform(0, 2 * math.pi) for _ in range(sides)])
                
                points = []
                for angle in angles:
                    x = cx + poly_radius * math.cos(angle)
                    y = cy + poly_radius * math.sin(angle)
                    points.append((x, y))
                
                polygon = Polygon(points=points, color=color)
                canvas.add_polygon(polygon)
                
            count += 1
            
        except ValueError:
            # Colisão ou inválido, tenta novamente
            pass
            
    print(f"Geradas {count} formas em {attempts} tentativas.")

if __name__ == "__main__":
 
    canvas = Canvas(100, 100)
    
    # Gera formas aleatórias para teste
    generate_random_shapes(canvas, num_shapes=5, max_sides=8)
    
    # --- SELEÇÃO DE MÉTODO ---
    print("Escolha o método de otimização:")
    print("1. Analítico (MIP - Exato)")
    print("2. Metaheurística (Differential Evolution - Aproximado)")
    print("3. Ambos (Comparação)")
    choice = input("Digite 1, 2 ou 3: ").strip()
    
    run_analytical = (choice == '1' or choice == '3')
    run_metaheuristic = (choice == '2' or choice == '3')
    
    # Salva estado inicial para restauração se necessário
    initial_polygons_state = copy.deepcopy(canvas.polygons)
    initial_circles_state = copy.deepcopy(canvas.circles)
    
    # --- GERAÇÃO DE ID ---
    timestamp_id = int(time.time())
    
    if run_analytical:
        prefix = 'A'
        execution_id = f"{prefix}_{timestamp_id}"
        print(f"ID da Execução Analítica: {execution_id}")

        print("Calculando maior retângulo na configuração inicial...")
        # Salva o estado inicial
        canvas.plot_workcanvas(filename=f'{execution_id}_initial.png')
        
        resolution = 30
        cx, cy, w, h = find_largest_rectangle(canvas, resolution=resolution)
        initial_area = w * h
        print(f"Inicial: Área={initial_area:.2f}")

        # --- SOLUÇÃO ANALÍTICA ---
        start_time = time.time()
        print("Iniciando Solução Analítica (MIP)...")
        analytical_solver = AnalyticalSolver(canvas.x_dimension, canvas.y_dimension)
        
        # Adiciona formas ao solver analítico
        for poly in canvas.polygons:
            analytical_solver.add_shape(poly)
        for circle in canvas.circles:
            analytical_solver.add_shape(circle)
            
        w_opt, h_opt, xs_opt, ys_opt, positions = analytical_solver.solve(time_limit=60)
        
        # Atualiza posições no canvas
        if positions:
            # Atualiza polígonos
            for i, poly in enumerate(canvas.polygons):
                new_x, new_y = positions[i]
                # Move o polígono para a nova posição (assumindo que positions[i] é o canto inferior esquerdo do bbox)
                # Precisamos calcular o deslocamento relativo
                # Bounding box original
                xs = [p[0] for p in poly.points]
                ys = [p[1] for p in poly.points]
                min_x, min_y = min(xs), min(ys)
                
                dx = new_x - min_x
                dy = new_y - min_y
                
                new_points = [(p[0] + dx, p[1] + dy) for p in poly.points]
                poly.points = new_points
                
            # Atualiza círculos (se houver, lógica similar)
            # Nota: O solver analítico trata círculos como quadrados (bounding box)
            # A posição retornada é o canto inferior esquerdo do quadrado envolvente
            offset = len(canvas.polygons)
            for i, circle in enumerate(canvas.circles):
                new_x, new_y = positions[offset + i]
                # O centro do círculo é (x + r, y + r)
                circle.center = (new_x + circle.radius, new_y + circle.radius)

        actual_iterations = 0 # MIP não tem "iterações" no mesmo sentido do DE
        
        # Recalcula área final para registro (usando o resultado analítico ou rasterização para confirmação)
        # Vamos usar o resultado analítico w*h se disponível, mas manter a verificação rasterizada
        optimized_area = w_opt * h_opt
        print(f"Final (Analítico): Largura={w_opt:.2f}, Altura={h_opt:.2f}, Área={optimized_area:.2f}")
        
        end_time = time.time()
        execution_time = end_time - start_time
        print(f"Tempo de execução Analítico: {execution_time:.2f}s")

        # Salva o estado otimizado
        canvas.plot_workcanvas(filename=f'{execution_id}_optimized.png')
        
        # Registra a execução
        count_poly = len(canvas.polygons)
        count_circle = len(canvas.circles)
        register_execution('execution_log.csv', canvas.x_dimension, canvas.y_dimension, count_poly, count_circle, initial_area, optimized_area, actual_iterations, resolution, execution_time, execution_id)

    if run_metaheuristic:
        # Restaura estado inicial se o analítico já rodou
        if run_analytical:
            print("Restaurando estado inicial para Metaheurística...")
            canvas.polygons = copy.deepcopy(initial_polygons_state)
            canvas.circles = copy.deepcopy(initial_circles_state)
            # Recria geometry_objects para consistência (embora optimize_layout possa não usar diretamente, é bom manter)
            canvas.geometry_objects = []
            for poly in canvas.polygons:
                canvas.geometry_objects.append(ShapelyPolygon(poly.points))
            for circle in canvas.circles:
                canvas.geometry_objects.append(Point(circle.center).buffer(circle.radius))

        prefix = 'M'
        execution_id = f"{prefix}_{timestamp_id}"
        print(f"ID da Execução Metaheurística: {execution_id}")
        
        if not run_analytical: # Se não rodou analítico, precisa calcular inicial e salvar imagem
            print("Calculando maior retângulo na configuração inicial...")
            canvas.plot_workcanvas(filename=f'{execution_id}_initial.png')
            resolution = 30
            cx, cy, w, h = find_largest_rectangle(canvas, resolution=resolution)
            initial_area = w * h
            print(f"Inicial: Área={initial_area:.2f}")
        
        # --- METAHEURÍSTICA ---
        start_time = time.time()
        print("Iniciando Metaheurística (Differential Evolution)...")
        max_iter = 3000
        
        try:
            actual_iterations = optimize_layout(canvas, max_iter=max_iter, resolution=5, use_greedy=True) 
            
            # Recalcula área final para registro
            cx_opt, cy_opt, w_opt, h_opt = find_largest_rectangle(canvas, resolution=resolution)
            optimized_area = w_opt * h_opt
            print(f"Final (Metaheurística): Área={optimized_area:.2f}")
            
        except Exception as e:
            print(f"Erro durante a execução da Metaheurística: {e}")
            # Em caso de erro, mantemos o estado atual (que pode estar inconsistente ou vazio se falhou no meio)
            # Mas como optimize_layout limpa o canvas antes de reconstruir, pode estar vazio.
            # Vamos tentar restaurar o inicial para garantir que o plot final não quebre ou mostre vazio
            print("Restaurando estado inicial devido a erro...")
            canvas.polygons = copy.deepcopy(initial_polygons_state)
            canvas.circles = copy.deepcopy(initial_circles_state)
            canvas.geometry_objects = []
            for poly in canvas.polygons:
                canvas.geometry_objects.append(ShapelyPolygon(poly.points))
            for circle in canvas.circles:
                canvas.geometry_objects.append(Point(circle.center).buffer(circle.radius))
            
            optimized_area = initial_area # Assume sem melhoria
            actual_iterations = 0

        end_time = time.time()
        execution_time = end_time - start_time
        print(f"Tempo de execução Metaheurística: {execution_time:.2f}s")

        # Salva o estado otimizado
        canvas.plot_workcanvas(filename=f'{execution_id}_optimized.png')
        
        # Registra a execução
        count_poly = len(canvas.polygons)
        count_circle = len(canvas.circles)
        register_execution('execution_log.csv', canvas.x_dimension, canvas.y_dimension, count_poly, count_circle, initial_area, optimized_area, actual_iterations, resolution, execution_time, execution_id)
