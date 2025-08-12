import sys

sys.path.append("build")  # Add build directory to Python path

import node_sim


class AP(node_sim.AP):
    pass


class RT(node_sim.RT):
    pass


# Create an AP instance
ap_instance = AP(1000)
print(ap_instance.id)  # Output: 42
for id in range(10):
    rt = RT(id)
    ap_instance.add_rt(rt)

print(ap_instance.rts)  # Output: [<__main__.RT object at ...
