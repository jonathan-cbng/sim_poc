#!/usr/bin/env python3
from nodes import AP, RT

# for i in range(30,0,-1):
#     print(f"Sleeping {i}")
#     time.sleep(1)


def main():
    # Create an AP instance
    ap_instance = AP(1000)
    print(ap_instance)  # Output: 42
    for id in range(10):
        rt = RT(id)
        ap_instance.add_rt(rt)

    print(ap_instance.rts)  # Output: [<__main__.RT object at ...

    print(ap_instance)


if __name__ == "__main__":
    main()
