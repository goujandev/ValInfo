"""Generate assets/valinfo.ico - the red V mark, no image libraries needed."""

from __future__ import annotations

import struct
from pathlib import Path

SIZE = 64
BG = (0, 0, 0, 0)          # transparent
RED = (85, 70, 255, 255)   # BGRA


def inside_v(x: float, y: float) -> bool:
    """True if the pixel falls inside the V stroke."""
    # Two diagonal strokes meeting at the bottom centre.
    for x0, x1 in ((0.14, 0.50), (0.86, 0.50)):
        t = y  # 0 at the top, 1 at the bottom
        cx = x0 + (x1 - x0) * t
        if abs(x - cx) < 0.085 and 0.12 <= y <= 0.86:
            return True
    # The notch bar across the top of the wedge.
    return 0.40 <= x <= 0.60 and 0.20 <= y <= 0.28


def pixels() -> bytes:
    rows = []
    for row in range(SIZE):
        # BMP rows run bottom-up.
        y = (SIZE - 1 - row) / (SIZE - 1)
        line = bytearray()
        for column in range(SIZE):
            x = column / (SIZE - 1)
            line += bytes(RED if inside_v(x, y) else BG)
        rows.append(bytes(line))
    return b"".join(rows)


def build() -> bytes:
    data = pixels()
    # BITMAPINFOHEADER: height is doubled for the (empty) AND mask.
    header = struct.pack(
        "<IiiHHIIiiII", 40, SIZE, SIZE * 2, 1, 32, 0, len(data), 0, 0, 0, 0
    )
    mask = b"\x00" * (SIZE * SIZE // 8)
    image = header + data + mask

    icondir = struct.pack("<HHH", 0, 1, 1)
    entry = struct.pack(
        "<BBBBHHII", SIZE, SIZE, 0, 0, 1, 32, len(image), 6 + 16
    )
    return icondir + entry + image


if __name__ == "__main__":
    out = Path(__file__).resolve().parent.parent / "assets" / "valinfo.ico"
    out.parent.mkdir(exist_ok=True)
    out.write_bytes(build())
    print(f"wrote {out} ({out.stat().st_size} bytes)")
