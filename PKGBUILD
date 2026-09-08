# Maintainer: kmiit <kmiit@foxmail.com>
pkgname=firmware-xiaomi-shennong
pkgver=20260906
pkgrel=1
pkgdesc="Device firmware for Xiaomi 14 Pro (shennong / SM8650)"
url="https://github.com/shennong-mainline/firmware-xiaomi-shennong"
arch=('any')
license=('custom')
options=('!strip' '!emptydirs' '!debug' '!lto')
provides=('linux-firmware-ath12k-wcn7850')
conflicts=('linux-firmware-atheros')

package() {
	install -d "$pkgdir/usr/lib/firmware"
	cp -a "$startdir/lib/firmware/." "$pkgdir/usr/lib/firmware/"
	install -d "$pkgdir/usr/share/licenses/$pkgname"
	if [ -d "$startdir/LICENSES" ]; then
		cp -a "$startdir/LICENSES/." "$pkgdir/usr/share/licenses/$pkgname/"
	fi
}
