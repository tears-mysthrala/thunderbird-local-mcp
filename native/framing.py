import json
import struct

MAX_FRAME = 1024 * 1024

def encode(value):
    raw = json.dumps(value, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    if len(raw) > MAX_FRAME:
        raise ValueError('FRAME_TOO_LARGE')
    return struct.pack('<I', len(raw)) + raw

def receive(read):
    def exact(size):
        chunks = bytearray()
        while len(chunks) < size:
            part = read(size - len(chunks))
            if not part:
                raise EOFError()
            chunks.extend(part)
        return bytes(chunks)
    size = struct.unpack('<I', exact(4))[0]
    if not 0 < size <= MAX_FRAME:
        raise ValueError('FRAME_TOO_LARGE')
    value = json.loads(exact(size).decode('utf-8'))
    if not isinstance(value, dict):
        raise ValueError('INVALID_FRAME')
    return value
