import sys

sys.path.append("build")  # Add build directory to Python path

import ap

# Create an AP instance
ap_instance = ap.AP(42)
print(ap_instance.greet())  # Output: Hello from AP 42
print(ap_instance.ap_id)  # Output: 42
ap_instance.ap_id = 100
print(ap_instance.greet())  # Output: Hello from AP 100
