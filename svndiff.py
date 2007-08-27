
def encode_int(i):
    s = chr(i % 128)
    i = i / 128

    while i > 0:
        s = chr(128 + i % 128) + s
        i = i / 128

    return s

def encode_new_file(data):
    res = ['SVN' + chr(0)]

    i = chr(128) + encode_int(len(data))

    w = encode_int(0)
    w += encode_int(0)
    w += encode_int(len(data))
    w += encode_int(len(i))
    w += encode_int(len(data))
    w += i

    w += data

    res.append(w)

    return res
