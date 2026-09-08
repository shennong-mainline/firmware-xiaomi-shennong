# firmware-xiaomi-shennong

Device firmware for the Xiaomi 14 Pro (`shennong`, SM8650)  
Dumped from stock HyperOS(OS3.0.307)  

| Path | What |
|---|---|
| `lib/firmware/qcom/sm8650/gen70900_*.fw` + `gmu_gen70900.bin` + `zap.mbn` | Adreno 750 firmware|
| `lib/firmware/qcom/gen70900_*` | Symlinks; `msm` loads `qcom/<name>` first |
| `lib/firmware/ath12k/WCN7850/hw2.0/` | Working WiFi set: linux-firmware `amss`/`m3`/`board.bin`, Xiaomi `regdb.bin` and `board-n2.elf` |
| `lib/firmware/qca/hmtbtfw20.tlv` + `hmtnv20.bin` + `hmtnv20.b10f` + `hmtnv20.b112` | WCN7850 UART HCI (linux-firmware 2.0.1-00349) |

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
