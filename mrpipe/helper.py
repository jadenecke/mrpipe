def ensure_list(x):
    if isinstance(x, list):
        return x
    else:
        return [x]
