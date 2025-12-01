import csv
import os
from datetime import datetime

def register_execution(filename, canvas_width, canvas_height, num_polygons, num_circles, initial_area, optimized_area, iterations, resolution, execution_time):
    """
    Registra os dados da execução em um arquivo CSV.
    """
    file_exists = os.path.isfile(filename)
    
    with open(filename, mode='a', newline='') as file:
        writer = csv.writer(file)
        
        # Escreve o cabeçalho se o arquivo não existir
        if not file_exists:
            writer.writerow([
                'Timestamp', 
                'Canvas Width', 
                'Canvas Height', 
                'Num Polygons', 
                'Num Circles', 
                'Initial Area', 
                'Optimized Area', 
                'Iterations', 
                'Resolution',
                'Execution Time (s)'
            ])
            
        writer.writerow([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            canvas_width,
            canvas_height,
            num_polygons,
            num_circles,
            f"{initial_area:.2f}",
            f"{optimized_area:.2f}",
            iterations,
            resolution,
            f"{execution_time:.2f}"
        ])
    
    print(f"Execução registrada em {filename}")
