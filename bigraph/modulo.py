def mod_value(mod, value):
    def apply_mod(x):
        return x % mod
    return apply_mod

def mod_add(mod, a, b):
    return (a + b) % mod

def mod_multiply(mod, a, b):
    return (a * b) % mod

def mod_metabolism(mod, base):
    def metabolism(a):
        return (base * a) % mod
    return metabolism

def f_add(mod, fa, fb):
    def add(a, b):
        return (fa(a) + fb(b)) % mod
    return add

def f_multiply(mod, fa, fb):
    def multiply(a, b):
        return (fa(a) * fb(b)) % mod
    return multiply

def mod_repair(mod, base):
    def repair(b):
        return mod_metabolism(mod, base * b)
    return repair

def generate_metabolism(mod):
    return [
        mod_metabolism(mod, index + 1)
        for index in range(mod)]

def generate_repair(mod):
    return [
        mod_repair(mod, index + 1)
        for index in range(mod)]

