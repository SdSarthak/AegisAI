"""Generate AEGIS Guard extension icons (16x16, 48x48)."""
import base64
import struct
import zlib
import os

OUT = os.path.join(os.path.dirname(__file__), "icons")
os.makedirs(OUT, exist_ok=True)

def png_chunk(chunk_type, data):
    payload = chunk_type + data
    return struct.pack(">I", len(data)) + payload + struct.pack(">I", zlib.crc32(payload) & 0xffffffff)

def make_png(w, h, r, g, b):
    def raw():
        for y in range(h):
            yield b'\x00'
            for x in range(w):
                yield bytes([r, g, b])
    raw_data = b''.join(raw())
    compressed = zlib.compress(raw_data, 9)
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    signature = b'\x89PNG\r\n\x1a\n'
    chunks = [
        png_chunk(b'IHDR', ihdr),
        png_chunk(b'IDAT', compressed),
        png_chunk(b'IEND', b''),
    ]
    return signature + b''.join(chunks)

# Neutral gray, green, red, yellow (loading), orange (offline)
palette = {
    "icon": (80, 88, 100),
    "icon-green": (63, 185, 80),
    "icon-red": (248, 81, 73),
    "icon-yellow": (210, 153, 34),
    "icon-orange": (230, 120, 50),
}

for name, (r, g, b) in palette.items():
    for size in [16, 48]:
        fname = f"{name}{size}.png"
        path = os.path.join(OUT, fname)
        with open(path, "wb") as f:
            f.write(make_png(size, size, r, g, b))
        print(f"Wrote {path}")
# icon128 for manifest
if "icon" in palette:
    r, g, b = palette["icon"]
    with open(os.path.join(OUT, "icon128.png"), "wb") as f:
        f.write(make_png(128, 128, r, g, b))
    print("Wrote icons/icon128.png")
