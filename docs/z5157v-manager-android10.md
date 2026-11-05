# Android 10 manager fix

The official KernelSU Next v1.0.8 manager crashes on the Z5157V with
`NoSuchMethodError: IUserManager.getUsers(ZZZ)`. Its MMRL platform dependency
calls a three-argument hidden API, while this Android 10 firmware exposes
only the older one-argument method.

`ci/manager.py` fetches KSU v1.0.8 at
`9d9f9ed5d5f3a66a2f44e24c926075554f9275ce` and MMRL at
`2bb00b3c2b9e3e9705a5d7c4d2d6ece1d8ba36c4`. It rebuilds the platform module
with runtime method selection, preserving the rest of the manager's native
kernel interface. Legacy/modern signatures and permission failures have
local tests. The same helper successfully enumerated both users against the
phone's actual framework through an ADB-shell probe.

The APK is a separate application, `com.rifsxd.ksunext.z5157v`, so the official
manager's installation and data can be retained. A dedicated certificate
signs the APK. Its public fingerprint and size are recorded in
`ci/manager/manager.json`; the matching kernel builds restrict the manager
to that package and certificate. Certificate checks remain enabled. Keep the
private keystore and password for future updates; they are not committed.

The patched manager requires its matching kernel for root management. The
existing released kernel trusts the official certificate instead. No kernel
was flashed as part of the manager build. Stock SELinux enforcing settings,
module-signature enforcement and disabled kprobes are retained.

The separate Actions workflow builds stock, the signed manager, KSU, then
KSU+SUSFS. It is scoped to the verified v1.0.8/v1.5.5 port; newer KSU revisions
require a separate reviewed recipe. Build logs and matching APK/AK3 artifacts
are uploaded. The v3.4.2 experiment stays on its own branch.
