#!/usr/bin/env python3
"""Extract NXP SN220 download payload from libsn220u_fw.so.

The HyperOS blob is an aarch64 ELF that exports:

  gphDnldNfc_DlSequence  - concatenated download WRITE frames
  gphDnldNfc_DlSeqSz     - little-endian uint32 length of that sequence

Each WRITE frame is [BE16 payload-length][payload...]. The kernel nxp-nci
driver sends GET_VERSION / FORCE / RESET itself; this script only dumps the
raw sequence the HAL would pass to phDnldNfc_Write.

Host architecture does not matter: the .so is parsed as ELF, never dlopened.
"""

from __future__ import annotations

import argparse
import struct
import sys
from pathlib import Path

PT_LOAD = 1
SHT_DYNSYM = 11
SHT_SYMTAB = 2
STT_OBJECT = 1
STT_NOTYPE = 0

SEQ_SYM = "gphDnldNfc_DlSequence"
SZ_SYM = "gphDnldNfc_DlSeqSz"


def die(msg: str) -> None:
    print(f"extract-nxp-sn220-fw: {msg}", file=sys.stderr)
    sys.exit(1)


def parse_elf(blob: bytes) -> tuple[int, int]:
    """Return (file_offset, size) of gphDnldNfc_DlSequence."""
    if blob[:4] != b"\x7fELF":
        die("not an ELF file")
    ei_class, ei_data = blob[4], blob[5]
    if ei_class != 2 or ei_data != 1:
        die("expected ELF64 little-endian")

    e_phoff, e_shoff = struct.unpack_from("<QQ", blob, 32)
    e_phentsize, e_phnum = struct.unpack_from("<HH", blob, 54)
    e_shentsize, e_shnum, e_shstrndx = struct.unpack_from("<HHH", blob, 58)

    phdrs = []
    for i in range(e_phnum):
        off = e_phoff + i * e_phentsize
        p_type, _p_flags, p_offset, p_vaddr, _p_paddr, p_filesz, p_memsz, _p_align = (
            struct.unpack_from("<IIQQQQQQ", blob, off)
        )
        if p_type == PT_LOAD:
            phdrs.append((p_vaddr, p_memsz, p_offset, p_filesz))

    def vaddr_to_off(vaddr: int) -> int:
        for p_vaddr, p_memsz, p_offset, p_filesz in phdrs:
            if p_vaddr <= vaddr < p_vaddr + p_memsz:
                rel = vaddr - p_vaddr
                if rel >= p_filesz:
                    die(f"symbol vaddr {vaddr:#x} is not in file")
                return p_offset + rel
        die(f"no PT_LOAD covers vaddr {vaddr:#x}")

    shstr_off = e_shoff + e_shstrndx * e_shentsize
    shstr_sh_offset, shstr_sh_size = struct.unpack_from("<QQ", blob, shstr_off + 24)

    def sh_name(sh_name_off: int) -> str:
        start = shstr_sh_offset + sh_name_off
        end = blob.find(b"\x00", start, shstr_sh_offset + shstr_sh_size)
        return blob[start:end].decode("ascii", "replace")

    dynsym = dynstr = None
    for i in range(e_shnum):
        off = e_shoff + i * e_shentsize
        name_off, sh_type = struct.unpack_from("<II", blob, off)
        sh_offset, sh_size, _sh_link, _sh_info, _sh_addralign, sh_entsize = (
            struct.unpack_from("<QQIIQQ", blob, off + 24)
        )
        name = sh_name(name_off)
        if sh_type == SHT_DYNSYM and name in (".dynsym", ".symtab") or (
            sh_type == SHT_DYNSYM and dynsym is None
        ):
            dynsym = (sh_offset, sh_size, sh_entsize or 24)
        if name == ".dynstr":
            dynstr = (sh_offset, sh_size)
        if sh_type == SHT_SYMTAB and dynsym is None:
            dynsym = (sh_offset, sh_size, sh_entsize or 24)
        if name == ".strtab" and dynstr is None:
            dynstr = (sh_offset, sh_size)

    if not dynsym or not dynstr:
        die("missing .dynsym / .dynstr")

    sym_off, sym_size, sym_entsize = dynsym
    str_off, str_size = dynstr
    found: dict[str, tuple[int, int]] = {}
    for so in range(sym_off, sym_off + sym_size, sym_entsize):
        st_name, st_info, _st_other, _st_shndx, st_value, st_size = struct.unpack_from(
            "<IBBHQQ", blob, so
        )
        if not st_name:
            continue
        nend = blob.find(b"\x00", str_off + st_name, str_off + str_size)
        name = blob[str_off + st_name : nend].decode("ascii", "replace")
        if name in (SEQ_SYM, SZ_SYM):
            found[name] = (st_value, st_size)

    if SEQ_SYM not in found:
        die(f"missing symbol {SEQ_SYM}")
    seq_vaddr, seq_st_size = found[SEQ_SYM]
    seq_off = vaddr_to_off(seq_vaddr)

    size = seq_st_size
    if SZ_SYM in found:
        sz_off = vaddr_to_off(found[SZ_SYM][0])
        (sz_val,) = struct.unpack_from("<I", blob, sz_off)
        if size and sz_val != size:
            die(f"{SZ_SYM}={sz_val:#x} != {SEQ_SYM} st_size {size:#x}")
        size = sz_val

    if size == 0 or seq_off + size > len(blob):
        die(f"invalid sequence size {size:#x} at file offset {seq_off:#x}")
    return seq_off, size


def walk_frames(data: bytes) -> tuple[int, int]:
    """Return (frame_count, max_payload). Reject truncated/oversize headers."""
    i = 0
    n = 0
    max_pld = 0
    while i < len(data):
        if i + 2 > len(data):
            die("truncated BE16 length at end of sequence")
        (hdr,) = struct.unpack_from(">H", data, i)
        pld = hdr & 0x03FF
        if pld == 0:
            die(f"zero-length frame at offset {i:#x}")
        if i + 2 + pld > len(data):
            die(
                f"frame at {i:#x} length {pld} overruns sequence "
                f"({len(data)} bytes)"
            )
        max_pld = max(max_pld, pld)
        i += 2 + pld
        n += 1
    if i != len(data):
        die("sequence length is not an exact frame walk")
    return n, max_pld


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("so", type=Path, help="path to libsn220u_fw.so")
    ap.add_argument("out", type=Path, help="output libsn220u_fw.bin")
    args = ap.parse_args()

    blob = args.so.read_bytes()
    seq_off, size = parse_elf(blob)
    data = blob[seq_off : seq_off + size]
    nframes, max_pld = walk_frames(data)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes(data)

    print(
        f"extracted {SEQ_SYM}: {size} bytes, {nframes} WRITE frames, "
        f"max payload {max_pld} from {args.so} offset {seq_off:#x} -> {args.out}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
