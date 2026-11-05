#!/usr/bin/env python3
"""Test the actual init-rc read proxies with controlled file and user buffers."""
from pathlib import Path
import argparse,subprocess
ROOT=Path(__file__).resolve().parents[3]
p=argparse.ArgumentParser();p.add_argument('--work',type=Path,required=True);args=p.parse_args();args.work.mkdir(parents=True,exist_ok=True)
source=(ROOT/'KernelSU-Next/kernel/ksud.c').read_text()
rc=source[source.index('static const char KERNEL_SU_RC[] ='):source.index('static void stop_vfs_read_hook')]
proxies=source[source.index('static ssize_t read_proxy('):source.index('static bool is_init_rc(')]
(args.work/'actual-proxies.inc').write_text(rc+'\nstatic const size_t ksu_rc_len = sizeof(KERNEL_SU_RC)-1;\n'+proxies)
subprocess.run(['cc','-std=gnu11','-Wall','-Wextra','-I',str(args.work),str(Path(__file__).with_name('test.c')),'-o',str(args.work/'test')],check=True)
subprocess.run([str(args.work/'test')],check=True)
