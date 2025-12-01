# Migração para Solução Analítica (MIP)

## Contexto
O projeto original utilizava uma abordagem heurística baseada em **Evolução Diferencial** para o posicionamento das formas e **Rasterização** para o cálculo do maior retângulo vazio. Embora eficaz para encontrar soluções aproximadas rapidamente, essa abordagem não garante a otimalidade global e depende de parâmetros de resolução.

## Nova Abordagem: Programação Inteira Mista (MIP)
Para solucionar o problema de forma analítica e exata, adotamos a **Programação Inteira Mista (Mixed-Integer Programming - MIP)**.

### Formulação Matemática

O problema é modelado como um problema de empacotamento (Packing Problem) com o objetivo de maximizar o tamanho de um retângulo vazio inserido no layout.

#### Variáveis de Decisão
*   $x_i, y_i$: Coordenadas do canto inferior esquerdo da forma $i$.
*   $w_r, h_r$: Largura e altura do maior retângulo vazio.
*   $x_s, y_s$: Coordenadas do retângulo vazio.
*   $b_{ij, k}$: Variáveis binárias para garantir a não-sobreposição entre a forma $i$ e a forma $j$.
*   $b_{is, k}$: Variáveis binárias para garantir a não-sobreposição entre a forma $i$ e o retângulo vazio.

#### Função Objetivo
$$ \text{Maximizar } w_r + h_r $$
*Nota: Como a maximização direta da área ($w_r \cdot h_r$) resultaria em um problema não-linear (quadrático), utilizamos o perímetro ($2(w_r + h_r)$) como uma aproximação linear para solvers MIP padrão.*

#### Restrições

1.  **Limites do Canvas**:
    $$ 0 \le x_i \le W - w_i $$
    $$ 0 \le y_i \le H - h_i $$
    $$ 0 \le x_s \le W - w_r $$
    $$ 0 \le y_s \le H - h_r $$

2.  **Não-Sobreposição (Big-M)**:
    Para cada par de formas $i$ e $j$, pelo menos uma das seguintes condições deve ser verdadeira:
    *   $i$ está à esquerda de $j$: $x_i + w_i \le x_j$
    *   $i$ está à direita de $j$: $x_j + w_j \le x_i$
    *   $i$ está abaixo de $j$: $y_i + h_i \le y_j$
    *   $i$ está acima de $j$: $y_j + h_j \le y_i$

    Isso é implementado com variáveis binárias $b$ e uma constante grande $M$.

3.  **Retângulo Vazio**:
    O retângulo de dimensões $w_r, h_r$ não pode sobrepor nenhuma forma $i$, utilizando as mesmas restrições de não-sobreposição descritas acima.

### Simplificações Adotadas
*   **Aproximação de Formas**: Para viabilizar o modelo MIP, todas as formas (polígonos e círculos) são aproximadas pelos seus **Bounding Boxes** (retângulos envolventes).
*   **Rotação**: Nesta primeira versão analítica, a rotação das formas não é considerada para manter a linearidade do modelo.

## Vantagens
*   **Garantia de Otimalidade**: O solver garante encontrar a melhor solução possível dentro das simplificações adotadas.
*   **Resolução Infinita**: Não depende de grid ou pixels; as coordenadas são contínuas.

## Desvantagens
*   **Complexidade Computacional**: O tempo de resolução cresce exponencialmente com o número de formas (NP-Hard).
*   **Conservadorismo**: O uso de Bounding Boxes pode desperdiçar espaço se as formas forem muito irregulares ou rotacionadas.
