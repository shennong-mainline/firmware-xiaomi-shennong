# firmware-xiaomi-shennong

Device firmware for the Xiaomi 14 Pro (`shennong`, SM8650).

| Path | What |
|---|---|
| `lib/firmware/qcom/sm8650/gen70900_*.fw` + `gmu_gen70900.bin` + `zap.mbn` | Adreno 750 firmware from HyperOS |
| `lib/firmware/qcom/gen70900_*` | Symlinks; `msm` loads `qcom/<name>` first |
| `lib/firmware/ath12k/WCN7850/hw2.0/{amss,m3,board-2,board}.bin` | linux-firmware WCN7850 set (`WLAN.HMT.1.1.c7`). Do not replace with HyperOS `kiwi/amss.bin`. |
| `blobs/kiwi/regdb_xiaomi.bin` → `ath12k/WCN7850/hw2.0/regdb.bin` | Xiaomi kiwi regdb. Package build copies it from `blobs/`. Refresh with `scripts/kiwi-wifi-fw.py dump` from `~/android/DumprX/out/modem/image/kiwi`. |
| `lib/firmware/qca/hmtbtfw20.tlv` + `hmtnv20.bin` + `hmtnv20.b10f` + `hmtnv20.b112` | WCN7850 UART HCI (linux-firmware 2.0.1-00349) |
| `blobs/nxp/libsn220u_fw.so` → `/usr/lib/firmware/nxp/libsn220u_fw.bin` | SN220 NFC RAM firmware. Package build extracts `gphDnldNfc_DlSequence` from the HyperOS `.so`. |

`board-n2.elf` is **not** shipped. It is `modem/image/kiwi/bd_n2.elf` in DumprX, but ath12k never requests that filename (only `board-2.bin` then `board.bin`). Mixing the Xiaomi BDF with linux-firmware AMSS is untested; WiFi associates with the linux-firmware `board.bin` fallback.

CI builds an `arch=any` pacman package and publishes it as a GitHub Release
that is also a pacman repo:

```
[shennong]
SigLevel = Optional TrustAll
Server = https://github.com/shennong-mainline/firmware-xiaomi-shennong/releases/latest/download
```

```
pacman -Sy firmware-xiaomi-shennong
```

The package conflicts with `linux-firmware-atheros` so WCN7850 files are not
owned twice.

Refresh the kiwi blob after a new HyperOS dump:

```
python3 scripts/kiwi-wifi-fw.py dump
```
