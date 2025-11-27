import matplotlib.pyplot as plt
import numpy as np
from shapely.geometry import Polygon as ShapelyPolygon, Point

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
        new_shape = ShapelyPolygon(polygon.points)
        
        for shape in self.geometry_objects:
            if new_shape.intersects(shape):
                raise ValueError("Colisão detectada! Polígono não adicionado.")
        
        self .geometry_objects.append(new_shape)
        self.polygons.append(polygon)
        return True
    
    
    def add_circle(self, circle):
        
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

        plt.savefig('canvas.png')
   


if __name__ == "__main__":
 
    canvas = Canvas(50, 50)
    
    # Adiciona primeiro objeto (sucesso)
    triangle = Polygon(points=[(10, 15), (1, 2), (7, 2)], color='red')
    canvas.add_polygon(triangle)
    
    # Adiciona segundo objeto (sucesso)
    circle = Circle(center=(30, 30), radius=5, color='blue')
    canvas.add_circle(circle)
    
    square = Polygon(points=[(20, 20), (25, 20), (25, 25), (20, 25)], color='green')
    canvas.add_polygon(square)
    
    # Adiciona um objeto que colide com o triângulo (falha)
    # coliding_circle = Circle(center=(5, 5), radius=5, color='yellow')
    # canvas.add_circle(coliding_circle)

    canvas.plot_workcanvas()