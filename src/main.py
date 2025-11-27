import matplotlib.pyplot as plt
import numpy as np
from shapely.geometry import Polygon as ShapelyPolygon, Point
from solver import find_largest_rectangle

class Polygon:
    def __init__(self, points, color='green'):
        self.points = points 
        self.color = color
        self.lines = []
        
class Circle:
    def __init__(self, center, radius, color='green'):
        self.center = center
        self.radius = radius
        self.color = color

class Canvas:
    def __init__(self, x_dimension, y_dimension):
        self.x_dimension = x_dimension
        self.y_dimension = y_dimension
        self.polygons = []
        self.circles = []
        self.geometry_objects = []
        
    def add_polygon(self, polygon):
        
        if len(polygon.points) < 3:
            raise ValueError("Um polígono deve ter pelo menos 3 pontos.")
        
        if any(not (0 <= x <= self.x_dimension and 0 <= y <= self.y_dimension) for x, y in polygon.points):
            raise ValueError("Pontos do polígono fora dos limites do canvas.")
        
        new_shape = ShapelyPolygon(polygon.points)
        
        for shape in self.geometry_objects:
            if new_shape.intersects(shape):
                raise ValueError("Colisão detectada! Polígono não adicionado.")
        
        self .geometry_objects.append(new_shape)
        self.polygons.append(polygon)
        return True
    
    
    def add_circle(self, circle):
        
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
    
    def plot_workcanvas(self):
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

        plt.savefig('canvas.png')
   


if __name__ == "__main__":
 
    canvas = Canvas(30, 30)
    
    # Adiciona primeiro objeto (sucesso)
    triangle = Polygon(points=[(10, 15), (1, 2), (7, 2)], color='red')
    canvas.add_polygon(triangle)
    
    # Adiciona segundo objeto (sucesso)
    circle = Circle(center=(25, 5), radius=5, color='blue')
    canvas.add_circle(circle)
    
    square = Polygon(points=[(20, 20), (25, 20), (25, 25), (20, 25)], color='green')
    canvas.add_polygon(square)
    
    # Adiciona um objeto que colide com o triângulo (falha)
    # coliding_circle = Circle(center=(5, 5), radius=5, color='yellow')
    # canvas.add_circle(coliding_circle)

    canvas.plot_workcanvas()