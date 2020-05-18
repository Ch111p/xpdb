import bdb

def funcA(a, b):
    return a + b

def sub(a, b):
    return a - b

if __name__ == '__main__':
    a = funcA(1, 2)
    b = sub(a, 2)
    print(b)

