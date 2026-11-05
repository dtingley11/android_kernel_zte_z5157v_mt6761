#!/usr/bin/env python3
"""Exercise the actual legacy read proxies and private-wrapper constructor."""
import argparse
from pathlib import Path
import shlex
import subprocess
ROOT = Path(__file__).resolve().parents[3]
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--work', type=Path, required=True)
a = p.parse_args()
a.work.mkdir(parents=True, exist_ok=True)
s = (ROOT / 'KernelSU-Next/kernel/runtime/ksud_integration.c').read_text()
rc = s[s.index('static const char KERNEL_SU_RC[] ='):s.index('// Prefer /metadata')]
proxies = s[s.index('static ssize_t read_proxy('):s.index('static bool check_init_path(')]
(a.work / 'actual-proxies.inc').write_text(rc + '\nstatic const size_t ksu_rc_len=sizeof(KERNEL_SU_RC)-1;\n' + proxies)
subprocess.run(['cc', '-std=gnu11', '-Wall', '-Wextra', '-Werror', '-I', str(a.work),
                str(Path(__file__).with_name('init-rc.c')), '-o', str(a.work / 'init-rc')], check=True)
subprocess.run([str(a.work / 'init-rc')], check=True)
rc_text = subprocess.check_output([str(a.work / 'init-rc'), '--dump-rc'], text=True)
stages = []
for line in rc_text.splitlines():
    if not line.strip().startswith('exec '):
        continue
    tokens = shlex.split(line)
    assert tokens[:6] == ['exec', 'u:r:ksu:s0', 'root', '--', '/system/bin/sh', '-c'], tokens
    assert len(tokens) == 7, tokens
    command = shlex.split(tokens[-1])
    assert command[:2] == ['exec', '/data/adb/ksud'] and len(command) == 3, command
    stages.append(command[2])
assert stages == ['post-fs-data', 'services', 'services', 'boot-completed'], stages
print('PASS: all boot actions preserve the ksu SELinux context and shell command arguments')

security = (ROOT / 'KernelSU-Next/kernel/selinux/anon_inode_compat.c').read_text()
security = security[security.index('int ksu_inode_init_security_anon_compat('):security.rindex('#endif')]
wrapper = (ROOT / 'KernelSU-Next/kernel/infra/file_wrapper.c').read_text()
start = wrapper.index('struct file *ksu_anon_inode_create_getfile_compat(', wrapper.index('\n#else\nstruct file *ksu_anon_inode_create_getfile_compat'))
wrapper = wrapper[start:wrapper.index('\n#endif', start)]
(a.work / 'actual-wrapper.inc').write_text(security + '\nstatic struct vfsmount *anon_inode_mnt;\n' + wrapper)
subprocess.run(['cc', '-std=gnu11', '-Wall', '-Wextra', '-Werror', '-I', str(a.work),
                str(Path(__file__).with_name('wrapper.c')), '-o', str(a.work / 'wrapper')], check=True)
subprocess.run([str(a.work / 'wrapper')], check=True)

sucompat = (ROOT / 'KernelSU-Next/kernel/feature/sucompat.c').read_text()
start = sucompat.index('int ksu_handle_execveat_sucompat(')
sucompat = sucompat[start:sucompat.index('// sucompat: permitted', start)]
(a.work / 'actual-sucompat.inc').write_text(sucompat)
subprocess.run(['cc', '-std=gnu11', '-Wall', '-Wextra', '-Werror', '-Wno-unused-parameter',
                '-I', str(a.work), str(Path(__file__).with_name('sucompat.c')),
                '-o', str(a.work / 'sucompat')], check=True)
subprocess.run([str(a.work / 'sucompat')], check=True)

control = (ROOT / 'KernelSU-Next/kernel/compat/susfs.c').read_text()
control = control[control.index('int ksu_susfs_task_prctl('):]
constants = '\n'.join(line for line in (ROOT / 'include/linux/susfs_def.h').read_text().splitlines()
                      if line.startswith('#define CMD_') or line.startswith('#define SUSFS_FAKE_'))
(a.work / 'actual-susfs-control.inc').write_text(constants + '\n' + control)
subprocess.run(['cc', '-std=gnu11', '-Wall', '-Wextra', '-Werror', '-Wno-unused-parameter',
                '-Wno-misleading-indentation', '-I', str(a.work),
                str(Path(__file__).with_name('susfs-control.c')), '-o', str(a.work / 'susfs-control')], check=True)
subprocess.run([str(a.work / 'susfs-control')], check=True)

server = (ROOT / 'security/selinux/ss/services.c').read_text()
start = server.index('void security_ksu_policy_changed(')
helper = server[start:server.index('\n#endif', start)]
start = server.index('static void avd_init(')
decision = server[start:server.index('\n}', start)+2]
rules = (ROOT / 'KernelSU-Next/kernel/selinux/rules.c').read_text()
start = rules.index('static void reset_avc_cache(')
reset = rules[start:rules.index('\n#ifndef SELINUX_POLICY_INSTEAD_SELINUX_SS', start)]
(a.work / 'actual-policy-sequence.inc').write_text(helper + '\n' + decision + '\n' + reset)
subprocess.run(['cc', '-std=gnu11', '-Wall', '-Wextra', '-Werror', '-I', str(a.work),
                str(Path(__file__).with_name('policy-sequence.c')), '-o', str(a.work / 'policy-sequence')], check=True)
subprocess.run([str(a.work / 'policy-sequence')], check=True)
