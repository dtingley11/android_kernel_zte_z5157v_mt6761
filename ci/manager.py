#!/usr/bin/env python3
"""Build the signed Android 10 manager matching this branch's v1.0.8 kernels."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import urllib.request
import zipfile

from build import fetch

ROOT = Path(__file__).resolve().parent.parent
RECIPE = ROOT / 'ci/manager'
KSU = '9d9f9ed5d5f3a66a2f44e24c926075554f9275ce'
MMRL = '2bb00b3c2b9e3e9705a5d7c4d2d6ece1d8ba36c4'
APK_URL = 'https://github.com/KernelSU-Next/KernelSU-Next/releases/download/v1.0.8/KernelSU_Next_v1.0.8_12701-release.apk'
APK_HASH = 'ee34907c92888f1c17a6bdd6cf205ebc04b6b50aac5005cec366ba0d182e4b46'


def run(command, cwd, logs, name, env=None):
    with (logs / (name + '.log')).open('w') as log:
        result = subprocess.run([str(a) for a in command], cwd=cwd, env=env,
                                stdout=log, stderr=subprocess.STDOUT)
    if result.returncode:
        print((logs / (name + '.log')).read_text(errors='replace')[-3000:], file=sys.stderr)
        raise RuntimeError(f'{name} failed: {result.returncode}')


def archive(source, revision, dest):
    import tarfile
    dest.mkdir()
    process = subprocess.Popen(['git', '-C', str(source), 'archive', revision], stdout=subprocess.PIPE)
    with tarfile.open(fileobj=process.stdout, mode='r|') as stream:
        stream.extractall(dest, filter='data')
    if process.wait():
        raise RuntimeError('Local source archive failed')
    subprocess.run(['git', 'init', '-q', str(dest)], check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work', type=Path, required=True)
    parser.add_argument('--keystore', type=Path, required=True)
    parser.add_argument('--alias', default='z5157v-manager')
    parser.add_argument('--ksu-source', type=Path)
    parser.add_argument('--mmrl-source', type=Path)
    parser.add_argument('--upstream-apk', type=Path)
    parser.add_argument('--prepare-only', action='store_true')
    args = parser.parse_args()
    work = args.work.resolve(); work.mkdir(parents=True, exist_ok=True)
    logs = work / 'reports'; logs.mkdir(exist_ok=True)
    report = {'status': 'failed', 'ksu_revision': KSU, 'mmrl_revision': MMRL}
    try:
        ksu = work / 'ksu'; mmrl = work / 'mmrl'
        if args.ksu_source:
            archive(args.ksu_source, KSU, ksu)
        else:
            assert fetch('https://github.com/KernelSU-Next/KernelSU-Next.git', KSU, ksu, logs, 'manager-source') == KSU
        if args.mmrl_source:
            archive(args.mmrl_source, MMRL, mmrl)
        else:
            assert fetch('https://github.com/MMRLApp/MMRL.git', MMRL, mmrl, logs, 'mmrl-source') == MMRL
        run(['git', 'apply', '--check', RECIPE / 'v1.0.8-android10.patch'], ksu, logs, 'patch-check')
        run(['git', 'apply', RECIPE / 'v1.0.8-android10.patch'], ksu, logs, 'patch')
        library = ksu / 'manager/third-party/mmrl-platform'
        shutil.copytree(mmrl / 'platform', library)
        shutil.copy2(mmrl / 'LICENSE', library / 'LICENSE')
        shutil.copy2(RECIPE / 'platform.gradle.kts', library / 'build.gradle.kts')
        java = library / 'src/main/java/com/dergoogler/mmrl/platform/hiddenApi'
        java.mkdir(parents=True)
        shutil.copy2(RECIPE / 'UserListCompat.java', java / 'UserListCompat.java')
        hidden = library / 'src/main/kotlin/com/dergoogler/mmrl/platform/hiddenApi/HiddenUserManager.kt'
        text = hidden.read_text()
        old = 'userManager.getUsers(true, true, true)'
        if text.count(old) != 1:
            raise RuntimeError('Unexpected HiddenUserManager implementation')
        hidden.write_text(text.replace(old, 'UserListCompat.getUsers(userManager, IUserManager::class.java)'))
        tests = work / 'tests'; tests.mkdir()
        run(['javac', '--release', '8', '-d', tests, java / 'UserListCompat.java', RECIPE / 'UserListCompatTest.java'], ROOT, logs, 'compile-tests')
        run(['java', '-cp', tests, 'com.dergoogler.mmrl.platform.hiddenApi.UserListCompatTest'], ROOT, logs, 'test-user-list')
        upstream_apk = args.upstream_apk or work / 'official.apk'
        if not args.upstream_apk:
            with urllib.request.urlopen(APK_URL) as response, upstream_apk.open('wb') as output:
                shutil.copyfileobj(response, output)
        if hashlib.sha256(upstream_apk.read_bytes()).hexdigest() != APK_HASH:
            raise RuntimeError('Official v1.0.8 APK checksum differs')
        with zipfile.ZipFile(upstream_apk) as stream:
            native = ksu / 'manager/app/src/main/jniLibs/armeabi-v7a'
            for name in ('libksud_magic.so', 'libksud_overlayfs.so', 'libsusfsd.so'):
                (native / name).write_bytes(stream.read('lib/armeabi-v7a/' + name))
        report['status'] = 'prepared'
        if args.prepare_only:
            return 0
        if not os.environ.get('MANAGER_KEYSTORE_PASSWORD'):
            raise RuntimeError('MANAGER_KEYSTORE_PASSWORD is required')
        expected = json.loads((RECIPE / 'manager.json').read_text())
        cert = work / 'certificate.der'
        run(['keytool', '-exportcert', '-keystore', args.keystore, '-alias', args.alias,
             '-storepass:env', 'MANAGER_KEYSTORE_PASSWORD', '-file', cert], ROOT, logs, 'certificate')
        if len(cert.read_bytes()) != expected['certificate_size'] or hashlib.sha256(cert.read_bytes()).hexdigest() != expected['certificate_sha256']:
            raise RuntimeError('Signing key does not match the kernel manager configuration')
        run(['./gradlew', '--no-daemon', '-Dorg.gradle.jvmargs=-Xmx4g -XX:MaxMetaspaceSize=1g -Dfile.encoding=UTF-8',
             '-Pkotlin.daemon.jvmargs=-Xmx3g', '--max-workers=2', 'assembleRelease'], ksu / 'manager', logs, 'manager-build')
        unsigned = ksu / 'manager/app/build/outputs/apk/release/KernelSU_Next_v1.0.8-z5157v-android10_12701-release.apk'
        signed = logs / 'KernelSU_Next_v1.0.8-Z5157V-Android10.apk'
        sdk = Path(os.environ['ANDROID_HOME']) / 'build-tools/35.0.0'
        run([sdk / 'apksigner', 'sign', '--ks', args.keystore, '--ks-key-alias', args.alias,
             '--ks-pass', 'env:MANAGER_KEYSTORE_PASSWORD', '--key-pass', 'env:MANAGER_KEYSTORE_PASSWORD',
             '--v1-signing-enabled', 'false', '--v2-signing-enabled', 'true', '--v3-signing-enabled', 'false',
             '--v4-signing-enabled', 'false', '--out', signed, unsigned], ROOT, logs, 'sign')
        run([sdk / 'apksigner', 'verify', '--verbose', '--print-certs', signed], ROOT, logs, 'verify-signature')
        badging = subprocess.check_output([str(sdk / 'aapt'), 'dump', 'badging', str(signed)], text=True)
        if f"package: name='{expected['package']}' versionCode='12701'" not in badging:
            raise RuntimeError('APK identity differs from the matching kernel configuration')
        (logs / 'apk-badging.log').write_text(badging)
        with zipfile.ZipFile(signed) as stream:
            if stream.testzip():
                raise RuntimeError('APK integrity check failed')
            abis = {n.split('/')[1] for n in stream.namelist() if n.startswith('lib/')}
            if abis != {'armeabi-v7a'}:
                raise RuntimeError(f'Unexpected APK ABIs: {abis}')
            for name in stream.namelist():
                if name.startswith('lib/') and name.endswith('.so'):
                    data = stream.read(name)
                    if data[:6] != b'\x7fELF\x01\x01' or struct.unpack_from('<H', data, 18)[0] != 40:
                        raise RuntimeError(f'Not an ARM32 library: {name}')
        digest = hashlib.sha256(signed.read_bytes()).hexdigest()
        (logs / 'SHA256SUMS').write_text(digest + '  ' + signed.name + '\n')
        report.update(status='built', manager=expected, apk_sha256=digest)
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as error:
        report['status'] = 'failed'
        report['error'] = str(error)
        print(error, file=sys.stderr)
        return 1
    finally:
        (logs / 'MANAGER-BUILD.json').write_text(json.dumps(report, indent=2) + '\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
