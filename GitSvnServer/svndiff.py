
import md5
import sys
import zlib


def encode_int(i):
    s = chr(i % 128)
    i = i / 128

    while i > 0:
        s = chr(128 + i % 128) + s
        i = i / 128

    return s


def encode_new(data, version = 0):
    i = chr(128) + encode_int(len(data))

    tv_len = len(data)

    if version == 1:
        i = encode_int(len(i)) + i
        zdata = zlib.compress(data)
        if len(zdata) >= len(data):
            zdata = data
        data = encode_int(len(data)) + zdata

    w = encode_int(0)
    w += encode_int(0)
    w += encode_int(tv_len)
    w += encode_int(len(i))
    w += encode_int(len(data))
    w += i

    w += data

    return w


class Encoder (object):
    def __init__(self, source, version=0, original=None):
        self.version = version
        self.source = source
        self.original = original
        self.sent_header = False
        self.src_offset = 0
        self.orig_offset = 0
        self.complete = False
        self.chunk_size = 1024 * 1024
        self.md5 = md5.new()

    def header(self):
        return 'SVN%s' % chr(self.version)

    def get_md5(self):
        return self.md5.hexdigest()

    def get_chunk(self):
        if self.complete:
            return None

        if not self.sent_header:
            self.sent_header = True
            return self.header()

        if self.original is None:
            data = self.source.read(self.chunk_size)
            if len(data) < self.chunk_size:
                self.complete = True
            if len(data) == 0:
                return None
            self.src_offset += len(data)
            self.md5.update(data)
            return encode_new(data, self.version)

        print >> sys.stderr, "not implemented yet"
        sys.exit(1)

        return ""


def get_svndiff_int(data):
    if len(data) == 0:
        return None, data

    value = ord(data[0]) & 0x7f
    i = 1

    while i < len(data) and (ord(data[i-1]) & 0x80) != 0:
        value = (value << 7) + (ord(data[i]) & 0x7f)
        i += 1

    if i >= len(data) and (ord(data[i-1]) & 0x80) != 0:
        return None, data

    return value, data[i:]


def get_svndiff_instructions(data):
    instructions = []

    while len(data) > 0:
        b = ord(data[0])
        data = data[1:]
        i = (b & 0xc0) >> 6
        l = (b & 0x3f)
        if l == 0:
            l, data = get_svndiff_int(data)
        o = None
        if i == 0 or i == 1:
            o, data = get_svndiff_int(data)
        instructions.append((i, l, o))

    return instructions


def error(msg):
    print >> sys.stderr, "svndiff: %s" % msg


header_order = ['src_offset', 'src_len', 'tgt_len', 'instruct_len',
                'new_data_len']
class Window (object):
    def __init__(self, version):
        self.header = []
        for i in header_order:
            self.header.append(None)
        self.next_header = 0
        self.instruction_data = ""
        self.new_data = ""
        self.version = version

    def h(self, name):
        return self.header[header_order.index(name)]

    def complete(self):
        if self.next_header < len(header_order):
            return False

        if len(self.instruction_data) < self.h('instruct_len'):
            return False

        if len(self.new_data) < self.h('new_data_len'):
            return False

        return True

    def feed(self, in_data):
        data = in_data

        while self.next_header < len(header_order):
            i, data = get_svndiff_int(data)
            if i is None:
                return data

            self.header[self.next_header] = i
            self.next_header += 1

        ilen = self.h('instruct_len') - len(self.instruction_data)
        if ilen > 0:
            self.instruction_data += data[:ilen]
            data = data[ilen:]

        dlen = self.h('new_data_len') - len(self.new_data)
        if dlen > 0:
            self.new_data += data[:dlen]
            data = data[dlen:]

        return data

    def decode_data(self, idata):
        if self.version == 0 or len(idata) == 0:
            return idata

        orig_len, data = get_svndiff_int(idata)

        if len(data) == orig_len:
            return data

        decomp_data = zlib.decompress(data)

        if len(decomp_data) != orig_len:
            error('zlib decompress failed!')
            # TODO: need to propogate this error up in a nicer manner
            sys.exit(1)

        return decomp_data

    def apply(self, source, target):
        src_offset = self.h('src_offset')
        src_len = self.h('src_len')
        tgt_len = self.h('tgt_len')
        instruct_len = self.h('instruct_len')
        new_data_len = self.h('new_data_len')

        instruction_data = self.decode_data(self.instruction_data)
        instructions = get_svndiff_instructions(instruction_data)

        new_data = self.decode_data(self.new_data)

        if source.tell() < src_offset:
            source.read(src_offset - source.tell())
        source_view = source.read(src_len)

        target_view = ""

        for i, l, o in instructions:
            if i == 0:
                # Copy from source view
                target_view += source_view[o:o + l]

            elif i == 1:
                # Copy from target view
                for j in range(o, o + l):
                    target_view += target_view[j]

            elif i == 2:
                # Copy from new data
                target_view += new_data[:l]
                new_data = new_data[l:]

            else:
                error('Invalid svndiff instruction: %d' % i)
                return ""

        if len(target_view) != tgt_len:
            error('Failed to apply svndiff correctly')
            error('  length should be %d, not %d' % (tgt_len, len(target_view)))
            # TODO: we ought to raise this as an error somehow, not die ...
            sys.exit(1)

        target.write(target_view)

class Decoder (object):
    def __init__(self, source, target):
        self.source = source
        self.target = target
        self.seen_header = False
        self.data = ""
        self.window = None
        self.diffversion = 0

    def check_header(self):
        if self.data[0:3] != 'SVN':
            error('Invalid svndiff data')

        version = ord(self.data[3])
        if version > 1:
            error('Invalid svndiff version: %d' % version)
            # TODO: we ought to raise this as an error somehow, not die ...
            sys.exit(1)

        self.diffversion = version
        print "svndiff%d" % version

        self.data = self.data[4:]
        self.seen_header = True

    def feed(self, data):
        old_len = len(self.data)

        self.data += data

        if len(self.data) == 0:
            return

        if not self.seen_header:
            self.check_header()

        if len(self.data) == 0:
            return

        if self.window is None:
            self.window = Window(self.diffversion)

        while len(self.data) != old_len:
            self.data = self.window.feed(self.data)
            old_len = len(self.data)

            if self.window.complete():
                self.window.apply(self.source, self.target)
                self.window = None

    def complete(self):
        if self.window is None:
            return

        self.window.feed(self.data)

        if not self.window.complete():
            error("window should be complete now!")

        self.window.apply(self.source, self.target)
