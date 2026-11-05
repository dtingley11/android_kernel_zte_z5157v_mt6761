# Module startup and ARM32 SUSFS compatibility

On the phone, root grants and SUSFS v1.5.5 version/feature queries work.
Installed modules remain in `/data/adb/modules_update` with update markers,
and the daemon's boot-log directory is absent. A second module has the same
activation problem. Both depend on the daemon running at boot.

The v1.0.8 integration depended on intercepting `atrace.rc`. This branch
backports the main `init.rc` EOF-appending design from KernelSU Next legacy
`b933b1f728116a456fbebf27b6a8772a640cdf23`, keeping the v1.0.8 commands and
manual-hook interface. It recognizes `/init.rc` and
`/system/etc/init/hw/init.rc`. Original contents are returned unchanged;
KSU's boot actions are appended after EOF. Short buffers, zero-length reads,
read failures and partial user-copy faults are tested against the actual
proxy functions for both read APIs. Device logs from the updated kernel
confirm init parses these actions and attempts all three boot stages.

The remaining failure is `cannot execve('/data/adb/ksud'): Permission denied`.
This vendor kernel's `check_nnp_nosuid()` rejects unbounded SELinux transitions
on nosuid mounts. `/data` is nosuid, so the explicit init-to-su transition
fails before the daemon runs. Root shells already in the su domain can
execute the same daemon.

The boot actions now enter the su domain through `/system/bin/sh`, then
`exec` the daemon with the original stage argument. The second execution
stays in the same domain. This keeps `/data` nosuid, SELinux enforcing and
the kernel's transition checks unchanged. `exec-probe.c` reproduced the
direct-launch denial and verified the shell launch succeeds on the phone,
using only `ksud --version` in an isolated child. Host tests verify command
quoting and stage arguments. Full boot-stage execution with the final
kernel still needs a reboot test.

The installed SUSFS R28 module also contains an ARM64-only `ksu_susfs`, which
cannot execute on the Z5157V's ARM32 kernel. Its updater downloads the same
ARM64 binary. The matching ARM32 v1.5.5 tool was tested on the phone and
successfully reported the kernel version, NON-GKI variant and all seven
enabled features.

`ci/susfs-module.py` builds that tool and adapts the official R28 module ZIP,
pinned by URL and SHA-256. Installation requires ARM32 and SUSFS v1.5.5.
It bundles the compatible executable, skips the unsupported SUS_SU helper,
and prevents the ARM64 updater from replacing it. Existing configuration
handling and upstream module scripts are retained. The original authors,
source provenance and userspace-tool license are included.

The updated workflow builds the patched manager, compatibility module and
matching KSU kernels. The Android 10 manager signing identity is unchanged.
Kprobes stay disabled, and SELinux enforcing defaults and module-signature
enforcement remain enabled. The v3.4.2 experiment is separate.

A successful build and the userspace probe do not prove that modules start
at boot. After installing the updated kernel and ARM32 module, verify a
full reboot clears staging, produces KSU boot logs, and runs the module's
post-fs-data/service stages. Update flags must not be removed just to change
the manager's pending label.

## SUSFS WebUI on Android 10

The stock WebView is 74.0.3729.186. R28 uses top-level await and newer class
syntax, so its feature-status link can remain hidden when the main script
cannot run. The compatibility package bundles the original frontend for
Chrome 74, moves initialization into an async function and obtains its
feature-gating version directly from the kernel. It preserves the original
status rules and settings. The build uses esbuild 0.28.2 with a lockfile.

Device checks confirmed module activation, all four boot-script stages,
SUSFS v1.5.5 feature queries, automatic marking of KSU mounts and per-app
unmount activity. The rebuilt feature-status page rendered on WebView 74
and matched the seven enabled kernel features. Other spoofing features
still need individual runtime tests; enabled status is a capability query.
