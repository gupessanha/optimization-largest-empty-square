import numpy as np
from shapely.geometry import Polygon as ShapelyPolygon, Point
from shapely import affinity
from typing import List, Tuple, Any, Union

class GreedyPacker:
    """
    Algoritmo guloso para empacotamento de formas 2D (Bin Packing).
    Tenta posicionar os itens um a um, testando posições em uma grade e rotações.
    """
    def __init__(self, width: float, height: float, step: float = 1.0, rotations: List[int] = [0, 90, 180, 270]):
        self.width = width
        self.height = height
        self.step = step
        self.rotations = rotations
        self.placed_geometries = [] # Lista de objetos Shapely já posicionados

    def _to_shapely(self, shape: Any) -> Union[ShapelyPolygon, Point]:
        """Converte objetos do domínio (Polygon/Circle) para Shapely."""
        # Verifica se é um objeto Polygon do main.py (tem atributo points)
        if hasattr(shape, 'points'):
            return ShapelyPolygon(shape.points)
        # Verifica se é um objeto Circle do main.py (tem center e radius)
        elif hasattr(shape, 'radius'):
            # Assumindo que o centro inicial é irrelevante para o packing, criamos em (0,0)
            # Mas se o objeto já tem centro, usamos ele? 
            # O packer vai mover, então começamos na origem ou no centroide.
            # Para consistência, criamos no (0,0) e movemos.
            return Point(0, 0).buffer(shape.radius)
        else:
            raise ValueError(f"Tipo de forma desconhecido: {type(shape)}")

    def _is_valid(self, shape_geom: Union[ShapelyPolygon, Point]) -> bool:
        """Verifica se a geometria está dentro dos limites e não colide."""
        minx, miny, maxx, maxy = shape_geom.bounds
        if minx < 0 or miny < 0 or maxx > self.width or maxy > self.height:
            return False
        
        for existing in self.placed_geometries:
            if shape_geom.intersects(existing):
                return False
        return True

    def pack(self, shapes: List[Any]) -> List[Tuple[float, float, float]]:
        """
        Executa o empacotamento.
        
        Args:
            shapes: Lista de objetos (Polygon ou Circle) a serem empacotados.
            
        Returns:
            List[Tuple]: Lista de configurações finais para cada shape na ordem original.
                         Cada config é (x, y, rotation) ou similar.
                         Para simplificar a integração com o DE, retornamos um vetor de posições?
                         O DE espera [x1, y1, x2, y2...]. A rotação não é otimizada pelo DE atual.
                         
                         O DE atual NÃO otimiza rotação. Ele só move (x, y).
                         Se o GreedyPacker rotacionar, o DE vai precisar saber que a forma mudou.
                         
                         Se o GreedyPacker rotacionar um polígono, os "pontos relativos" usados no DE
                         precisam ser atualizados para refletir essa rotação.
                         
                         Portanto, este método deve retornar os objetos modificados ou 
                         informações suficientes para reconstruí-los.
        """
        # 1. Preparar itens com metadados (índice original, objeto shapely, objeto original)
        items = []
        for i, shape in enumerate(shapes):
            geom = self._to_shapely(shape)
            # Centraliza geometria em (0,0) para facilitar rotação e translação
            centroid = geom.centroid
            geom = affinity.translate(geom, xoff=-centroid.x, yoff=-centroid.y)
            items.append({
                'index': i,
                'original': shape,
                'geom': geom,
                'area': geom.area,
                'final_geom': None,
                'pos': (0, 0),
                'rotation': 0
            })

        # 2. Ordenar por área decrescente
        items.sort(key=lambda x: x['area'], reverse=True)

        # 3. Loop de posicionamento
        for item in items:
            placed = False
            geom_base = item['geom'] # Centrado em 0,0
            
            # Grid search
            # Otimização: passo adaptativo ou busca espiral poderia ser melhor, mas vamos de grid simples
            for y in np.arange(0, self.height, self.step):
                if placed: break
                for x in np.arange(0, self.width, self.step):
                    if placed: break
                    
                    # Tenta rotações
                    # Se for círculo, rotação é irrelevante (Point buffer)
                    is_circle = isinstance(geom_base, ShapelyPolygon) and len(geom_base.exterior.coords) > 100 # Heurística ruim
                    # Melhor checar o objeto original
                    is_circle = hasattr(item['original'], 'radius')
                    
                    current_rots = [0] if is_circle else self.rotations
                    
                    for angle in current_rots:
                        # 1. Rotaciona (em torno do centro 0,0)
                        rotated = affinity.rotate(geom_base, angle, origin=(0,0))
                        
                        # 2. Translada para posição candidata (x,y)
                        # Assumimos que x,y é o CENTROIDE ou o CANTO INFERIOR ESQUERDO?
                        # O DE usa (x,y) como translação dos pontos relativos.
                        # Se os pontos relativos são em relação ao centroide, então x,y é o novo centroide.
                        # Vamos assumir x,y como centroide para consistência com a lógica de "move_to" do DE.
                        
                        # Mas espere, o DE usa:
                        # x, y = position_vector[...]
                        # new_points = [(px + x, py + y) for px, py in template]
                        # Onde template são pontos relativos ao centroide.
                        # Então (x,y) É a posição do centroide.
                        
                        # Porém, o GreedyPacker do test.py usava bounding box minx, miny.
                        # Vamos usar centroide aqui para alinhar com o DE.
                        # Mas para "encostar" nos cantos, usar bounding box é melhor.
                        # Vamos calcular o offset necessário para que o bbox min fique em x,y da grade?
                        # Não, vamos testar posições de centroide na grade.
                        # Se a grade for fina o suficiente, funciona.
                        
                        candidate = affinity.translate(rotated, xoff=x, yoff=y)
                        
                        if self._is_valid(candidate):
                            self.placed_geometries.append(candidate)
                            item['final_geom'] = candidate
                            item['pos'] = (x, y)
                            item['rotation'] = angle
                            placed = True
                            break
            
            if not placed:
                print(f"Aviso: Não foi possível alocar o item {item['index']} (Área: {item['area']:.2f})")
                # Adiciona fora do canvas ou em posição aleatória válida?
                # Para o DE, precisamos de uma posição inicial. Se não couber, colocamos no meio?
                # Colocamos em (0,0) e deixamos o DE resolver (vai ter colisão, penalidade alta).
                item['final_geom'] = geom_base # Em 0,0
                item['pos'] = (self.width/2, self.height/2) # Meio
                self.placed_geometries.append(affinity.translate(geom_base, xoff=self.width/2, yoff=self.height/2))

        # 4. Reordenar para a ordem original e retornar resultado
        items.sort(key=lambda x: x['index'])
        
        # Retorna lista de dicionários com as infos necessárias
        return items

