# Module startup and ARM32 SUSFS compatibility

On the phone, root grants and SUSFS v1.5.5 version/feature queries work.
Installed modules remain in `/data/adb/modules_update` with update markers,
and the daemon's boot-log directory is absent. A second module has the same
activation problem. This indicates a general boot-stage problem, rather
than successful module activation.

The v1.0.8 integration depended on intercepting `atrace.rc`. This branch
backports the main `init.rc` EOF-appending design from KernelSU Next legacy
`b933b1f728116a456fbebf27b6a8772a640cdf23`, keeping the v1.0.8 commands and
manual-hook interface. It recognizes `/init.rc` and
`/system/etc/init/hw/init.rc`. Original contents are returned unchanged;
KSU's boot actions are appended after EOF. Short buffers, zero-length reads,
read failures and partial user-copy faults are tested against the actual
proxy functions for both read APIs. Device boot-stage execution still needs
verification with this updated kernel.

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
