# Kernel build variants

The Actions workflow builds stock, KernelSU Next, then KernelSU Next + SUSFS
from the triggering device-kernel commit. Stock retains the recovered device
support and removes both root integrations. Each variant uses a separate
source and output directory.

KSU defaults to the latest `legacy` branch and SUSFS to the latest
`kernel-4.9-v2` branch when each job fetches them. No fallback revision is
substituted. The KSU+SUSFS job still attempts preparation after a KSU failure.
Workflow dispatch accepts alternate branch names, tags or commit hashes.

The port patches currently support KSU
`9d9f9ed5d5f3a66a2f44e24c926075554f9275ce` and SUSFS
`41ba0b533b8524a0ba95a5952506a75f17355450`. Current upstream branches have
different interfaces, so their patch checks can fail. Each artifact records
the fetched revisions and includes the failing patch-check logs. Partial
patches are never compiled, and preparation failures remain failed jobs.

`ci/patches` contains the KSU source hooks, SUSFS vendor filesystem port,
ARM32/API compatibility changes and Next-specific SUSFS interfaces. The SUSFS
filesystem recipe checks the fetched upstream kernel-patch hash before using
its vendor adaptation. Manager signature checks, source hooks, SELinux and
module-signing enforcement are retained; kprobes remain disabled.

Successful artifacts contain `zImage-dtb`, the device trees, configuration,
symbol map, revisions and checksums. They are kernel payloads, not Android boot
images. Logs are uploaded on both success and failure. GCC 4.9 is fetched from
AOSP at `c348b64ea1e2015a576485aa787dc70dda9ef396`.
