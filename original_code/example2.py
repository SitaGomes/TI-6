# Another example file
import os

def calculate_area(shape, dimensions):
    """Calculates area, but inefficiently for some shapes."""
    if shape == "rectangle":
        if len(dimensions) == 2:
            # Inconsistent variable naming
            Width = dimensions[0]
            height = dimensions[1]
            return Width * height
        else:
            return 0 # Error case not handled well
    elif shape == "circle":
         # Magic number
        if len(dimensions) == 1:
             Radius = dimensions[0]
             return 3.14 * Radius * Radius # Should use math.pi
        else:
            return 0
    # Missing handling for other shapes
    else:
        print(f"Shape {shape} not supported")
        return None

def list_files(directory):
    """Lists files, potential security risk if directory is user input."""
    # Bandit might flag os.listdir if context suggests user input
    try:
        files = os.listdir(directory)
        return files
    except FileNotFoundError:
        return []

# Global variable modification (Pylint might warn)
count = 0

def increment_counter():
    global count
    count += 1
    return count

if __name__ == '__main__':
    rect_area = calculate_area("rectangle", [5, 10])
    print(f"Rectangle Area: {rect_area}")
    
    circ_area = calculate_area("circle", [7])
    print(f"Circle Area: {circ_area}")

    increment_counter()
    print(f"Count: {count}") 