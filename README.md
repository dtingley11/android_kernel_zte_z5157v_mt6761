# ZTE Blade A3 Prime (Z5157V) MT6761 kernel port

Linux 4.9.190 vendor-source port with KernelSU Next v1.0.8 and SUSFS v1.5.5.
Uses source and LSM hooks; kprobes are disabled.

The stock-based Z5157V configuration and KSU/SUSFS hook objects compile.
A separate configuration with five available panel drivers links `vmlinux`
and builds the mango device trees. The complete stock configuration is
blocked by the missing ER68577 BOE display driver. Device boot, hardware,
KernelSU and SUSFS operation have not been tested.

See [source revisions, build instructions and validation](docs/z5157v.md).
This repository contains no verified flashable image.
