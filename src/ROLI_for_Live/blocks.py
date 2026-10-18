"""Minimal ROLI BLOCKS SysEx helpers (protocol per WeAreROLI/roli_blocks_basics, ISC).

Only the messages this integration needs: serial dump request, config read/write,
and decoding of config updates and control-button events from the device.
"""

ROLI_HEADER = (0xF0, 0x00, 0x21, 0x10)
BLOCKS_PREFIX = ROLI_HEADER + (0x77,)
SERIAL_DUMP_REQUEST = ROLI_HEADER + (0x78, 0x3F, 0xF7)

# Message types, host -> device
MSG_DEVICE_COMMAND = 0x01
MSG_CONFIG = 0x10
# Device commands
CMD_BEGIN_API_MODE = 0x00
CMD_END_API_MODE = 0x02
CMD_PING = 0x03
# Config commands
CFG_SET = 0x00
CFG_REQUEST = 0x01
CFG_UPDATE = 0x04
# Message types, device -> host
DEV_PACKET_ACK = 0x02
DEV_CONFIG = 0x18
DEV_BUTTON_DOWN = 0x20
DEV_BUTTON_UP = 0x21
# Touch messages: bits after the type (time offset 5, index 5, x 12, y 12, z 8 [+ vx, vy, vz 8 each])
_TOUCH_BITS = 5 + 5 + 12 + 12 + 8
DEV_TOUCH_TYPES = {0x10: _TOUCH_BITS, 0x11: _TOUCH_BITS, 0x12: _TOUCH_BITS,
                   0x13: _TOUCH_BITS + 24, 0x14: _TOUCH_BITS + 24, 0x15: _TOUCH_BITS + 24}


def _checksum(data):
    c = len(data) & 0xFF
    for b in data:
        c = (c + (c * 2 + b)) & 0xFF
    return c & 0x7F


def _pack(fields):
    bits, n = 0, 0
    for value, width in fields:
        bits |= (value & ((1 << width) - 1)) << n
        n += width
    out = []
    while n > 0:
        out.append(bits & 0x7F)
        bits >>= 7
        n -= 7
    return out


def _packet(index, fields):
    payload = _pack(fields)
    return BLOCKS_PREFIX + (index & 0x7F,) + tuple(payload) + (_checksum(payload), 0xF7)


def device_command(command, index=0):
    return _packet(index, [(MSG_DEVICE_COMMAND, 7), (command, 9)])


def config_request(item, index=0):
    return _packet(index, [(MSG_CONFIG, 7), (CFG_REQUEST, 4), (0, 32), (item, 8)])


def config_set(item, value, index=0):
    return _packet(index, [(MSG_CONFIG, 7), (CFG_SET, 4), (item, 8), (value & 0xFFFFFFFF, 32)])


class _BitReader(object):
    def __init__(self, data):
        self.data = data
        self.pos = 0

    def remaining(self):
        return len(self.data) * 7 - self.pos

    def read(self, n):
        v = 0
        for i in range(n):
            byte, bit = divmod(self.pos, 7)
            v |= ((self.data[byte] >> bit) & 1) << i
            self.pos += 1
        return v


def _s32(v):
    return v - (1 << 32) if v >= (1 << 31) else v


def parse_device_packet(midi_bytes):
    """Yield ('config', item, value), ('button', id, is_down) and ('ack',) events from one BLOCKS packet."""
    if len(midi_bytes) < 9 or tuple(midi_bytes[:5]) != BLOCKS_PREFIX or not (midi_bytes[5] & 0x40):
        return
    payload = list(midi_bytes[6:-2])
    if _checksum(payload) != midi_bytes[-2]:
        return
    r = _BitReader(payload)
    if r.remaining() < 32:
        return
    r.read(32)  # packet timestamp
    while r.remaining() >= 7:
        t = r.read(7)
        if t == 0:
            return
        if t == DEV_CONFIG:
            if r.remaining() < 4:
                return
            cmd = r.read(4)
            if cmd == CFG_UPDATE and r.remaining() >= 8 + 96:
                item = r.read(8)
                value = _s32(r.read(32))
                r.read(64)  # min, max
                yield ('config', item, value)
            elif cmd == CFG_SET and r.remaining() >= 40:
                item = r.read(8)
                yield ('config', item, _s32(r.read(32)))
            else:
                return
        elif t == DEV_PACKET_ACK:
            if r.remaining() < 10:
                return
            r.read(10)
            yield ('ack',)
        elif t in (DEV_BUTTON_DOWN, DEV_BUTTON_UP):
            if r.remaining() < 17:
                return
            r.read(5)  # timestamp offset
            yield ('button', r.read(12), t == DEV_BUTTON_DOWN)
        elif t in DEV_TOUCH_TYPES:
            if r.remaining() < DEV_TOUCH_TYPES[t]:
                return
            r.read(DEV_TOUCH_TYPES[t])
        else:
            return  # unknown message type: stop parsing this packet


def parse_serial(midi_bytes):
    """Return the 16-char serial from a 0x78 serial dump reply, or None."""
    if tuple(midi_bytes[:5]) != ROLI_HEADER + (0x78,):
        return None
    data = bytes(midi_bytes)
    i = data.find(b'48:B6:20:')
    if i < 0 or len(data) < i + 17 + 16:
        return None
    return data[i + 17:i + 33].decode('ascii', 'replace')
