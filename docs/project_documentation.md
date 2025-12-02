# Documentação do Projeto: Otimização de Espaços Vazios

Este documento registra a evolução do desenvolvimento do algoritmo para detecção de espaços vazios em um canvas com obstáculos (polígonos e círculos). O projeto evoluiu de uma detecção de colisão básica para a identificação do maior quadrado vazio e, posteriormente, do maior retângulo vazio.

## 1. Prevenção de Colisões

Antes de otimizar o espaço, foi necessário garantir que os objetos inseridos não se sobrepusessem.

### Abordagem
Utilizou-se a biblioteca **Shapely** para geometria computacional. Ao tentar adicionar um novo objeto, cria-se uma representação geométrica dele e verifica-se a interseção com todos os objetos já presentes na lista `geometry_objects`.

### Código (`src/main.py`)
```python
from shapely.geometry import Polygon as ShapelyPolygon, Point

# ... dentro da classe Canvas ...

def add_polygon(self, polygon):
    # ... validações ...
    new_shape = ShapelyPolygon(polygon.points)
    
    for shape in self.geometry_objects:
        if new_shape.intersects(shape):
            raise ValueError("Colisão detectada!")
    
    self.geometry_objects.append(new_shape)
    # ...
```

---

## 2. Maior Quadrado Vazio

O primeiro objetivo de otimização foi encontrar o maior quadrado ($L \times L$) que pudesse ser inserido no espaço livre.

### Formulação Matemática

A abordagem escolhida baseou-se na **Transformada de Distância** em uma grade discretizada (imagem rasterizada).

1.  **Discretização:** O canvas contínuo é convertido em uma matriz binária $M$ (imagem), onde $0$ representa obstáculo e $1$ representa espaço livre.
2.  **Métrica de Chebyshev ($L_\infty$):** Para quadrados alinhados aos eixos, a distância relevante não é a Euclidiana, mas a de Chebyshev:
    $$d_\infty(p, q) = \max(|x_p - x_q|, |y_p - y_q|)$$
    Nesta métrica, o conjunto de pontos a uma distância $r$ de um centro forma um quadrado.
3.  **Função Objetivo:** Calculamos o campo de distância $D(p)$ para cada pixel livre $p$:
    $$D(p) = \min_{q \in \text{Obstáculos}} d_\infty(p, q)$$
    O valor $D(p)$ representa o "raio" (metade do lado) do maior quadrado que pode ser centrado em $p$.
4.  **Solução:** O centro do maior quadrado é o ponto $p^*$ que maximiza $D(p)$.

### Implementação (`src/solver.py` - Versão Quadrado)

Utilizou-se `scipy.ndimage.distance_transform_cdt` com a métrica `chessboard`.

```python
import numpy as np
from scipy.ndimage import distance_transform_cdt
from PIL import Image, ImageDraw

def find_largest_square(canvas, resolution=10):
    # 1. Rasterização (Canvas -> Imagem Binária)
    width_px = int(canvas.x_dimension * resolution)
    height_px = int(canvas.y_dimension * resolution)
    img = Image.new('L', (width_px, height_px), 1)
    draw = ImageDraw.Draw(img)
    
    # ... desenha polígonos e círculos com cor 0 ...
    
    grid = np.array(img)
    
    # 2. Transformada de Distância (Chessboard)
    dt = distance_transform_cdt(grid, metric='chessboard')
    
    # 3. Tratamento de Bordas
    # Calcula distância para as bordas da imagem para garantir que o quadrado não saia do canvas
    rows, cols = np.indices(dt.shape)
    dist_x = np.minimum(cols, width_px - 1 - cols)
    dist_y = np.minimum(rows, height_px - 1 - rows)
    dist_border = np.minimum(dist_x, dist_y)
    
    dt_final = np.minimum(dt, dist_border + 1)
    
    # 4. Encontrar Máximo
    max_dist_px = np.max(dt_final)
    argmax = np.argmax(dt_final)
    y_px, x_px = np.unravel_index(argmax, dt.shape)
    
    # Conversão de volta para unidades do canvas
    radius = (max_dist_px - 0.5) / resolution
    center_x = (x_px + 0.5) / resolution
    center_y = (height_px - (y_px + 0.5)) / resolution
    
    return center_x, center_y, radius
```

---

## 3. Maior Retângulo Vazio

