#!/usr/bin/env python3
"""Test the actual init-rc read proxies with controlled file and user buffers."""
from pathlib import Path
import argparse,shlex,subprocess
ROOT=Path(__file__).resolve().parents[3]
p=argparse.ArgumentParser();p.add_argument('--work',type=Path,required=True);args=p.parse_args();args.work.mkdir(parents=True,exist_ok=True)
source=(ROOT/'KernelSU-Next/kernel/ksud.c').read_text()
rc=source[source.index('static const char KERNEL_SU_RC[] ='):source.index('static void stop_vfs_read_hook')]
proxies=source[source.index('static ssize_t read_proxy('):source.index('static bool is_init_rc(')]
(args.work/'actual-proxies.inc').write_text(rc+'\nstatic const size_t ksu_rc_len = sizeof(KERNEL_SU_RC)-1;\n'+proxies)
subprocess.run(['cc','-std=gnu11','-Wall','-Wextra','-I',str(args.work),str(Path(__file__).with_name('test.c')),'-o',str(args.work/'test')],check=True)
subprocess.run([str(args.work/'test')],check=True)

rc_text=subprocess.check_output([str(args.work/'test'),'--dump-rc'],text=True)
stages=[]
for line in rc_text.splitlines():
 if not line.strip().startswith('exec '):continue
 tokens=shlex.split(line)
 assert tokens[:6]==['exec','u:r:su:s0','root','--','/system/bin/sh','-c'],tokens
 assert len(tokens)==7,tokens
 command=shlex.split(tokens[-1])
 assert command[:2]==['exec','/data/adb/ksud'] and len(command)==3,command
 stages.append(command[2])
 stub=args.work/'daemon-stub.sh'
 stub.write_text('#!/bin/sh\nprintf "%s\\n" "$1"\n');stub.chmod(0o755)
 output=subprocess.check_output(['sh','-c',tokens[-1].replace('/data/adb/ksud',shlex.quote(str(stub)))],text=True)
 assert output.strip()==command[2],output
assert stages==['post-fs-data','services','services','boot-completed'],stages
print('PASS: boot actions preserve the SELinux context and pass each complete exec command to the system shell')
