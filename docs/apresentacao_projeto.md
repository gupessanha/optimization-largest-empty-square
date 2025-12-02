# Otimização de Layout e Detecção de Maior Retângulo Vazio
**Disciplina:** Otimização  
**Curso:** Engenharia de Computação  
**Autor:** [Seu Nome/GitHub Copilot]  
**Data:** Novembro 2025

---

## 1. Introdução

O problema de alocação de formas e aproveitamento de espaço (Cutting Stock Problem, Nesting Problem) é um desafio clássico na computação e pesquisa operacional, com aplicações diretas na indústria têxtil, metalúrgica e design de interfaces.

Este projeto tem como objetivo desenvolver um sistema capaz de:
1.  Representar um espaço de trabalho (Canvas) contendo obstáculos geométricos (Polígonos e Círculos).
2.  Identificar o **Maior Retângulo Vazio** (Largest Empty Rectangle - LER) disponível no espaço livre.
3.  **Otimizar o Layout**, reorganizando automaticamente a posição dos obstáculos para maximizar a área desse retângulo vazio.

A abordagem combina Geometria Computacional para validação de restrições e Meta-heurísticas para otimização global.

---

## 2. Modelagem Matemática

O problema foi dividido em dois sub-problemas acoplados: a avaliação do espaço livre e a otimização posicional.

### 2.1. Definição do Espaço e Restrições
Seja $C$ o canvas de dimensões $W \times H$.
Seja $S = \{S_1, S_2, ..., S_n\}$ o conjunto de obstáculos.
Cada obstáculo $S_i$ possui uma posição $p_i = (x_i, y_i)$.

A restrição fundamental é a não-sobreposição e contenção no canvas:
$$ S_i \subset C \quad \forall i $$
$$ S_i \cap S_j = \emptyset \quad \forall i \neq j $$

### 2.2. Detecção do Maior Retângulo (Sub-problema de Avaliação)
Para calcular a área livre, optou-se por uma abordagem de **Discretização (Rasterização)** em vez de uma abordagem analítica vetorial.

O canvas é mapeado em uma matriz binária $M$ de resolução $R$:
$$ M_{x,y} = \begin{cases} 0 & \text{se } (x,y) \in \bigcup S_i \\ 1 & \text{se } (x,y) \in \text{Livre} \end{cases} $$

O problema se reduz a encontrar o sub-retângulo de área máxima contendo apenas $1$s na matriz $M$. Utilizamos o algoritmo de **Histograma**, que possui complexidade linear $O(N)$ para cada linha da matriz, onde $N$ é o número de colunas.

### 2.3. Otimização de Layout (Problema Principal)
Definimos o vetor de decisão $\mathbf{x}$ contendo as coordenadas de todos os obstáculos:
$$ \mathbf{x} = [x_1, y_1, x_2, y_2, \dots, x_n, y_n] $$

A função objetivo $f(\mathbf{x})$ que desejamos **maximizar** é a área do maior retângulo vazio dada a configuração $\mathbf{x}$:

$$ \text{Maximizar } A(\mathbf{x}) = \text{Area}(\text{LargestRect}(C \setminus \bigcup S_i(\mathbf{x}))) $$

Sujeito a:
$$ \text{Colisões}(\mathbf{x}) = 0 $$

Como a função $A(\mathbf{x})$ é não-linear, não-convexa e não-diferenciável (devido à discretização e mudanças topológicas abruptas), métodos de gradiente (como Newton-Raphson) são inviáveis. Utilizamos a meta-heurística **Evolução Diferencial**.

---

## 3. Implementação e Código

O projeto foi desenvolvido em Python utilizando as seguintes bibliotecas:
*   **Shapely:** Para manipulação geométrica vetorial e detecção precisa de colisões.
*   **PIL (Pillow) & NumPy:** Para rasterização eficiente e manipulação matricial.
*   **SciPy:** Para o algoritmo de otimização `differential_evolution`.

### Estrutura do Repositório

1.  **`src/solver.py`**:
    *   Implementa a função `find_largest_rectangle`.
    *   Converte as formas vetoriais em uma grade de pixels.
    *   Aplica o algoritmo de "Maior Retângulo em Histograma" iterando sobre as linhas da matriz.

2.  **`src/optimizer.py`**:
    *   Define a função de custo (negativo da área).
    *   Implementa penalidade "Big-M" (valor infinito) caso a função `check_collision` do Shapely detecte sobreposição.
    *   Executa o loop de evolução diferencial para perturbar as posições $(x, y)$ das formas.

3.  **`src/main.py`**:
    *   Orquestrador do sistema.
    *   Gera visualizações (`matplotlib`) do estado inicial e otimizado.

---

## 4. Discussão e Resultados

### 4.1. Resultados Obtidos
Nos testes realizados, o sistema demonstrou capacidade de reorganizar formas aleatórias para liberar grandes áreas contíguas.
*   **Cenário Inicial:** Formas dispersas no centro. Área $\approx 300$.
*   **Cenário Otimizado:** Formas agrupadas nos cantos ou bordas. Área $\approx 420$.

### 4.2. Análise: Rasterização vs. Analítico
Uma decisão crítica de engenharia foi o uso de **Rasterização** para calcular a área livre.

*   **Por que não analítico?** Calcular o maior retângulo vazio exato entre polígonos arbitrários e círculos requer a construção de Diagramas de Voronoi Generalizados ou Decomposição Trapezoidal, algoritmos de alta complexidade de implementação e custo computacional $O(n^2 \log n)$ ou pior dependendo da geometria curva.
*   **Vantagem da Rasterização:** Transforma o problema geométrico complexo em operações matriciais simples e extremamente rápidas.
*   **Trade-off:** A precisão é limitada pela resolução da grade. No entanto, para fins de otimização de layout, uma aproximação rápida é preferível a uma solução exata lenta, pois a função objetivo precisa ser avaliada milhares de vezes pelo algoritmo genético.

### 4.3. Conclusão
O projeto atingiu os objetivos de aprendizado, demonstrando como combinar geometria computacional clássica com algoritmos de otimização estocástica para resolver problemas de empacotamento e layout.
