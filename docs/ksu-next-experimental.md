# KernelSU Next ARM32 experiment

`ksu-next-latest-arm32-experimental` builds current Next legacy kernel code
with v3.4.2 ARM32 userspace on the Z5157V Linux 4.9.190 vendor kernel. It is
separate from the working v1.0.8/SUSFS branches. Device operation is unverified;
this branch does not produce a flashable installer.

## Sources

- KernelSU Next `legacy`: `b933b1f728116a456fbebf27b6a8772a640cdf23`.
- Manager, daemon and shared UAPI, v3.4.2:
  `4c706b5938665866ebe16944a481a7b91e3396af`.
- Stock kernel base: `5feb8e5b222046e92480cb2bd45bbbbf04f1b91e`.
- AOSP ARM GCC 4.9: `c348b64ea1e2015a576485aa787dc70dda9ef396`.
- ARM32 BusyBox from Next v1.0.8:
  `9d9f9ed5d5f3a66a2f44e24c926075554f9275ce`.

The complete sources and licenses are committed. `KernelSU-Next/UPSTREAM.json`
records the upstream revisions and BusyBox checksum. The legacy kernel reports
its upstream-derived version 33318; v3.4.2 manager requires at least 33188. Both
use shared UAPI version 5.

## Compatibility changes

- Manual source hooks cover exec, access, stat, init-rc reads, safe-mode input
  and reboot-based control-descriptor installation. Upstream built-in LSM hooks
  handle UID transitions and package tracking. Kprobes and syscall-table patching
  are disabled.
- Linux 4.9 read/write offsets, namespace-path return types, ARM registers,
  credentials, unmount permissions and SELinux accessors are adapted to the
  vendor interfaces. Source patches replace upstream build-time source rewriting.
- Kernel-side constants use GCC-compatible constant expressions. Userspace keeps
  typed constants for Rust bindgen. Pointer conversions preserve the fixed-width
  control ABI and native ARM32 pointer widths.
- File wrappers allocate private inodes rather than changing the shared anonymous
  inode. SELinux initialization follows Linux v5.15
  `security/selinux/hooks.c:selinux_inode_init_security_anon`, using the existing
  `file` class because the supplied Android 10 policy lacks `anon_inode` and denies
  unknown classes. SID transitions, context validation and CREATE permission
  checks remain enforced. Device validation is still required.
- Init services use the system-shell launcher needed for this device's nosuid
  `/data`, with the current `ksu` SELinux domain. Core and optional module RC
  appending account for partial copies and short reads.
- ARM32 daemon assets, SIGSYS registers, bindgen includes and `timespec`
  conversion are retained from the v3.4.2 experiment. Actual kernel uname matches
  the stock identity recorded in `ci/stock-uname.json`.

SELinux enforcing defaults, module-signature enforcement and manager
certificate/authorization checks remain enabled. The vendor seccomp structures
are unchanged and seccomp filtering remains configured. Authorized KSU processes
use upstream legacy's older-kernel seccomp escape behavior. Pre-init runner
support is unavailable on this kernel and is disabled by upstream detection.

## Local verification

- Full `zImage-dtb`, device-tree and module build passes with pinned GCC 4.9.
- No unresolved KSU symbols. Only the existing optional weak vendor symbols
  `__ddp_mem_test`, `mlog_get_buffer` and `report_hub_dmd` remain.
- Both manager native libraries and release-profile `ksud` compile as ELF32 ARM
  using Android NDK r29 (`29.0.14206865`), API 26 and Rust 1.99.1.
- 91 UAPI constant values/widths and 27 record layouts match unmodified v3.4.2
  under ARM32 NDK Clang. GCC kernel-side values, sizes and alignments agree.
- Actual read proxies pass host tests for original content, optional module RC,
  zero/short reads, errors and partial faults. Private-inode tests exercise
  allocation cleanup, inode isolation, context validation and SELinux denials.
  Manual exec-hook tests cover denied callers, failed credential changes, first
  installation and nested root.

Host tests exercise extracted source functions with controlled kernel-interface
stubs; they do not establish runtime SELinux or VFS behavior.

## Remaining work

A usable manager needs a matching signing identity and kernel certificate
configuration, plus Android 10 launch/WebUI testing. The previously compiled
v3.4.2 debug APK does not match the kernel's trusted certificate. This experiment
has not been installed or booted on the phone.

Boot, root authorization and denial, file-wrapper ownership/reopening, SELinux
policy loading, module startup/mounts and recovery all need device testing.
Manual hooks do not provide the probe-based syscall tracing or ADB-root exec
interception paths.

SUSFS is not integrated into this experimental branch. The verified v1.5.5
filesystem integration remains on the stable branch; it needs separate adaptation
to the current Next interfaces after the base port is validated.

## CI

`next-experimental.yml` independently builds the full kernel, native libraries
and daemon, uploading diagnostics and source/output hashes. Failed builds remain
failed jobs. No release or installer is published.

```sh
python3 ci/next-experimental.py kernel --work /path/to/kernel-work \
  --ndk /path/to/ndk/29.0.14206865
python3 ci/next-experimental.py native --work /path/to/native-work \
  --ndk /path/to/ndk/29.0.14206865
RUSTUP_TOOLCHAIN=1.99.1 python3 ci/next-experimental.py daemon \
  --work /path/to/daemon-work --ndk /path/to/ndk/29.0.14206865
```
