#!/usr/bin/env python3
"""Build a reversible Z5157V root module restoring ADB install and uninstall."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import zipfile
import zlib

CLASS = 'Lcom/android/server/pm/PackageManagerShellCommand;'
ORIGINAL_SHA256 = '2f17fc13a613d8db466d7f0d48e37b3eba53e112e3526c3c327ecd6f127173e2'


def uleb(data, offset):
    result = 0
    for shift in range(0, 35, 7):
        byte = data[offset]; offset += 1
        result |= (byte & 127) << shift
        if not byte & 128:
            return result, offset
    raise ValueError('Malformed DEX ULEB128')


def patch_dex(original):
    data = bytearray(original)
    if data[:4] != b'dex\n' or len(data) != struct.unpack_from('<I', data, 32)[0]:
        raise ValueError('Invalid DEX header')
    # This exact OEM JAR has stale DEX SHA-1 signatures but valid Adler checksums.
    # The complete input JAR is pinned above; regenerate both fields after patching.
    if zlib.adler32(data[12:]) != struct.unpack_from('<I', data, 8)[0]:
        raise ValueError('Invalid original DEX Adler checksum')
    def table(offset, width):
        count, start = struct.unpack_from('<II', data, offset)
        return [start + i * width for i in range(count)]
    strings = []
    for item in table(56, 4):
        start = struct.unpack_from('<I', data, item)[0]
        _, start = uleb(data, start)
        strings.append(bytes(data[start:data.index(0, start)]).decode('utf-8', errors='replace'))
    types = [strings[struct.unpack_from('<I', data, item)[0]] for item in table(64, 4)]
    methods = []
    for item in table(88, 8):
        cls, proto, name = struct.unpack_from('<HHI', data, item)
        methods.append((types[cls], strings[name]))
    targets = {methods.index((CLASS, name)): name for name in ('runInstall', 'runUninstall')}
    check = methods.index((CLASS, 'isUserBuild'))
    classdata = None
    for item in table(96, 32):
        if types[struct.unpack_from('<I', data, item)[0]] == CLASS:
            classdata = struct.unpack_from('<I', data, item + 24)[0]
    if not classdata:
        raise ValueError('PackageManagerShellCommand class missing')
    offset = classdata; counts = []
    for _ in range(4):
        count, offset = uleb(data, offset); counts.append(count)
    for _ in range(counts[0] + counts[1]):
        _, offset = uleb(data, offset); _, offset = uleb(data, offset)
    code_offsets = {}
    for count in counts[2:]:
        index = 0
        for _ in range(count):
            delta, offset = uleb(data, offset); index += delta
            _, offset = uleb(data, offset); code_offset, offset = uleb(data, offset)
            if index in targets: code_offsets[targets[index]] = code_offset
    if set(code_offsets) != set(targets.values()):
        raise ValueError('Install/uninstall command code missing')
    changes = []
    for name, code in code_offsets.items():
        units = struct.unpack_from('<I', data, code + 12)[0]
        start, end = code + 16, code + 16 + 2 * units
        matches = []
        for pos in range(start, end - 14, 2):
            # invoke-direct or invoke-direct/range isUserBuild; move-result vN.
            if data[pos] in (0x70, 0x76) and struct.unpack_from('<H', data, pos + 2)[0] == check and data[pos + 6] == 0x0a:
                register = data[pos + 7]
                # OEM dex places const/4 vReturn, 1 between result and branch.
                if (register < 16 and data[pos + 8] == 0x12 and data[pos + 9] >> 4 == 1
                        and data[pos + 10] == 0x38 and data[pos + 11] == register
                        and struct.unpack_from('<h', data, pos + 12)[0] == 3
                        and data[pos + 14] == 0x0f and data[pos + 15] == data[pos + 9] & 15):
                    matches.append((pos + 6, register))
        if len(matches) != 1:
            raise ValueError(f'Expected one build-type check in {name}, found {len(matches)}')
        pos, register = matches[0]
        before = bytes(data[pos:pos + 2])
        # Same-size instruction: move-result vN -> const/4 vN, 0.
        # The original permission, signature and session checks remain in place.
        data[pos:pos + 2] = bytes([0x12, register])
        changes.append({'method': CLASS + '->' + name + '()I', 'dex_offset': pos,
                        'before': before.hex(), 'after': bytes(data[pos:pos + 2]).hex()})
    data[12:32] = hashlib.sha1(data[32:]).digest()
    struct.pack_into('<I', data, 8, zlib.adler32(data[12:]))
    changed = [i for i in range(32, len(data)) if data[i] != original[i]]
    expected = {x['dex_offset'] for x in changes}
    assert set(changed) == expected
    return bytes(data), changes


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--services', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args(); a.out.mkdir(parents=True, exist_ok=True)
    original = a.services.read_bytes()
    if hashlib.sha256(original).hexdigest() != ORIGINAL_SHA256:
        raise SystemExit('services.jar differs from the reviewed Z5157V Android 10 firmware')
    jar = a.out / 'services-patched.jar'
    with zipfile.ZipFile(a.services) as source, zipfile.ZipFile(jar, 'w') as target:
        for info in source.infolist():
            content = source.read(info.filename)
            if info.filename == 'classes.dex': content, changes = patch_dex(content)
            target.writestr(info, content)
    with zipfile.ZipFile(jar) as patched, zipfile.ZipFile(a.services) as source:
        assert patched.testzip() is None
        assert patched.namelist() == source.namelist()
        for name in source.namelist():
            if name != 'classes.dex': assert source.read(name) == patched.read(name)
    digest = hashlib.sha256(jar.read_bytes()).hexdigest()
    report = {'original_services_sha256': ORIGINAL_SHA256, 'patched_services_sha256': digest,
              'changes': changes, 'device_applied': False, 'reboot_tested': False}
    prop = '''id=zte_adb_install_restore
name=Z5157V ADB Install and Uninstall Restore
version=2
versionCode=2
author=dtingley11
description=Restores ADB installation and uninstallation on Z5157V Android 10.
'''
    customize = '''#!/system/bin/sh
SKIPUNZIP=0
[ "$(getprop ro.build.version.sdk)" = 29 ] || abort "Requires the reviewed Android 10 firmware"
current=$(sha256sum /system/framework/services.jar)
current=${current%% *}
case "$current" in
  @ORIGINAL@|9b2594cb6959d41acef5c32153d94563a4cd08e7b046a3f87c77154267641e4b|@PATCHED@) ;;
  *) abort "services.jar differs from the reviewed Z5157V firmware" ;;
esac
set_perm "$MODPATH/services.jar" 0 0 0644 u:object_r:system_file:s0
set_perm "$MODPATH/post-fs-data.sh" 0 0 0755
ui_print "ADB install/uninstall checks patched; reboot to apply"
'''.replace('@ORIGINAL@', ORIGINAL_SHA256).replace('@PATCHED@', digest)
    boot = '''#!/system/bin/sh
# Bind only this framework file; removal/disable restores it on the next boot.
MODDIR=${0%/*}
[ -f "$MODDIR/disable" ] && exit 0
chcon u:object_r:system_file:s0 "$MODDIR/services.jar" || exit 1
mount -o bind "$MODDIR/services.jar" /system/framework/services.jar
'''
    archive = a.out / 'Z5157V-ADB-Install-Uninstall-Restore-v2.zip'
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as stream:
        for name, value, mode in [('module.prop', prop.encode(), 0o644), ('customize.sh', customize.encode(), 0o755),
                                  ('post-fs-data.sh', boot.encode(), 0o755), ('services.jar', jar.read_bytes(), 0o644),
                                  ('PATCH.json', (json.dumps(report, indent=2)+'\n').encode(), 0o644)]:
            entry = zipfile.ZipInfo(name); entry.create_system = 3
            entry.external_attr = (0o100000 | mode) << 16
            entry.compress_type = zipfile.ZIP_DEFLATED; stream.writestr(entry, value)
    (a.out / 'PATCH.json').write_text(json.dumps(report, indent=2)+'\n')
    (a.out / 'SHA256SUMS').write_text(hashlib.sha256(archive.read_bytes()).hexdigest()+'  '+archive.name+'\n')
    print(archive)

if __name__ == '__main__': main()