O requisito evoluiu para encontrar o maior retângulo (largura e altura independentes), o que permite aproveitar melhor espaços alongados que um quadrado não preencheria eficientemente.

### Formulação Matemática

A Transformada de Distância não se aplica diretamente aqui, pois ela assume expansão uniforme (raio). A solução clássica para este problema é o algoritmo do **Maior Retângulo em Histograma**.

1.  **Decomposição por Linhas:** A matriz binária é processada linha por linha.
2.  **Histograma Acumulado:** Para cada linha $i$, construímos um vetor de "alturas" $H_i$. Para cada coluna $j$:
    *   Se $M[i][j] == 0$ (obstáculo), $H_i[j] = 0$.
    *   Se $M[i][j] == 1$ (livre), $H_i[j] = H_{i-1}[j] + 1$ (acumula a altura livre acima).
3.  **Otimização Linear:** Para cada linha, o problema se reduz a encontrar o maior retângulo dentro do histograma $H_i$. Isso é resolvido em $O(N)$ usando uma **Pilha (Stack)** monótona crescente para encontrar os limites esquerdo e direito de cada barra do histograma.
4.  **Complexidade:** $O(R \times C)$, onde $R$ e $C$ são as dimensões da grade.

### Implementação (`src/solver.py` - Versão Retângulo)

```python
import numpy as np
from PIL import Image, ImageDraw

def largest_rectangle_area(heights):
    """Encontra o maior retângulo em um histograma linear em O(N)."""
    stack = [-1]
    max_area = 0
    best_rect = (0, 0, 0, 0) # area, height, x_start, width
    
    heights_extended = np.append(heights, 0)
    
    for i, h in enumerate(heights_extended):
        while stack[-1] != -1 and heights_extended[stack[-1]] >= h:
            height = heights_extended[stack.pop()]
            width = i - stack[-1] - 1
            area = height * width
            if area > max_area:
                max_area = area
                best_rect = (area, height, stack[-1] + 1, width)
        stack.append(i)
        
    return best_rect

def find_largest_rectangle(canvas, resolution=10):
    # 1. Rasterização (Igual à versão anterior)
    # ... (código de desenho PIL omitido) ...
    
    grid = np.array(img)
    width_px, height_px = grid.shape[1], grid.shape[0]
    
    max_area_global = 0
    best_rect_global = None
    
    # 2. Iteração por Linhas e Histograma
    heights = np.zeros(width_px, dtype=int)
    
    for row in range(height_px):
        # Atualiza histograma (se livre soma 1, se obstáculo zera)
        mask = (grid[row] == 1)
        heights[mask] += 1
        heights[~mask] = 0
        
        # 3. Resolve para a linha atual
        area, h, x_start, w = largest_rectangle_area(heights)
        
        if area > max_area_global:
            max_area_global = area
            best_rect_global = (x_start, row, w, h)
            
    # 4. Conversão de Coordenadas
    x_px_start, y_px_bottom, w_px, h_px = best_rect_global
    
    width = w_px / resolution
    height = h_px / resolution
    
    x_min = x_px_start / resolution
    center_x = x_min + width / 2
    
    # Ajuste de Y (Imagem cresce para baixo, Canvas para cima)
    y_center_img = y_px_bottom - h_px / 2 + 0.5
    center_y = (height_px - y_center_img) / resolution
    
    return center_x, center_y, width, height
```

## Comparação de Resultados

Em um teste com um triângulo e um círculo como obstáculos:

*   **Abordagem Quadrado:** Encontrou um quadrado de lado ~15.00 (Área ~225).
*   **Abordagem Retângulo:** Encontrou um retângulo de $20.00 \times 15.00$ (Área 300).

A abordagem retangular provou-se superior para maximização de área em cenários onde o espaço livre é assimétrico.

---

## 4. Reorganização de Formas (Otimização de Layout)

Além de detectar o maior espaço vazio em uma configuração estática, o sistema foi expandido para **mover as formas** de modo a maximizar esse espaço. Este é um problema de otimização combinatória e geométrica complexo (NP-difícil).

### Formulação Matemática

Seja $S = \{S_1, S_2, ..., S_n\}$ o conjunto de formas (obstáculos) a serem posicionadas no canvas de dimensões $W \times H$.
Cada forma $S_i$ possui uma geometria fixa, mas sua posição é definida por um vetor de coordenadas $p_i = (x_i, y_i)$.

