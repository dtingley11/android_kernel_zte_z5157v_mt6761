#!/usr/bin/env python3
"""Package a verified experimental kernel for Z5157V device testing."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import stat
import subprocess
import tempfile
import zipfile
from build import fetch

ROOT = Path(__file__).resolve().parent.parent
AK3 = '41f04bdb4ee30a44e429c2c1131d5e8bb32b15f1'
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--work', type=Path, required=True)
p.add_argument('--anykernel-source', type=Path)
a = p.parse_args(); work = a.work.resolve(); reports = work / 'reports'
report = json.loads((reports / 'STATUS.json').read_text())
if report['status'] != 'compiled' or report['component'] not in ('kernel', 'kernel-susfs'):
    raise RuntimeError('Only a verified experimental kernel can be packaged')
identity = json.loads((ROOT / 'ci/next-manager.json').read_text())
if report['manager'] != identity:
    raise RuntimeError('Kernel manager identity differs from the signed APK recipe')
up = a.anykernel_source.resolve() if a.anykernel_source else work / 'anykernel-upstream'
if not a.anykernel_source:
    fetch('https://github.com/osm0sis/AnyKernel3.git', AK3, up, reports, 'anykernel')
revision = subprocess.check_output(['git', '-C', str(up), 'rev-parse', 'HEAD'], text=True).strip()
if revision != AK3:
    raise RuntimeError('AnyKernel3 revision differs from the reviewed installer')
image = work / 'kernel/arch/arm/boot/Image'
recorded = next(x['sha256'] for x in report['outputs'] if x['file'] == 'arch/arm/boot/Image')
if hashlib.sha256(image.read_bytes()).hexdigest() != recorded:
    raise RuntimeError('Kernel changed after build verification')
stage = Path(tempfile.mkdtemp(prefix='next-anykernel-', dir=work))
for directory in ('META-INF', 'tools'):
    shutil.copytree(up / directory, stage / directory, symlinks=True)
shutil.copy2(up / 'LICENSE', stage / 'LICENSE')
shutil.copy2(image, stage / 'Image')
shutil.copy2(work / 'kernel/arch/arm/boot/dts/mango/mt6761.dtb', stage / 'kernel_dtb')
label = 'KernelSU Next v3.4.2 ARM32 experimental'
if report['variant'] == 'ksu-susfs':
    label += ' + SUSFS v1.5.5'
(stage / 'anykernel.sh').write_text((ROOT / 'ci/anykernel/anykernel.sh').read_text().replace('@VARIANT@', label))
(stage / 'anykernel.sh').chmod(0o755)
report.update(package_type='AnyKernel3', anykernel_revision=revision, flashable_package=True,
              device_boot_tested=False, runtime_verification='pending on matching experimental kernel')
(stage / 'BUILD.json').write_text(json.dumps(report, indent=2) + '\n')
files = sorted(x for x in stage.rglob('*') if x.is_file())
(stage / 'SHA256SUMS').write_text(''.join(hashlib.sha256(x.read_bytes()).hexdigest()+'  '+str(x.relative_to(stage))+'\n' for x in files))
archive = reports / f"AnyKernel3-Z5157V-Next-v3.4.2-{report['variant']}-experimental-{report['source_revision'][:9]}.zip"
with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as stream:
    for path in sorted(stage.rglob('*')):
        if path.is_file(): stream.write(path, str(path.relative_to(stage)))
with zipfile.ZipFile(archive) as stream:
    assert stream.testzip() is None
    assert stream.read('Image') == image.read_bytes()
    assert stream.read('kernel_dtb') == (stage / 'kernel_dtb').read_bytes()
    assert stream.getinfo('META-INF/com/google/android/update-binary').external_attr >> 16 & stat.S_IXUSR
archive.with_suffix('.zip.sha256').write_text(hashlib.sha256(archive.read_bytes()).hexdigest()+'  '+archive.name+'\n')
(reports / 'PACKAGE.json').write_text(json.dumps(report, indent=2)+'\n')
print(archive)
