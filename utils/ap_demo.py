from node_sim import AP, RT

# Create an AP instance
ap_instance = AP(1000)
print(ap_instance)  # Output: 42
for id in range(10):
    rt = RT(id)
    ap_instance.add_rt(rt)

print(ap_instance.rts)  # Output: [<__main__.RT object at ...

print(ap_instance)