O vetor de configuração do sistema é:
$$ \mathbf{x} = [x_1, y_1, x_2, y_2, ..., x_n, y_n] $$

#### Função Objetivo
Queremos maximizar a área do maior retângulo vazio $R_{max}$ que pode ser inscrito no espaço livre $F(\mathbf{x})$:

$$ \text{Maximizar } f(\mathbf{x}) = \text{Area}(\text{LargestEmptyRect}(Canvas \setminus \bigcup_{i=1}^n S_i(p_i))) $$

#### Restrições
O conjunto de configurações válidas $\Omega$ é definido por:

1.  **Limites do Canvas:** Todas as formas devem estar inteiramente contidas no canvas.
    $$ S_i(p_i) \subset [0, W] \times [0, H], \quad \forall i $$
2.  **Não-Sobreposição:** Nenhuma forma pode interceptar outra.
    $$ S_i(p_i) \cap S_j(p_j) = \emptyset, \quad \forall i \neq j $$

### Algoritmo de Solução: Evolução Diferencial

Como a função objetivo $f(\mathbf{x})$ é não-linear, não-diferenciável (devido à natureza discreta da rasterização e mudanças abruptas na topologia do espaço livre) e possui muitos ótimos locais, métodos baseados em gradiente não funcionam bem.

Utilizamos a **Evolução Diferencial (Differential Evolution - DE)**, uma meta-heurística estocástica que evolui uma população de soluções candidatas.

1.  **População:** $N$ vetores de configuração aleatórios.
2.  **Função de Custo (Fitness):**
    *   Se houver colisão ou violação de limites: $Custo = \infty$ (ou um valor muito alto).
    *   Se válido: $Custo = -1 \times \text{Area}(R_{max})$ (Minimizamos o negativo da área).
3.  **Evolução:** A cada geração, novos vetores são criados combinando vetores existentes (mutação e cruzamento). Se o novo vetor tiver menor custo, ele substitui o antigo.

Essa abordagem permite encontrar layouts onde as formas se agrupam (ex: nos cantos), liberando grandes áreas contíguas no centro.

---

## 5. Propostas de Otimização Futura (Solvers Avançados)

Para cenários de larga escala (ex: Canvas 1000x1000 com centenas de formas), a abordagem baseada em rasterização e evolução diferencial pode se tornar um gargalo computacional. Abaixo estão propostas de implementações alternativas utilizando solvers matemáticos dedicados para reduzir drasticamente o tempo de execução.

### 5.1. Substituição da Rasterização por Programação Inteira Mista (MILP)
Atualmente, a detecção do maior retângulo vazio varre uma matriz de pixels. Isso pode ser substituído por um modelo matemático exato usando solvers como **PuLP**, **Gurobi** ou **CVXPY**.

**Modelagem MILP:**
*   **Variáveis:** $x, y, w, h$ (dimensões do retângulo vazio).
*   **Variáveis Binárias:** $b_{i, \text{pos}}$ indicando a posição relativa do retângulo em relação a cada obstáculo $i$ (esquerda, direita, cima, baixo).
*   **Restrições:** Se $b_{i, \text{left}} = 1$, então $x + w \le x_{i, \text{min}}$. (O retângulo deve estar completamente à esquerda do obstáculo).
*   **Objetivo:** Maximizar $w \cdot h$ (linearizado ou aproximado).

Essa abordagem elimina a necessidade de criar matrizes gigantes na memória e resolve o problema usando álgebra, sendo ideal para canvas de alta resolução.

### 5.2. Substituição da Evolução Diferencial por Otimização Baseada em Gradiente
A Evolução Diferencial é robusta mas lenta pois "adivinha" soluções. Para usar solvers rápidos baseados em gradiente (como **SLSQP** ou **IPOPT** via `scipy.optimize`), é necessário tornar a função de colisão diferenciável.

**Abordagem de Campos de Potencial:**
*   Em vez de uma verificação binária de colisão (Sim/Não), define-se uma função de energia $E$ baseada na sobreposição das formas.
*   $E(\mathbf{x}) = \sum \text{Area}(S_i \cap S_j)$.
*   O solver minimiza $E(\mathbf{x})$ usando derivadas, fazendo as formas "deslizarem" suavemente para fora umas das outras, convergindo muito mais rápido que a tentativa e erro estocástica.
