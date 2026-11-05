#!/usr/bin/env python3
"""Build the ARM32 SUSFS v1.5.5 tool and an offline R28 module adaptation."""
import argparse,hashlib,json,os
from pathlib import Path
import shutil,struct,subprocess,urllib.request,zipfile
ROOT=Path(__file__).resolve().parent.parent
URL='https://github.com/sidex15/susfs4ksu-module/releases/download/v1.5.2%2B_R28/ksu_module_susfs_1.5.2%2B.zip'
SHA='abcd6bf456ea8189298d9e496faa440201d90e4f0bd93b83c0527589001c9376'
SUSFS='41ba0b533b8524a0ba95a5952506a75f17355450'

def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--work',required=True,type=Path);p.add_argument('--out',required=True,type=Path)
 p.add_argument('--ndk',type=Path,default=os.environ.get('ANDROID_NDK_HOME'))
 p.add_argument('--source-zip',type=Path);args=p.parse_args()
 args.work=args.work.resolve();args.out=args.out.resolve()
 args.work.mkdir(parents=True,exist_ok=True);args.out.mkdir(parents=True,exist_ok=True)
 if not args.ndk:raise RuntimeError('Specify --ndk or ANDROID_NDK_HOME')
 ndk=args.ndk.resolve();source=args.source_zip or args.work/'upstream-r28.zip'
 if not args.source_zip:
  with urllib.request.urlopen(URL) as stream,source.open('wb') as output:shutil.copyfileobj(stream,output)
 if hashlib.sha256(source.read_bytes()).hexdigest()!=SHA:raise RuntimeError('Upstream R28 ZIP hash changed')
 with (args.out/'susfs-arm32-build.log').open('w') as log:
  subprocess.run([str(ndk/'ndk-build'),f'NDK_PROJECT_PATH={ROOT}/tools/susfs',f'APP_BUILD_SCRIPT={ROOT}/tools/susfs/jni/Android.mk',f'NDK_APPLICATION_MK={ROOT}/tools/susfs/jni/Application.mk',f'NDK_OUT={args.work}/obj',f'NDK_LIBS_OUT={args.work}/bin','APP_ABI=armeabi-v7a'],stdout=log,stderr=subprocess.STDOUT,check=True)
 tool=args.work/'bin/armeabi-v7a/ksu_susfs'
 subprocess.run([str(ndk/'toolchains/llvm/prebuilt/linux-x86_64/bin/llvm-strip'),'--strip-unneeded',str(tool)],check=True)
 data=tool.read_bytes()
 if data[:6]!=b'\x7fELF\x01\x01' or struct.unpack_from('<H',data,18)[0]!=40:raise RuntimeError('Tool is not ARM32 ELF')
 stage=args.work/'module';stage.mkdir()
 with zipfile.ZipFile(source) as z:
  for item in z.infolist():
   name=Path(item.filename)
   if name.is_absolute() or '..' in name.parts:raise RuntimeError('Unsafe ZIP member')
  z.extractall(stage)
 for item in (stage/'tools').iterdir():item.unlink()
 shutil.copy2(tool,stage/'tools/ksu_susfs_arm')
 shutil.copy2(ROOT/'tools/susfs/LICENSE',stage/'LICENSE-ksu-susfs')
 customize=stage/'customize.sh';text=customize.read_text()
 start=text.index('download()');end=text.index('# set permissions',start)
 text=text[:start]+'''# This package targets ARM32 and the verified built-in SUSFS v1.5.5 port.
case "$(uname -m)" in
  armv*l) ;;
  *) abort 'This compatibility package requires an ARM32 kernel.' ;;
esac
chmod 0755 "${TMPDIR}/susfs/tools/ksu_susfs_arm"
SUSFS_VERSION_RAW="$("${TMPDIR}/susfs/tools/ksu_susfs_arm" show version)"
[ "$SUSFS_VERSION_RAW" = "v1.5.5" ] || abort 'This package requires SUSFS v1.5.5.'
cp -f "${TMPDIR}/susfs/tools/ksu_susfs_arm" "${DEST_BIN_DIR}/ksu_susfs"
chmod 0755 "${DEST_BIN_DIR}/ksu_susfs"
ui_print 'Installed ARM32 SUSFS v1.5.5 tool; SUS_SU is unavailable with this manual-hook port.'

'''+text[end:]
 customize.write_text(text)
 prop=stage/'module.prop';text=prop.read_text()
 text=text.replace('name=SUSFS-FOR-KERNELSU','name=SUSFS-FOR-KERNELSU (ARM32 v1.5.5)')
 text=text.replace('version=v1.5.2-R28','version=v1.5.2-R28-arm32-v1.5.5')
 text=text.replace('versionCode=105002028','versionCode=105002029')
 text='\n'.join(line for line in text.splitlines() if not line.startswith('updateJson='))+'\n';prop.write_text(text)
 config=stage/'config.sh';text=config.read_text().replace('sus_su=2','sus_su=-1');config.write_text(text)
 tool_hash=hashlib.sha256(data).hexdigest()
 (stage/'susfs-bin-check.sh').write_text('#!/system/bin/sh\nexpected='+tool_hash+'\nactual=$(sha256sum /data/adb/ksu/bin/ksu_susfs | cut -d " " -f1)\n[ "$actual" = "$expected" ] && echo match || echo mismatch\n')
 updater="#!/system/bin/sh\necho 'The ARM32 v1.5.5 tool is bundled with this package. Install a matching compatibility package to update it.'\nexit 1\n"
 for name in ('susfs-bin-update.sh','action.sh'):
  (stage/name).write_text(updater)
 provenance={'module_source_url':URL,'module_source_sha256':SHA,'susfs_revision':SUSFS,'tool_abi':'armeabi-v7a','tool_sha256':tool_hash,'kernel_version_required':'v1.5.5','sus_su_supported':False}
 (stage/'ARM32-BUILD.json').write_text(json.dumps(provenance,indent=2)+'\n')
 for script in stage.glob('*.sh'):
  if 'ksu_susfs_arm64' in script.read_text():raise RuntimeError('ARM64 download remains in '+script.name)
  subprocess.run(['sh','-n',str(script)],check=True)
 archive=args.out/'SUSFS-R28-Z5157V-ARM32-v1.5.5.zip'
 with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
  for f in sorted(stage.rglob('*')):
   if f.is_file():z.write(f,str(f.relative_to(stage)))
 with zipfile.ZipFile(archive) as z:
  assert z.testzip() is None
  assert z.read('tools/ksu_susfs_arm')==data
  assert not any('arm64' in n for n in z.namelist())
  assert b'ksu_susfs_arm64' not in z.read('customize.sh')
 digest=hashlib.sha256(archive.read_bytes()).hexdigest()
 sums=args.out/'SHA256SUMS'
 lines=sums.read_text().splitlines() if sums.exists() else []
 lines=[line for line in lines if not line.endswith('  '+archive.name)]
 sums.write_text('\n'.join(lines+[digest+'  '+archive.name])+'\n')
 print(archive)

if __name__=='__main__':main()
