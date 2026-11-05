#!/usr/bin/env python3
"""Build isolated v3.4.2 ARM32 components; never create a flashable package."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess
import sys

from build import TOOLCHAIN_SHA, TOOLCHAIN_URL, config_values, fetch

ROOT = Path(__file__).resolve().parent.parent
NEXT = ROOT / 'KernelSU-Next'
REVISION = '4c706b5938665866ebe16944a481a7b91e3396af'


def run(command, logs, name, cwd=ROOT, env=None):
    with (logs / (name + '.log')).open('w') as stream:
        result = subprocess.run([str(a) for a in command], cwd=cwd, env=env,
                                stdout=stream, stderr=subprocess.STDOUT)
    if result.returncode:
        print((logs / (name + '.log')).read_text(errors='replace')[-3000:], file=sys.stderr)
        raise RuntimeError(f'{name} failed with exit status {result.returncode}')


def check_arm_elf(path):
    data = path.read_bytes()
    if data[:6] != b'\x7fELF\x01\x01' or struct.unpack_from('<H', data, 18)[0] != 40:
        raise RuntimeError(f'{path.name} is not little-endian ELF32 ARM')
    return {'file': path.name, 'sha256': hashlib.sha256(data).hexdigest(), 'elf': 'ARM32'}


def build_kernel(args, logs, report):
    toolchain = args.toolchain or args.work / 'gcc'
    if not args.toolchain:
        fetch(TOOLCHAIN_URL, TOOLCHAIN_SHA, toolchain, logs, 'gcc')
    revision = subprocess.check_output(['git', '-C', str(toolchain), 'rev-parse', 'HEAD'], text=True).strip()
    if revision != TOOLCHAIN_SHA:
        raise RuntimeError('Toolchain does not match the pinned GCC 4.9 revision')
    report['toolchain_revision'] = revision
    out = args.work / 'kernel'
    make = ['make', f'O={out}', 'ARCH=arm',
            f'CROSS_COMPILE={toolchain}/bin/arm-linux-androideabi-', 'HOSTCFLAGS=-O2 -fcommon']
    run([*make, 'z5157v_next_experimental_defconfig'], logs, 'configure')
    values = config_values(out / '.config')
    expected = {'KSU': 'y', 'KSU_ARM32_EXPERIMENTAL': 'y', 'KPROBES': 'n',
                'SECURITY_SELINUX': 'y', 'SECURITY_SELINUX_BOOTPARAM_VALUE': '1',
                'MODULE_SIG_FORCE': 'y'}
    for option, expected_value in expected.items():
        if values.get(option, 'n') != expected_value:
            raise RuntimeError(f'Unexpected CONFIG_{option}={values.get(option)}')
    report['configuration_checks'] = expected
    # Keep going across object failures to expose independent porting blockers.
    # No zImage/boot.img/AK3 is built, even if all objects eventually compile.
    run([*make, '-k', f'-j{args.jobs}', 'KernelSU-Next/kernel/'], logs, 'kernel-objects')


def ndk_environment(args):
    if not args.ndk:
        raise RuntimeError('Specify --ndk or ANDROID_NDK_HOME')
    bins = args.ndk / 'toolchains/llvm/prebuilt/linux-x86_64/bin'
    if not (bins / 'armv7a-linux-androideabi26-clang').is_file():
        raise RuntimeError('NDK ARM32 compiler was not found')
    return bins


def build_native(args, logs, report):
    bins = ndk_environment(args)
    out = args.work / 'native'
    out.mkdir(exist_ok=True)
    cpp = NEXT / 'manager/app/src/main/cpp'
    compiler = bins / 'armv7a-linux-androideabi26-clang++'
    common = [compiler, '-std=c++17', '-fPIC', '-shared']
    run([*common, '-I', NEXT, cpp / 'ksu.cc', cpp / 'jni.cc', '-llog', '-o', out / 'libkernelsu.so'], logs, 'native-manager')
    run([*common, cpp / 'adbroot.cc', '-llog', '-ldl', '-o', out / 'libadbroot.so'], logs, 'native-adbroot')
    report['outputs'] = [check_arm_elf(path) for path in sorted(out.glob('*.so'))]


def build_daemon(args, logs, report):
    bins = ndk_environment(args)
    env = os.environ.copy()
    env.update(ANDROID_NDK_HOME=str(args.ndk), CARGO_TARGET_DIR=str(args.work / 'rust'),
               CARGO_BUILD_JOBS=str(args.jobs),
               CARGO_TARGET_ARMV7_LINUX_ANDROIDEABI_LINKER=str(bins / 'armv7a-linux-androideabi26-clang'),
               CC_armv7_linux_androideabi=str(bins / 'armv7a-linux-androideabi26-clang'),
               CXX_armv7_linux_androideabi=str(bins / 'armv7a-linux-androideabi26-clang++'),
               AR_armv7_linux_androideabi=str(bins / 'llvm-ar'),
               BINDGEN_EXTRA_CLANG_ARGS_armv7_linux_androideabi=(
                   f'--sysroot={bins.parent}/sysroot -I{bins.parent}/sysroot/usr/include/arm-linux-androideabi'))
    run([args.cargo, 'build', '--locked', '--target', 'armv7-linux-androideabi', '--release',
         '--manifest-path', NEXT / 'userspace/ksud/Cargo.toml'], logs, 'daemon', env=env)
    daemon = args.work / 'rust/armv7-linux-androideabi/release/ksud'
    report['outputs'] = [check_arm_elf(daemon)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('component', choices=('kernel', 'native', 'daemon'))
    parser.add_argument('--work', type=Path, required=True)
    parser.add_argument('--toolchain', type=Path)
    parser.add_argument('--ndk', type=Path, default=os.environ.get('ANDROID_NDK_HOME'))
    parser.add_argument('--cargo', default='cargo')
    parser.add_argument('--jobs', type=int, default=4)
    args = parser.parse_args()
    args.work = args.work.resolve()
    args.work.mkdir(parents=True, exist_ok=True)
    if args.ndk:
        args.ndk = args.ndk.resolve()
    logs = args.work / 'reports'
    logs.mkdir(exist_ok=True)
    report = {'component': args.component, 'upstream_revision': REVISION,
              'status': 'failed', 'device_tested': False, 'flashable_package': False}
    try:
        imported = json.loads((NEXT / 'UPSTREAM.json').read_text())
        if imported['revision'] != REVISION:
            raise RuntimeError('Unexpected upstream source revision')
        {'kernel': build_kernel, 'native': build_native, 'daemon': build_daemon}[args.component](args, logs, report)
        report['status'] = 'compiled'
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as error:
        report['error'] = str(error)
        print(error, file=sys.stderr)
    finally:
        (logs / 'STATUS.json').write_text(json.dumps(report, indent=2) + '\n')
        summary = os.environ.get('GITHUB_STEP_SUMMARY')
        if summary:
            with open(summary, 'a') as stream:
                stream.write(f"### v3.4.2 ARM32: {args.component}\n\nStatus: **{report['status']}**. "
                             'Experimental component build only; no flashable package or device verification.\n')
    return 0 if report['status'] == 'compiled' else 1


if __name__ == '__main__':
    sys.exit(main())
