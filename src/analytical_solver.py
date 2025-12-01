import pulp
from typing import List, Tuple, Any

class AnalyticalSolver:
    def __init__(self, canvas_width: float, canvas_height: float):
        self.W = canvas_width
        self.H = canvas_height
        self.shapes = [] # List of (width, height, original_shape)

    def add_shape(self, shape: Any):
        """
        Adiciona uma forma ao solver.
        Calcula o Bounding Box da forma para usar no modelo linear.
        """
        if hasattr(shape, 'radius'): # Circle
            w = shape.radius * 2
            h = shape.radius * 2
        elif hasattr(shape, 'points'): # Polygon
            # Calcula bounding box
            xs = [p[0] for p in shape.points]
            ys = [p[1] for p in shape.points]
            w = max(xs) - min(xs)
            h = max(ys) - min(ys)
        else:
            raise ValueError("Forma desconhecida")
        
        self.shapes.append({'w': w, 'h': h, 'obj': shape})

    def solve(self, time_limit: int = 60) -> Tuple[float, float, float, float, List[Tuple[float, float]]]:
        """
        Resolve o problema de otimização usando MIP.
        Retorna (w_opt, h_opt, x_rect, y_rect, positions)
        """
        n = len(self.shapes)
        prob = pulp.LpProblem("LargestEmptyRectangleLayout", pulp.LpMaximize)

        # Variáveis para as formas
        # x[i], y[i] são as coordenadas do canto inferior esquerdo do bounding box da forma i
        x = [pulp.LpVariable(f"x_{i}", 0, self.W) for i in range(n)]
        y = [pulp.LpVariable(f"y_{i}", 0, self.H) for i in range(n)]

        # Variáveis para o retângulo vazio
        # w_rect, h_rect são largura e altura do retângulo
        # xs, ys são as coordenadas do retângulo
        w_rect = pulp.LpVariable("w_rect", 0, self.W)
        h_rect = pulp.LpVariable("h_rect", 0, self.H)
        xs = pulp.LpVariable("xs", 0, self.W)
        ys = pulp.LpVariable("ys", 0, self.H)

        # Função Objetivo: Maximizar o perímetro do retângulo (proxy linear para área)
        # Maximizar w + h tende a maximizar a área em problemas de empacotamento
        prob += w_rect + h_rect

        # Big-M constant
        M = max(self.W, self.H) * 2

        # Restrições de Limites (Boundary)
        for i in range(n):
            w_i = self.shapes[i]['w']
            h_i = self.shapes[i]['h']
            prob += x[i] + w_i <= self.W
            prob += y[i] + h_i <= self.H

        # Limites do Retângulo Vazio
        prob += xs + w_rect <= self.W
        prob += ys + h_rect <= self.H

        # Restrições de Não-Sobreposição entre Formas (Pairwise)
        for i in range(n):
            for j in range(i + 1, n):
                b1 = pulp.LpVariable(f"b_{i}_{j}_1", cat='Binary') # i left of j
                b2 = pulp.LpVariable(f"b_{i}_{j}_2", cat='Binary') # i right of j
                b3 = pulp.LpVariable(f"b_{i}_{j}_3", cat='Binary') # i below j
                b4 = pulp.LpVariable(f"b_{i}_{j}_4", cat='Binary') # i above j

                w_i, h_i = self.shapes[i]['w'], self.shapes[i]['h']
                w_j, h_j = self.shapes[j]['w'], self.shapes[j]['h']

                # Restrições Big-M
                prob += x[i] + w_i <= x[j] + M * (1 - b1)
                prob += x[j] + w_j <= x[i] + M * (1 - b2)
                prob += y[i] + h_i <= y[j] + M * (1 - b3)
                prob += y[j] + h_j <= y[i] + M * (1 - b4)

                # Pelo menos uma condição deve ser verdadeira
                prob += b1 + b2 + b3 + b4 >= 1

        # Restrições de Não-Sobreposição entre Retângulo Vazio e Formas
        for i in range(n):
            # Variáveis binárias para separar o retângulo (s) da forma (i)
            bs1 = pulp.LpVariable(f"bs_{i}_1", cat='Binary') # s left of i
            bs2 = pulp.LpVariable(f"bs_{i}_2", cat='Binary') # s right of i
            bs3 = pulp.LpVariable(f"bs_{i}_3", cat='Binary') # s below i
            bs4 = pulp.LpVariable(f"bs_{i}_4", cat='Binary') # s above i

            w_i, h_i = self.shapes[i]['w'], self.shapes[i]['h']

            # Retângulo (xs, ys, w_rect, h_rect) vs Forma i (xi, yi, wi, hi)
            
            # s left of i: xs + w_rect <= xi
            prob += xs + w_rect <= x[i] + M * (1 - bs1)
            
            # s right of i: xi + wi <= xs
            prob += x[i] + w_i <= xs + M * (1 - bs2)
            
            # s below i: ys + h_rect <= yi
            prob += ys + h_rect <= y[i] + M * (1 - bs3)
            
            # s above i: yi + hi <= ys
            prob += y[i] + h_i <= ys + M * (1 - bs4)

            prob += bs1 + bs2 + bs3 + bs4 >= 1

        # Resolver
        # Usar CBC solver (padrão do PuLP) com limite de tempo
        solver = pulp.PULP_CBC_CMD(timeLimit=time_limit, msg=True)
        prob.solve(solver)

        status = pulp.LpStatus[prob.status]
        print(f"Status da Solução: {status}")

        if status in ['Optimal', 'Feasible']:
            final_w = pulp.value(w_rect)
            final_h = pulp.value(h_rect)
            final_xs = pulp.value(xs)
            final_ys = pulp.value(ys)
            
            positions = []
            for i in range(n):
                positions.append((pulp.value(x[i]), pulp.value(y[i])))
                
            return final_w, final_h, final_xs, final_ys, positions
        else:
            return 0, 0, 0, 0, []
