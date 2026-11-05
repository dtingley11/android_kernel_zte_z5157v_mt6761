# KernelSU Next v3.4.2 ARM32 experiment

This branch starts from stock `main` at
`5feb8e5b222046e92480cb2bd45bbbbf04f1b91e`. It does not replace `ksu_added`
or the published v1.0.8/v1.5.5 release. No experimental boot image or AK3
installer is produced.

## Source and changes

`KernelSU-Next` contains upstream v3.4.2 source at
`4c706b5938665866ebe16944a481a7b91e3396af`, including the kernel, manager,
daemon, shared UAPI and upstream licenses. `UPSTREAM.json` records the ARM32
BusyBox asset reused from official v1.0.8 source at
`9d9f9ed5d5f3a66a2f44e24c926075554f9275ce`.

- Separate `z5157v_next_experimental_defconfig` enables KSU compiler checks
  with kprobes disabled. It does not implement manual hooks. The normal
  device defconfig stays stock.
- Linux 4.9 header fallbacks, poll types/event masks, the vendor task-work
  notification argument and read/write offset adapters are added. SELinux
  generated headers are prepared before KSU objects compile.
- Kernel, ARM32 manager and daemon versions are pinned to v3.4.2 / 33355
  instead of deriving them from the enclosing vendor repository.
- Manager ABI selection requires `-PksuArm32Experimental=true`. Daemon
  changes add ARM32 asset selection, ARM SIGSYS return-register handling,
  target-correct bindgen includes and a 32-bit `timespec` conversion.

The existing SUSFS port is not mixed into this experiment. Latest Next's
GKI-oriented SUSFS LKM code is not a replacement for this device's legacy
filesystem integration.

Kernel SELinux implementation and policy are unchanged. SELinux remains
enforcing by default, module-signature enforcement remains enabled, and
KSU manager-signature and authorization checks have not been bypassed.

## Local results

- Both manager native libraries compile to ELF32 ARM using Android NDK r29
  (`29.0.14206865`), targeting API 26.
- Release-profile `ksud` compiles for `armv7-linux-androideabi` using Rust
  1.99.1 and the same NDK.
- The complete debug manager APK compiles with Gradle 9.2.0 / Java 21.
  APK inspection confirms only `armeabi-v7a` native libraries, minimum API
  26, version 33355 and a valid APK v2 signature. It has not been installed
  on a device. Its debug certificate does not match the upstream certificate
  trusted by the kernel; a usable build needs a matching dedicated signing
  identity and kernel certificate configuration.
- Kernel object compilation fails with pinned AOSP GCC 4.9
  (`c348b64ea1e2015a576485aa787dc70dda9ef396`). Partial object compilation
  is not a linked or bootable kernel.

## Remaining kernel blockers

1. No ARM32 syscall backend exists in latest Next. Its wrappers assume newer
   `pt_regs` entry points, while this 4.9 ARM kernel uses direct arguments.
   A manual adapter must cover execve/execveat, stat64, access, read, UID
   transitions and reboot/fd installation without probes or duplicate hooks.
   Casting the old syscall table to the newer callback type is incorrect.
2. Latest LSM code assumes hlist hook storage; the vendor tree uses
   list-head storage. Its memory-patching backend also lacks ARM32 support.
   Normal built-in LSM registration needs review instead of writing through
   assumed hook layouts.
3. SELinux code assumes `selinux_state`, newer policy/sidtab structures and
   AVC/MLS interfaces absent here. Extended-permission layouts differ too.
   These need reviewed backports, preserving security checks.
4. File wrappers require newer file-operation members,
   `alloc_file_pseudo()` and `security_inode_init_security_anon()`. The latter
   performs security labeling/permission checks and cannot be omitted.
   Other missing helpers include nofault-copy and allocation interfaces.
5. The old seccomp implementation has no action-cache layout compatible with
   the newer copied filter structure. A correct integration must retain
   filtering and handle the KSU control interface deliberately.

## Component checks

`ci/next-experimental.py` builds individual components and records results
in `reports/STATUS.json`; it never creates flashable packages. The separate
`next-experimental.yml` workflow runs kernel, native-library and daemon
checks independently, uploading diagnostic logs. Kernel failure remains a
failed job.

```sh
python3 ci/next-experimental.py kernel --work /path/to/empty/kernel-work
ANDROID_NDK_HOME=/path/to/ndk/29.0.14206865 \
  python3 ci/next-experimental.py native --work /path/to/native-work
RUSTUP_TOOLCHAIN=1.99.1 ANDROID_NDK_HOME=/path/to/ndk/29.0.14206865 \
  python3 ci/next-experimental.py daemon --work /path/to/daemon-work
```

For a manager compile check, copy the ARM32 daemon to
`KernelSU-Next/manager/app/src/main/jniLibs/armeabi-v7a/libksud.so`, then run
`./gradlew -PksuArm32Experimental=true assembleDebug` in the manager directory.
Compile checks do not establish device boot, root authorization, modules or
SUSFS behavior.
