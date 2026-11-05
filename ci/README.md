# Kernel build variants

For the current ARM32 Next experiment and signed APK/AK3 artifacts, see
[the experimental build documentation](../docs/ksu-next-experimental.md).
The recipes below describe the separate stock/v1.0.8 build workflow.

The Actions workflow builds stock, KernelSU Next, then KernelSU Next + SUSFS.
It fetches the clean `main` kernel branch, preserving its display driver and
stock defconfig. The resolved stock SHA is reused by both patched variants.
Each variant uses a separate source and output directory. Workflow dispatch
can select another clean kernel branch, tag or commit with `kernel_ref`.

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

Successful builds are also packaged using the latest osm0sis/AnyKernel3
`master` revision (overridable with `anykernel_ref`). The ZIP checks the
Z5157/Z5157V device identifiers and targets the non-A/B `boot` partition.
The ZIP carries the raw ARM Image and appended kernel DTB; magiskboot
restores the installed boot image's kernel format. It preserves the installed
appended DTB, using the bundled DTB only when none is present. It also retains
ramdisk content, command line and separate DTB/DTBO sections. No ramdisk edits, bundled modules or vbmeta-partition patches are
applied. The AnyKernel3 revision, license and checksums are included. ZIP
structure is checked during packaging; flashing and boot remain untested.
