import matplotlib.pyplot as plt
import numpy as np
import random
import time
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
   


if __name__ == "__main__":
 
    canvas = Canvas(30, 30)
    
    # Adiciona primeiro objeto (sucesso)
    triangle = Polygon(points=[(4, 6), (1, 2), (7, 2)], color='red')
    canvas.add_polygon(triangle)
    
    # Adiciona segundo objeto (sucesso)
    # circle = Circle(center=(25, 5), radius=5, color='blue')
    # canvas.add_circle(circle)
    
    square = Polygon(points=[(20, 20), (25, 20), (25, 25), (20, 25)], color='green')
    canvas.add_polygon(square)
    
    triangle2 = Polygon(points=[(10, 25), (15, 28), (12, 22)], color='purple')
    canvas.add_polygon(triangle2)
    
    square2 = Polygon(points=[(5, 15), (10, 15), (10, 20), (5, 20)], color='brown')
    
    triangle3 = Polygon(points=[(15, 5), (18, 10), (12, 10)], color='cyan')
    canvas.add_polygon(triangle3)
    
    square3 = Polygon(points=[(22, 12), (27, 12), (27, 17), (22, 17)], color='magenta')
    
    # Adiciona um objeto que colide com o triângulo (falha)
    # coliding_circle = Circle(center=(5, 5), radius=5, color='yellow')
    # canvas.add_circle(coliding_circle)

    # --- SELEÇÃO DE MÉTODO ---
    print("Escolha o método de otimização:")
    print("1. Analítico (MIP - Exato)")
    print("2. Metaheurística (Differential Evolution - Aproximado)")
    choice = input("Digite 1 ou 2: ").strip()
    
    use_analytical = (choice == '1')
    
    # --- GERAÇÃO DE ID ---
    timestamp_id = int(time.time())
    prefix = 'A' if use_analytical else 'M'
    execution_id = f"{prefix}_{timestamp_id}"
    print(f"ID da Execução: {execution_id}")

    print("Calculando maior retângulo na configuração inicial...")
    # Salva o estado inicial
    canvas.plot_workcanvas(filename=f'{execution_id}_initial.png')
    
    resolution = 30
    cx, cy, w, h = find_largest_rectangle(canvas, resolution=resolution)
    initial_area = w * h
    print(f"Inicial: Área={initial_area:.2f}")

    # Otimiza o layout
    max_iter = 1000
    # Requisito 3: Resolução reduzida durante otimização (ex: 5)
    # Requisito 4: Usar GreedyPacker
    start_time = time.time()
    
    if use_analytical:
        # --- SOLUÇÃO ANALÍTICA ---
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
        
    else:
        # --- METAHEURÍSTICA ---
        print("Iniciando Metaheurística (Differential Evolution)...")
        actual_iterations = optimize_layout(canvas, max_iter=max_iter, resolution=5, use_greedy=True) 
        
        # Recalcula área final para registro
        cx_opt, cy_opt, w_opt, h_opt = find_largest_rectangle(canvas, resolution=resolution)
        optimized_area = w_opt * h_opt
        print(f"Final (Metaheurística): Área={optimized_area:.2f}")

    end_time = time.time()
    execution_time = end_time - start_time
    print(f"Tempo de execução: {execution_time:.2f}s")

    # Salva o estado otimizado
    canvas.plot_workcanvas(filename=f'{execution_id}_optimized.png')
    
    # Registra a execução
    count_poly = len(canvas.polygons)
    count_circle = len(canvas.circles)
    register_execution('execution_log.csv', canvas.x_dimension, canvas.y_dimension, count_poly, count_circle, initial_area, optimized_area, actual_iterations, resolution, execution_time, execution_id)
