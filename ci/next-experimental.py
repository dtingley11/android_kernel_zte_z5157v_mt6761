#!/usr/bin/env python3
"""Build and verify experimental legacy kernels and v3.4.2 ARM32 components."""
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
KERNEL_REVISION = 'b933b1f728116a456fbebf27b6a8772a640cdf23'


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
    combined = args.component == 'kernel-susfs'
    config = 'z5157v_next_susfs_experimental_defconfig' if combined else 'z5157v_next_experimental_defconfig'
    run([*make, config], logs, 'configure')
    values = config_values(out / '.config')
    expected = {'KSU': 'y', 'KSU_ARM32_EXPERIMENTAL': 'y', 'KSU_MANUAL_HOOK': 'y',
                'KSU_KPROBES_HOOK': 'n', 'KSU_SYSCALL_TABLE_HOOK': 'n', 'KPROBES': 'n',
                'KSU_DEBUG': 'n', 'KSU_DISABLE_MANAGER': 'n', 'KSU_DISABLE_POLICY': 'n',
                'SECURITY_SELINUX': 'y', 'SECURITY_SELINUX_BOOTPARAM_VALUE': '1',
                'MODULE_SIG_FORCE': 'y', 'KSU_SUSFS': 'y' if combined else 'n',
                'KSU_SUSFS_SUS_SU': 'n'}
    if combined:
        fragment = config_values(ROOT / 'ci/susfs.config')
        expected.update(fragment)
    for option, expected_value in expected.items():
        if values.get(option, 'n') != expected_value:
            raise RuntimeError(f'Unexpected CONFIG_{option}={values.get(option)}')
    report['configuration_checks'] = expected
    report['variant'] = 'ksu-susfs' if combined else 'ksu'
    report['manager'] = json.loads((ROOT / 'ci/next-manager.json').read_text())
    report['susfs_revision'] = '41ba0b533b8524a0ba95a5952506a75f17355450' if combined else None
    report['enabled_susfs_features'] = sorted(k for k,v in values.items() if k.startswith('KSU_SUSFS') and v == 'y')
    run([sys.executable, ROOT / 'tools/testing/z5157v-next-legacy/run.py',
         '--work', args.work / 'tests'], logs, 'host-checks')
    run([*make, f'-j{args.jobs}', 'zImage-dtb', 'dtbs', 'modules'], logs, 'full-kernel')
    unresolved = subprocess.check_output([str(toolchain / 'bin/arm-linux-androideabi-nm'),
                                          '-u', str(out / 'vmlinux')], text=True)
    (logs / 'undefined-symbols.txt').write_text(unresolved)
    allowed = {'__ddp_mem_test', 'mlog_get_buffer', 'report_hub_dmd'}
    for line in unresolved.splitlines():
        kind, name = line.split()
        if kind != 'w' or name not in allowed:
            raise RuntimeError(f'Unexpected unresolved symbol: {line}')
    symbols = subprocess.check_output([str(toolchain / 'bin/arm-linux-androideabi-nm'),
                                       str(out / 'vmlinux')], text=True)
    linked = {line.split()[-1] for line in symbols.splitlines() if line.split()}
    required = {'ksu_handle_execveat', 'ksu_handle_faccessat', 'ksu_handle_stat',
                'ksu_handle_vfs_read', 'ksu_handle_input_handle_event',
                'ksu_handle_sys_reboot', 'ksu_lsm_hook_init', 'ksu_handle_setresuid',
                'ksu_install_file_wrapper', 'ksu_inode_init_security_anon_compat',
                'security_ksu_policy_changed'}
    if combined:
        required.update({'susfs_init', 'ksu_susfs_task_prctl', 'susfs_try_umount_all', 'susfs_set_ksu_sid'})
    if not required <= linked:
        raise RuntimeError(f'Missing linked interfaces: {sorted(required - linked)}')
    report['linked_interfaces'] = sorted(required)
    report['unresolved_symbols'] = [line.split()[-1] for line in unresolved.splitlines()]
    report['kernel_version_code'] = 33318
    minimum_source = (NEXT / 'manager/app/src/main/java/com/rifsxd/ksunext/Natives.kt').read_text()
    import re
    minimum = int(re.search(r'MINIMAL_SUPPORTED_KERNEL = (\d+)', minimum_source).group(1))
    if minimum > 33318:
        raise RuntimeError('Manager requires a newer kernel control interface')
    report['manager_minimum_kernel_version'] = minimum
    ndk_environment(args)
    run([sys.executable, ROOT / 'tools/testing/z5157v-next-legacy/abi.py',
         '--ndk', args.ndk, '--gcc', toolchain, '--work', args.work / 'abi'], logs, 'uapi-abi')
    identity = json.loads((ROOT / 'ci/stock-uname.json').read_text())
    image = (out / 'arch/arm/boot/Image').read_bytes()
    for field in ('release', 'version'):
        if identity[field].encode().ljust(65, b'\0') not in image:
            raise RuntimeError(f'Actual kernel UTS {field} differs from stock')
    report['uname'] = identity
    for field in ('package', 'certificate_sha256'):
        if report['manager'][field].encode() not in image:
            raise RuntimeError(f'Kernel does not contain the expected manager {field}')
    check_arm_elf(out / 'vmlinux')
    report['outputs'] = [{'file': str(path.relative_to(out)),
                          'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
                         for path in [out / 'vmlinux', out / 'arch/arm/boot/Image',
                                      out / 'arch/arm/boot/zImage-dtb', out / 'arch/arm/boot/mtk.dtb']]


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
    run([sys.executable, ROOT / 'tools/testing/z5157v-next-legacy/abi.py',
         '--ndk', args.ndk, '--work', args.work / 'abi'], logs, 'uapi-abi')
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
    artifact = logs / 'ksud-arm32'
    run([bins / 'llvm-strip', '--strip-all', '-o', artifact, daemon], logs, 'strip-daemon')
    report['daemon_artifact'] = check_arm_elf(artifact)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('component', choices=('kernel', 'kernel-susfs', 'native', 'daemon'))
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
    report = {'component': args.component, 'userspace_revision': REVISION, 'kernel_revision': KERNEL_REVISION,
              'status': 'failed', 'device_tested': False, 'flashable_package': False,
              'source_revision': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
              'source_dirty': bool(subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT, text=True))}
    try:
        imported = json.loads((NEXT / 'UPSTREAM.json').read_text())
        if imported['revision'] != REVISION or imported['kernel']['revision'] != KERNEL_REVISION:
            raise RuntimeError('Unexpected upstream source revision')
        {'kernel': build_kernel, 'kernel-susfs': build_kernel, 'native': build_native, 'daemon': build_daemon}[args.component](args, logs, report)
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
                             'Experimental build; no flashable package or device verification.\n')
    return 0 if report['status'] == 'compiled' else 1


if __name__ == '__main__':
    sys.exit(main())
