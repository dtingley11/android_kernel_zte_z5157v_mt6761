#!/usr/bin/env python3
"""Build and sign the experimental ARM32 manager with its matching daemon."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parent.parent

def run(command, logs, name, cwd=ROOT, env=None):
    with (logs / (name + '.log')).open('w') as stream:
        result = subprocess.run([str(x) for x in command], cwd=cwd, env=env,
                                stdout=stream, stderr=subprocess.STDOUT)
    if result.returncode:
        print((logs / (name + '.log')).read_text(errors='replace')[-3000:], file=sys.stderr)
        raise RuntimeError(f'{name} failed: {result.returncode}')

def arm32(data):
    return data[:6] == b'\x7fELF\x01\x01' and struct.unpack_from('<H', data, 18)[0] == 40

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work', type=Path, required=True)
    parser.add_argument('--daemon', type=Path, required=True)
    parser.add_argument('--keystore', type=Path, required=True)
    parser.add_argument('--alias', default='z5157v-manager')
    parser.add_argument('--offline', action='store_true')
    args = parser.parse_args()
    work = args.work.resolve(); work.mkdir(parents=True, exist_ok=True)
    logs = work / 'reports'; logs.mkdir(exist_ok=True)
    expected = json.loads((ROOT / 'ci/next-manager.json').read_text())
    report = {'status': 'failed', 'manager': expected, 'device_tested': False}
    try:
        if not os.environ.get('MANAGER_KEYSTORE_PASSWORD'):
            raise RuntimeError('MANAGER_KEYSTORE_PASSWORD is required')
        sdk = Path(os.environ['ANDROID_HOME']) / 'build-tools/35.0.0'
        cert = work / 'certificate.der'
        run(['keytool', '-exportcert', '-keystore', args.keystore, '-alias', args.alias,
             '-storepass:env', 'MANAGER_KEYSTORE_PASSWORD', '-file', cert], logs, 'certificate')
        cert_data = cert.read_bytes()
        if len(cert_data) != expected['certificate_size'] or hashlib.sha256(cert_data).hexdigest() != expected['certificate_sha256']:
            raise RuntimeError('Signing certificate differs from the kernel identity')
        daemon = args.daemon.resolve().read_bytes()
        if not arm32(daemon):
            raise RuntimeError('Daemon is not ARM32')
        target = ROOT / 'KernelSU-Next/manager/app/src/main/jniLibs/armeabi-v7a/libksud.so'
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(daemon)
        report['daemon_sha256'] = hashlib.sha256(daemon).hexdigest()
        gradle = ['./gradlew', '--no-daemon', '-PksuArm32Experimental=true',
                  '-Dorg.gradle.jvmargs=-Xmx4g -XX:MaxMetaspaceSize=1g -Dfile.encoding=UTF-8',
                  '--max-workers=2', 'assembleRelease']
        if args.offline:
            gradle.insert(1, '--offline')
        manager = ROOT / 'KernelSU-Next/manager'
        run(gradle, logs, 'manager-build', cwd=manager)
        outputs = list((manager / 'app/build/outputs/apk/release').glob('*.apk'))
        if len(outputs) != 1:
            raise RuntimeError(f'Expected one release APK, got {len(outputs)}')
        signed = logs / 'KernelSU-Next-v3.4.2-Z5157V-ARM32-experimental.apk'
        run([sdk / 'apksigner', 'sign', '--ks', args.keystore, '--ks-key-alias', args.alias,
             '--ks-pass', 'env:MANAGER_KEYSTORE_PASSWORD', '--key-pass', 'env:MANAGER_KEYSTORE_PASSWORD',
             '--v1-signing-enabled', 'false', '--v2-signing-enabled', 'true',
             '--v3-signing-enabled', 'false', '--v4-signing-enabled', 'false',
             '--out', signed, outputs[0]], logs, 'sign')
        run([sdk / 'apksigner', 'verify', '--verbose', '--print-certs', signed], logs, 'verify-signature')
        if expected['certificate_sha256'] not in (logs / 'verify-signature.log').read_text():
            raise RuntimeError('APK signer differs from kernel certificate')
        badging = subprocess.check_output([str(sdk / 'aapt'), 'dump', 'badging', str(signed)], text=True)
        (logs / 'apk-badging.log').write_text(badging)
        if f"package: name='{expected['package']}' versionCode='{expected['version_code']}'" not in badging:
            raise RuntimeError('APK package or version differs from the experimental kernel identity')
        with zipfile.ZipFile(signed) as stream:
            if stream.testzip():
                raise RuntimeError('APK integrity check failed')
            abis = {name.split('/')[1] for name in stream.namelist() if name.startswith('lib/')}
            if abis != {'armeabi-v7a'}:
                raise RuntimeError(f'Unexpected APK ABIs: {abis}')
            for name in stream.namelist():
                if name.startswith('lib/') and name.endswith('.so') and not arm32(stream.read(name)):
                    raise RuntimeError(f'Not an ARM32 ELF: {name}')
            if stream.read('lib/armeabi-v7a/libksud.so') != daemon:
                raise RuntimeError('APK contains a different daemon')
        digest = hashlib.sha256(signed.read_bytes()).hexdigest()
        (logs / 'SHA256SUMS').write_text(digest + '  ' + signed.name + '\n')
        report.update(status='built', apk_sha256=digest, source_revision=subprocess.check_output(
            ['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip())
        print(signed)
    except (OSError, ValueError, KeyError, RuntimeError, subprocess.CalledProcessError) as error:
        report['error'] = str(error); print(error, file=sys.stderr)
        return 1
    finally:
        (logs / 'MANAGER-BUILD.json').write_text(json.dumps(report, indent=2) + '\n')
    return 0

if __name__ == '__main__':
    sys.exit(main())
