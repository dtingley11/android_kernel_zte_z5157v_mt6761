#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-only
set -euo pipefail
ulimit -c 0

if [[ $# != 2 ]]; then
    echo "Usage: ANDROID_NDK_HOME=/path/to/ndk $0 STOCK_ZIMAGE OUT_DIR" >&2
    exit 2
fi
: "${ANDROID_NDK_HOME:?Set ANDROID_NDK_HOME to an Android NDK installation}"
repo_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../../.." && pwd)
stock_kernel=$(realpath -- "$1")
out_dir=$(realpath -m -- "$2")
mkdir -p -- "$out_dir"

python3 - "$stock_kernel" "$out_dir/stock-Image" <<'PY'
import hashlib, pathlib, re, sys, zlib
blob = pathlib.Path(sys.argv[1]).read_bytes()
expected = '9f29e359222a273c6d10daa85a929cdc3b85bda414c95a435f1bcb7f8b25594a'
if hashlib.sha256(blob).hexdigest() != expected:
    raise SystemExit('This test only supports the documented stock Z5157V kernel revision')
for match in re.finditer(b'\x1f\x8b\x08', blob):
    try:
        image = zlib.decompress(blob[match.start():], 31)
    except zlib.error:
        continue
    if len(image) == 23502848:
        pathlib.Path(sys.argv[2]).write_bytes(image)
        break
else:
    raise SystemExit('Stock kernel decompression failed')
PY

"$ANDROID_NDK_HOME/toolchains/llvm/prebuilt/linux-x86_64/bin/armv7a-linux-androideabi21-clang" \
    -marm -static -fno-emulated-tls -O2 -Werror \
    -DCONFIG_ZTE_LCDBL_I2C_CTRL_VSP_VSN -DCONFIG_ZTE_LCD_COMMON_FUNCTION \
    -I"$repo_dir/tools/testing/z5157v-panel/include" \
    -I"$repo_dir/drivers/misc/mediatek/lcm/inc" \
    "$repo_dir/tools/testing/z5157v-panel/compare.c" -o "$out_dir/compare"
qemu-arm "$out_dir/compare" "$out_dir/stock-Image"
