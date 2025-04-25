# Refactored version of the second example file
import os
import math

class ShapeCalculator:
    """Calculates area for different shapes."""
    
    SUPPORTED_SHAPES = {"rectangle", "circle"}

    @staticmethod
    def calculate_rectangle_area(width, height):
        if width > 0 and height > 0:
            return width * height
        return 0

    @staticmethod
    def calculate_circle_area(radius):
        if radius > 0:
            return math.pi * radius ** 2
        return 0

    def calculate_area(self, shape, dimensions):
        if shape not in self.SUPPORTED_SHAPES:
            print(f"Shape '{shape}' not supported.")
            return None

        if shape == "rectangle":
            if len(dimensions) == 2:
                return self.calculate_rectangle_area(dimensions[0], dimensions[1])
            else:
                print("Rectangle requires 2 dimensions (width, height).")
                return None
        elif shape == "circle":
            if len(dimensions) == 1:
                return self.calculate_circle_area(dimensions[0])
            else:
                print("Circle requires 1 dimension (radius).")
                return None
        return None # Should not be reached if logic is correct

def safe_list_files(directory):
    """Safely lists files in a directory, handling potential errors."""
    if not isinstance(directory, str) or not os.path.isdir(directory):
        print(f"Invalid directory path: {directory}")
        return []
    try:
        files = os.listdir(directory)
        return files
    except FileNotFoundError:
        print(f"Directory not found: {directory}")
        return []
    except PermissionError:
        print(f"Permission denied for directory: {directory}")
        return []
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return []

class SimpleCounter:
    """A simple counter class to avoid global state."""
    def __init__(self):
        self._count = 0

    def increment(self):
        self._count += 1
        return self._count

    @property
    def count(self):
        return self._count

if __name__ == '__main__':
    calculator = ShapeCalculator()
    rect_area = calculator.calculate_area("rectangle", [5, 10])
    if rect_area is not None:
        print(f"Rectangle Area: {rect_area:.2f}")

    circ_area = calculator.calculate_area("circle", [7])
    if circ_area is not None:
        print(f"Circle Area: {circ_area:.2f}")

    # Using the counter class
    my_counter = SimpleCounter()
    my_counter.increment()
    print(f"Count: {my_counter.count}") 