import argparse
import sys
from collections import namedtuple

Patch = namedtuple("Patch", "line off val size var")


def ident_byte(b):
  return (48 <= b <= 57) or (65 <= b <= 90) or (97 <= b <= 122) or b == 95


def find_base(buf, name):
  pat = name.encode("ascii")
  i = 0

  while True:
    j = buf.find(pat, i)
    if j < 0:
      return -1

    i = j + 1
    end = j + len(pat)

    if buf[end : end + 1] != b"\x00":
      continue

    if j >= 1 and ident_byte(buf[j - 1]):
      continue

    return end + 1


def parse_config(text):
  out = []

  for n, raw in enumerate(text.splitlines(), 1):
    line = raw.strip()

    if not line or line.startswith("#"):
      continue

    fields = line.split()

    if len(fields) != 4:
      raise ValueError(f"line {n}: expected 4 fields, got {len(fields)}: {raw!r}")

    off, val, size, var = fields

    try:
      off = int(off, 16)
      val = int(val, 16)
      size = int(size, 0)
    except ValueError as e:
      raise ValueError(f"line {n}: bad number ({e}): {raw!r}") from e

    if size < 1 or size > 8:
      raise ValueError(f"line {n}: size {size} out of range 1..8")

    if off < 0:
      raise ValueError(f"line {n}: offset {off} is negative")

    if val < 0:
      raise ValueError(f"line {n}: value {val} is negative")

    if val >= (1 << (size * 8)):
      raise ValueError(f"line {n}: value 0x{val:X} doesn't fit in {size} byte(s)")

    out.append(Patch(n, off, val, size, var))

  return out


def main():
  ap = argparse.ArgumentParser(description="patch nvram binary from a text config file")
  ap.add_argument("bin", help="input nvram binary")
  ap.add_argument("cfg", help="config file")
  ap.add_argument("-o", "--out", help="patched binary output, required unless -d")
  ap.add_argument(
    "-d", "--dry", action="store_true", help="resolve and report, write nothing"
  )
  ap.add_argument("-v", "--verbose", action="store_true", help="print every write")

  a = ap.parse_args()

  if not a.dry and not a.out:
    ap.error("-o/--out is required unless -d/--dry is given")

  try:
    with open(a.cfg, "r", encoding="utf-8", errors="replace") as f:
      patches = parse_config(f.read())

    with open(a.bin, "rb") as f:
      buf = bytearray(f.read())
  except OSError as e:
    sys.exit(f"can't read {e.filename}: {e.strerror}")
  except ValueError as e:
    sys.exit(str(e))

  bases = {}

  for p in patches:
    if p.var in bases:
      continue

    base = find_base(buf, p.var)

    if base < 0:
      sys.exit(f"var-store {p.var!r} not found in {a.bin}")

    bases[p.var] = base

    if a.verbose or a.dry:
      print(f"base {p.var:<10} = 0x{base:X}")

  changed = 0

  for p in patches:
    pos = bases[p.var] + p.off

    if pos + p.size > len(buf):
      sys.exit(
        f"line {p.line}: write at 0x{pos:X}+{p.size} exceeds image size 0x{len(buf):X}"
      )

    new = p.val.to_bytes(p.size, "little")
    old = bytes(buf[pos : pos + p.size])

    if old != new:
      changed += 1

    if a.verbose or a.dry:
      mark = "" if old != new else "  (no change)"
      print(
        f"line {p.line}: {p.var}+0x{p.off:X} @0x{pos:X}  "
        f"{old.hex()} -> {new.hex()}{mark}"
      )

    if not a.dry:
      buf[pos : pos + p.size] = new

  if a.dry:
    print(f"dry-run: {len(patches)} patches, {changed} would change")
    return

  with open(a.out, "wb") as f:
    f.write(buf)

  print(f"wrote {a.out}: {len(patches)} patches, {changed} changed")


if __name__ == "__main__":
  main()
