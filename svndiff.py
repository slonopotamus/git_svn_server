
def encode_int(i):
    s = chr(i % 128)
    i = i / 128

    while i > 0:
        s = chr(128 + i % 128) + s
        i = i / 128

    return s

def header():
    return 'SVN' + chr(0)

def encode_new(data):
    i = chr(128) + encode_int(len(data))

    w = encode_int(0)
    w += encode_int(0)
    w += encode_int(len(data))
    w += encode_int(len(i))
    w += encode_int(len(data))
    w += i

    w += data

    return w
