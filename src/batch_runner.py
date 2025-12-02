import time
import copy
import sys
import os

# Add src to path to ensure imports work
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from main import Canvas, generate_random_shapes, Polygon, Circle
from solver import find_largest_rectangle
from optimizer import optimize_layout
from register import register_execution
from analytical_solver import AnalyticalSolver
from shapely.geometry import Polygon as ShapelyPolygon, Point

def run_single_experiment(num_shapes, max_sides, repetition):
    print(f"--- Experiment: {num_shapes} shapes, Repetition {repetition}/20 ---")
    
    canvas = Canvas(100, 100)
    generate_random_shapes(canvas, num_shapes=num_shapes, max_sides=max_sides)
    
    # Save initial state
    initial_polygons_state = copy.deepcopy(canvas.polygons)
    initial_circles_state = copy.deepcopy(canvas.circles)
    
    timestamp_id = int(time.time())
    resolution = 30
    
    # Calculate initial area
    # Note: We skip plotting to save disk space and time during batch execution
    cx, cy, w, h = find_largest_rectangle(canvas, resolution=resolution)
    initial_area = w * h

    # --- ANALYTICAL ---
    prefix = 'A'
    execution_id = f"{prefix}_{num_shapes}_{repetition}_{timestamp_id}"
    
    print(f"Running Analytical Solver for {num_shapes} shapes...")
    start_time = time.time()
    analytical_solver = AnalyticalSolver(canvas.x_dimension, canvas.y_dimension)
    for poly in canvas.polygons:
        analytical_solver.add_shape(poly)
    for circle in canvas.circles:
        analytical_solver.add_shape(circle)
        
    w_opt, h_opt, xs_opt, ys_opt, positions = analytical_solver.solve(time_limit=60)
    
    optimized_area_analytical = w_opt * h_opt
    end_time = time.time()
    execution_time_analytical = end_time - start_time
    
    # Register Analytical
    count_poly = len(canvas.polygons)
    count_circle = len(canvas.circles)
    register_execution('execution_log.csv', canvas.x_dimension, canvas.y_dimension, count_poly, count_circle, initial_area, optimized_area_analytical, 0, resolution, execution_time_analytical, execution_id)
    
    # --- METAHEURISTIC ---
    # Restore state
    canvas.polygons = copy.deepcopy(initial_polygons_state)
    canvas.circles = copy.deepcopy(initial_circles_state)
    canvas.geometry_objects = []
    for poly in canvas.polygons:
        canvas.geometry_objects.append(ShapelyPolygon(poly.points))
    for circle in canvas.circles:
        canvas.geometry_objects.append(Point(circle.center).buffer(circle.radius))
        
    prefix = 'M'
    execution_id = f"{prefix}_{num_shapes}_{repetition}_{timestamp_id}"
    
    print(f"Running Metaheuristic for {num_shapes} shapes...")
    start_time = time.time()
    max_iter = 3000
    actual_iterations = 0
    optimized_area_meta = initial_area
    
    try:
        actual_iterations = optimize_layout(canvas, max_iter=max_iter, resolution=5, use_greedy=True)
        cx_opt, cy_opt, w_opt, h_opt = find_largest_rectangle(canvas, resolution=resolution)
        optimized_area_meta = w_opt * h_opt
    except Exception as e:
        print(f"Error in Metaheuristic: {e}")
        
    end_time = time.time()
    execution_time_meta = end_time - start_time
    
    # Register Metaheuristic
    register_execution('execution_log.csv', canvas.x_dimension, canvas.y_dimension, count_poly, count_circle, initial_area, optimized_area_meta, actual_iterations, resolution, execution_time_meta, execution_id)

def main():
    max_sides = 8
    # Loop from 1 to 20 shapes
    for num_shapes in range(1, 21): 
        # Loop 20 times for each configuration
        for repetition in range(1, 21): 
            run_single_experiment(num_shapes, max_sides, repetition)

if __name__ == "__main__":
    main()
