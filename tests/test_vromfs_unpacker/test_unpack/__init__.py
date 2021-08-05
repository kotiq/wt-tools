def stem(name):
    pos = name.rfind('.vromfs.bin')
    return name if pos == -1 else name[:pos]
