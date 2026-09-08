#!/usr/bin/env python3
"""Xiaomi kiwi (WCN7850) WiFi files for ath12k.

Stock HyperOS keeps the WCN7850 image under modem/image/kiwi. DumprX unpacks
that to ~/android/DumprX/out/modem/image/kiwi.

ath12k (WCN7850/hw2.0) only requests:

  amss.bin  m3.bin  board-2.bin  board.bin  regdb.bin

linux-firmware already supplies amss.bin, m3.bin, board-2.bin, and the
board.bin fallback. Do not replace those with kiwi/amss.bin or kiwi/amss20.bin;
mainline ath12k boots WLAN.HMT.1.1.c7 from linux-firmware, not HyperOS AMSS.

The only Xiaomi kiwi file ath12k will load by name is regdb.bin (API-1 after
board-2.bin's REGDB IE). kiwi/bd_n2.elf is the phone BDF, but ath12k never
requests board-n2.elf, so this script does not install it.

Commands:
  dump     copy DumprX kiwi/regdb_xiaomi.bin -> blobs/kiwi/
  install  copy blobs/kiwi/regdb_xiaomi.bin -> package dest/regdb.bin
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

REGDB_NAME = "regdb_xiaomi.bin"


def die(msg: str) -> None:
    print(f"kiwi-wifi-fw: {msg}", file=sys.stderr)
    sys.exit(1)


def default_kiwi() -> Path:
    env = os.environ.get("DUMPRX_KIWI") or os.environ.get("DUMPRX_OUT")
    if env:
        p = Path(env).expanduser()
        if p.name != "kiwi":
            cand = p / "modem" / "image" / "kiwi"
            if cand.is_dir():
                return cand
        return p
    return Path.home() / "android" / "DumprX" / "out" / "modem" / "image" / "kiwi"


def copy_regdb(src: Path, dest: Path) -> None:
    if not src.is_file():
        die(f"missing {src}")
    data = src.read_bytes()
    if len(data) < 64:
        die(f"{src} is too small ({len(data)} bytes)")
    if data[:4] == b"\x7fELF":
        die(f"{src} looks like ELF; expected a raw regdb")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    print(f"kiwi-wifi-fw: {src} ({len(data)} bytes) -> {dest}")


def cmd_dump(args: argparse.Namespace) -> int:
    kiwi = args.kiwi if args.kiwi else default_kiwi()
    kiwi = kiwi.expanduser().resolve()
    if not kiwi.is_dir():
        die(f"kiwi dir not found: {kiwi}")

    skipped = [
        ("amss.bin / amss20.bin", "mainline ath12k uses linux-firmware AMSS"),
        ("phy_ucode.elf", "mainline ath12k uses linux-firmware m3.bin"),
        ("bd_n2.elf / bdwlan.*", "ath12k never requests board-n2.elf"),
    ]
    for name, why in skipped:
        print(f"kiwi-wifi-fw: skip {name} ({why})")

    src = kiwi / REGDB_NAME
    dest = args.dest.expanduser()
    copy_regdb(src, dest)
    return 0


def cmd_install(args: argparse.Namespace) -> int:
    copy_regdb(args.src.expanduser(), args.dest.expanduser())
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    dump = sub.add_parser("dump", help="copy DumprX kiwi regdb into blobs/kiwi/")
    dump.add_argument(
        "--kiwi",
        type=Path,
        help="DumprX kiwi dir (default ~/android/DumprX/out/modem/image/kiwi)",
    )
    dump.add_argument(
        "dest",
        nargs="?",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "blobs" / "kiwi" / REGDB_NAME,
        help="destination path (default repo blobs/kiwi/regdb_xiaomi.bin)",
    )
    dump.set_defaults(func=cmd_dump)

    inst = sub.add_parser("install", help="install blobs regdb as ath12k regdb.bin")
    inst.add_argument("src", type=Path, help="blobs/kiwi/regdb_xiaomi.bin")
    inst.add_argument("dest", type=Path, help="output regdb.bin")
    inst.set_defaults(func=cmd_install)

    args = ap.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
