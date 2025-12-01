import matplotlib.pyplot as plt
import numpy as np
from shapely.geometry import Polygon as ShapelyPolygon, Point
from shapely import affinity # Necessário para rotacionar e transladar
# from solver import find_largest_square # Comentei pois não tenho esse arquivo, mas pode manter

class Polygon:
    def __init__(self, points, color='green'):
        self.points = points 
        self.color = color
        self.shapely_obj = ShapelyPolygon(points) # Criamos o shapely object logo no init

    def update_points(self):
        # Atualiza a lista de pontos baseada no objeto shapely (após rotação/translação)
        if self.shapely_obj.is_empty: return
        self.points = list(self.shapely_obj.exterior.coords)

    def rotate(self, angle):
        # Rotaciona em torno do centróide
        self.shapely_obj = affinity.rotate(self.shapely_obj, angle, origin='centroid')
        self.update_points()

    def move_to(self, x, y):
        # Move o centróide ou bounding box para x,y. 
        # Para simplificar a heurística BL, vamos mover pelo bounding box (minx, miny)
        minx, miny, _, _ = self.shapely_obj.bounds
        dx = x - minx
        dy = y - miny
        self.shapely_obj = affinity.translate(self.shapely_obj, xoff=dx, yoff=dy)
        self.update_points()

class Circle:
    def __init__(self, radius, color='green'):
        # Removi 'center' do init pois a heurística vai decidir onde colocar
        self.radius = radius
        self.color = color
        self.center = (0, 0) # Posição temporária
        self.shapely_obj = Point(0, 0).buffer(radius)

    def move_to(self, x, y):
        # Para círculos, x,y será o centro (ajustado pelo raio para ficar no canto da grade)
        # Se a heurística tenta colocar em 0,0 (bottom-left), o centro real deve ser (r, r)
        target_x = x + self.radius
        target_y = y + self.radius
        self.center = (target_x, target_y)
        self.shapely_obj = Point(target_x, target_y).buffer(self.radius)

class Canvas:
    def __init__(self, x_dimension, y_dimension):
        self.x_dimension = x_dimension
        self.y_dimension = y_dimension
        self.polygons = []
        self.circles = []
        self.geometry_objects = [] # Lista de shapely objects já colocados
        
    def is_valid_position(self, shape_obj):
        # 1. Checa limites do Canvas
        minx, miny, maxx, maxy = shape_obj.bounds
        if minx < 0 or miny < 0 or maxx > self.x_dimension or maxy > self.y_dimension:
            return False
        
        # 2. Checa colisão com objetos existentes
        for existing_shape in self.geometry_objects:
            if shape_obj.intersects(existing_shape):
                return False
        return True

    def add_shape_final(self, shape_wrapper):
        # Método para adicionar oficialmente o objeto após a heurística aprovar
        self.geometry_objects.append(shape_wrapper.shapely_obj)
        if isinstance(shape_wrapper, Polygon):
            self.polygons.append(shape_wrapper)
        elif isinstance(shape_wrapper, Circle):
            self.circles.append(shape_wrapper)

    def plot_workcanvas(self):
        fig, ax = plt.subplots(figsize=(8, 8))
        ax.set_xlim(0, self.x_dimension)
        ax.set_ylim(0, self.y_dimension)
        ax.set_aspect('equal')
        ax.grid(True, linestyle='--', linewidth=0.5)
        
        for polygon in self.polygons:
            poly_patch = plt.Polygon(polygon.points, closed=True, fill=True, alpha=0.5, edgecolor=polygon.color, facecolor=polygon.color)
            ax.add_patch(poly_patch)
            
        for circle in self.circles:
            circle_patch = plt.Circle(circle.center, circle.radius, fill=True, alpha=0.5, edgecolor=circle.color, facecolor=circle.color)
            ax.add_patch(circle_patch)

        plt.title(f'Packing Otimizado - {len(self.geometry_objects)} itens')
        plt.show()

# --- CLASSE DA HEURÍSTICA ---
class GreedyPacker:
    def __init__(self, canvas, step=1.0, rotations=[0, 90, 180, 270]):
        self.canvas = canvas
        self.step = step # Precisão da grade (quanto menor, mais preciso e mais lento)
        self.rotations = rotations

    def pack(self, shapes):
        # 1. Ordenar por Área (Decrescente) - Estratégia comum de packing
        shapes.sort(key=lambda s: s.shapely_obj.area, reverse=True)

        not_placed = []

        for shape in shapes:
            placed = False
            
            # Percorre a grade (Bottom-Left strategy)
            # Y loop externo, X loop interno = preenche em faixas horizontais
            for y in np.arange(0, self.canvas.y_dimension, self.step):
                if placed: break
                for x in np.arange(0, self.canvas.x_dimension, self.step):
                    if placed: break
                    
                    # Tenta rotações
                    current_rots = self.rotations if isinstance(shape, Polygon) else [0]
                    
                    for angle in current_rots:
                        # Tenta mover e rotacionar uma cópia virtual para não estragar o original até confirmar
                        
                        # 1. Move para a posição da grade
                        shape.move_to(x, y)
                        
                        # 2. Aplica rotação (se for poligono)
                        if angle != 0 and isinstance(shape, Polygon):
                            shape.rotate(angle)

                        # 3. Valida
                        if self.canvas.is_valid_position(shape.shapely_obj):
                            self.canvas.add_shape_final(shape)
                            placed = True
                            print(f"Item colocado em x={x:.1f}, y={y:.1f} (Rot: {angle}°)")
                            break
                        else:
                            # Se falhou, precisamos "desfazer" a rotação para a próxima iteração ser limpa?
                            # Como movemos e rotacionamos o objeto real, se falhar, o próximo loop
                            # vai sobrescrever com move_to novo. O único perigo é a rotação acumular.
                            # Para simplificar neste exemplo didático, resetamos a rotação se falhar:
                            if angle != 0 and isinstance(shape, Polygon):
                                shape.rotate(-angle) 

            if not placed:
                print("Falha ao alocar um item.")
                not_placed.append(shape)
        
        return not_placed

# --- EXECUTANDO ---
if __name__ == "__main__":
    
    # Cria o Canvas
    canvas = Canvas(40, 40)
    
    # Lista de formas "soltas" para organizar
    shapes_to_pack = [
        Polygon(points=[(0,0), (10,0), (10,5), (0,5)], color='red'), # Retângulo
        Polygon(points=[(0,0), (5,10), (10,0)], color='blue'),       # Triângulo
        Circle(radius=3, color='purple'),
        Polygon(points=[(0,0), (4,0), (4,15), (0,15)], color='orange'), # Barra longa
        Circle(radius=4, color='cyan'),
        Polygon(points=[(0,0), (5,5), (10,0), (5,-5)], color='brown'), # Losango
    ]

    # Inicializa o otimizador com passo de 1 unidade (testa a cada 1.0 cm/px)
    packer = GreedyPacker(canvas, step=1.0)
    
    # Roda a heurística
    packer.pack(shapes_to_pack)
    
    # Plota
    canvas.plot_workcanvas()