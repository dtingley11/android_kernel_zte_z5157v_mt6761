#!/usr/bin/env python3
"""Compare ARM32 shared-UAPI values and layouts with pinned v3.4.2."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
import subprocess

ROOT = Path(__file__).resolve().parents[3]
REVISION = '4c706b5938665866ebe16944a481a7b91e3396af'
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--work', type=Path, required=True)
p.add_argument('--ndk', type=Path, required=True)
p.add_argument('--gcc', type=Path, help='Pinned GCC 4.9 toolchain directory for kernel-side constants')
p.add_argument('--upstream', type=Path, help='Generate the baseline from this upstream Git checkout')
a = p.parse_args()
a.work = a.work.resolve(); a.work.mkdir(parents=True, exist_ok=True)
bins = a.ndk / 'toolchains/llvm/prebuilt/linux-x86_64/bin'
baseline_path = Path(__file__).with_name('abi-v3.4.2-arm32.json')

def inspect(headers, names, records, label):
    source = a.work / (label + '.cc')
    expressions = [expr for name in names for expr in [f'(unsigned long long)({name})', f'sizeof({name})']]
    expressions += [expr for name in records for expr in [f'sizeof(struct {name})', f'alignof(struct {name})']]
    source.write_text('#include "uapi/ksu.h"\nunsigned long long abi[] = {\n' + ',\n'.join(expressions) + '\n};\n')
    obj = a.work / (label + '.o')
    result = subprocess.run([str(bins / 'armv7a-linux-androideabi26-clang++'), '-std=c++17',
                             '-Xclang', '-fdump-record-layouts-complete', '-I', str(headers),
                             '-c', str(source), '-o', str(obj)], text=True, capture_output=True, check=True)
    raw = a.work / (label + '.bin')
    subprocess.run([str(bins / 'llvm-objcopy'), '-O', 'binary', '--only-section=.data', str(obj), str(raw)], check=True)
    values = struct.unpack('<' + 'Q' * len(expressions), raw.read_bytes())
    layout = result.stdout.split('*** Dumping IRgen Record Layout')[0].replace(str(headers), '<source>')
    return {'values': list(values), 'record_layouts': layout}

if a.upstream:
    headers = a.work / 'upstream'; (headers / 'uapi').mkdir(parents=True, exist_ok=True)
    files = subprocess.check_output(['git', '-C', str(a.upstream), 'ls-tree', '-r', '--name-only', REVISION, 'uapi/'], text=True).splitlines()
    originals = []
    for name in files:
        data = subprocess.check_output(['git', '-C', str(a.upstream), 'show', f'{REVISION}:{name}'], text=True)
        (headers / name).write_text(data); originals.append(data)
    text = '\n'.join(originals)
    names = set(re.findall(r'static const __u\d+\s+(\w+)\s*=', text))
    names.update(re.findall(r'^#define ([A-Z]\w*)[ \t]+[^\n]+', text, re.M))
    for body in re.findall(r'enum \w+\s*\{(.*?)\}', text, re.S):
        names.update(re.findall(r'\b(KSU_[A-Z_0-9]+)\b', body))
    names = sorted(names)
    records = sorted(set(re.findall(r'^struct (\w+)\s*\{', text, re.M)))
    baseline = {'revision': REVISION, 'target': 'armv7a-linux-androideabi26',
                'constants': names, 'records': records, **inspect(headers, names, records, 'upstream')}
    baseline_path.write_text(json.dumps(baseline, indent=2) + '\n')
else:
    baseline = json.loads(baseline_path.read_text())
assert baseline['revision'] == REVISION
actual = inspect(ROOT / 'KernelSU-Next', baseline['constants'], baseline['records'], 'ported')
assert actual['values'] == baseline['values'], 'UAPI constant values, widths, sizes or alignments differ'
assert actual['record_layouts'] == baseline['record_layouts'], 'UAPI member offsets or record layouts differ'
if a.gcc:
    source = a.work / 'kernel-abi.c'
    source.write_text('#define bool _Bool\n' + (a.work / 'ported.cc').read_text().replace('alignof(', '_Alignof('))
    sysroot = bins.parent / 'sysroot/usr/include'
    obj = a.work / 'kernel-abi.o'
    subprocess.run([str(a.gcc / 'bin/arm-linux-androideabi-gcc'), '-std=gnu11', '-Werror',
                    '-nostdinc', '-mabi=aapcs-linux', '-D__KERNEL__', '-I', str(sysroot),
                    '-I', str(sysroot / 'arm-linux-androideabi'), '-I', str(ROOT / 'KernelSU-Next'),
                    '-c', str(source), '-o', str(obj)], check=True)
    raw = a.work / 'kernel-abi.bin'
    subprocess.run([str(a.gcc / 'bin/arm-linux-androideabi-objcopy'), '-O', 'binary',
                    '--only-section=.data', str(obj), str(raw)], check=True)
    kernel_values = list(struct.unpack('<' + 'Q' * len(baseline['values']), raw.read_bytes()))
    assert kernel_values == baseline['values'], 'GCC kernel-side UAPI differs from ARM32 userspace'
    print('PASS: GCC 4.9 kernel constants, widths, record sizes and alignments match NDK userspace')
print(f"PASS: {len(baseline['constants'])} UAPI constants (values and widths), {len(baseline['records'])} records (sizes, alignment and member offsets) match upstream v3.4.2 on ARM32")
(a.work / 'ABI.json').write_text(json.dumps({'revision': REVISION, 'target': baseline['target'],
    'constants': len(baseline['constants']), 'records': len(baseline['records']),
    'baseline_sha256': hashlib.sha256(baseline_path.read_bytes()).hexdigest(), 'status': 'passed'}, indent=2) + '\n')
