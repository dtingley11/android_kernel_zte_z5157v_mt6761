#!/usr/bin/env python3
"""Prepare fresh stock/KSU/SUSFS trees and build Z5157V kernel artifacts."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tarfile

ROOT = Path(__file__).resolve().parent.parent
PATCHES = ROOT / "ci/patches"
KSU_URL = "https://github.com/KernelSU-Next/KernelSU-Next.git"
SUSFS_URL = "https://github.com/wxx9248/susfs4ksu.git"
TOOLCHAIN_URL = "https://android.googlesource.com/platform/prebuilts/gcc/linux-x86/arm/arm-linux-androideabi-4.9"
TOOLCHAIN_SHA = "c348b64ea1e2015a576485aa787dc70dda9ef396"
SUSFS_PATCH_SHA = "b11b7f4cb6d6ca0a5b8f447ef66ed35eebdddaa2b01f6cf9a88df370d5ad10b9"
SUSFS_FILES = ("fs/susfs.c", "include/linux/susfs.h", "include/linux/susfs_def.h")
OPTIONAL_SYMBOLS = {"__ddp_mem_test", "mlog_get_buffer", "report_hub_dmd"}


def run(argv, cwd, log, check=True):
    with log.open("w") as stream:
        proc = subprocess.run([str(a) for a in argv], cwd=cwd, stdout=stream,
                              stderr=subprocess.STDOUT)
    if proc.returncode and check:
        print(log.read_text(errors="replace")[-6000:], file=sys.stderr)
        raise RuntimeError(f"Command failed ({proc.returncode}); see {log.name}")
    return proc.returncode


def fetch(url, ref, dest, logs, label):
    if not re.fullmatch(r"[A-Za-z0-9_./-]{1,200}", ref) or ref.startswith("-"):
        raise ValueError(f"Invalid {label} Git ref")
    subprocess.run(["git", "init", "-q", str(dest)], check=True)
    subprocess.run(["git", "-C", str(dest), "remote", "add", "origin", url], check=True)
    run(["git", "fetch", "--depth=1", "--no-tags", "origin", ref], dest,
        logs / f"fetch-{label}.log")
    run(["git", "checkout", "--detach", "FETCH_HEAD"], dest, logs / f"checkout-{label}.log")
    return subprocess.check_output(["git", "-C", str(dest), "rev-parse", "HEAD"], text=True).strip()


def apply_patch(src, name, logs, reverse=False, apply=True):
    patch = PATCHES / name
    label = ("remove-" if reverse else "apply-") + name
    root = Path(subprocess.check_output(
        ["git", "rev-parse", "--show-toplevel"], cwd=src, text=True).strip())
    args = ["git", "apply", "--whitespace=nowarn"]
    relative = src.relative_to(root)
    if relative != Path("."):
        args.append("--directory=" + str(relative))
    if reverse:
        args.append("--reverse")
    result = run([*args, "--check", patch], root, logs / f"{label}.log", check=False)
    if result:
        return False
    if apply:
        run([*args, patch], root, logs / f"{label}-result.log")
    return True


def config_values(path):
    values = {}
    for line in path.read_text().splitlines():
        if line.startswith("CONFIG_") and "=" in line:
            key, value = line.split("=", 1)
            values[key[7:]] = value
        elif line.startswith("# CONFIG_") and line.endswith(" is not set"):
            values[line[9:-11]] = "n"
    return values


def prepare(args, report, logs):
    src = args.work / "src"
    if src.exists():
        raise RuntimeError("Source directory already exists; use a fresh work directory")
    server = os.environ.get("GITHUB_SERVER_URL", "https://github.com").rstrip("/")
    repository = os.environ.get("GITHUB_REPOSITORY", "dtingley11/android_kernel_zte_z5157v_mt6761")
    report["kernel_revision"] = fetch(server + "/" + repository + ".git", args.kernel_ref,
                                        src, logs, "device-kernel")
    if (src / "KernelSU-Next/kernel").exists() or (src / "fs/susfs.c").exists():
        raise RuntimeError("The selected kernel ref is not a clean stock source branch")
    defconfig = src / "arch/arm/configs/z5157v_defconfig"
    if args.variant == "stock":
        report["status"] = "prepared"
        return

    upstream = args.work / "upstream"
    upstream.mkdir()
    report["ksu_revision"] = fetch(KSU_URL, args.ksu_ref, upstream / "ksu", logs, "ksu")
    report["susfs_revision"] = None
    if args.variant == "ksu-susfs":
        report["susfs_revision"] = fetch(SUSFS_URL, args.susfs_ref,
                                           upstream / "susfs", logs, "susfs")
    kernel = src / "KernelSU-Next/kernel"
    kernel.parent.mkdir()
    shutil.copytree(upstream / "ksu/kernel", kernel, symlinks=True)
    failures = []
    ksu_ok = apply_patch(kernel, "ksu-arm32.patch", logs)
    if not ksu_ok:
        failures.append("KernelSU ARM32/Linux 4.9 compatibility patch does not apply to the fetched revision")
    if args.variant == "ksu-susfs":
        susfs = upstream / "susfs/kernel_patches"
        for path in SUSFS_FILES:
            target = src / path
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(susfs / path, target)
        if not apply_patch(src, "susfs-compat.patch", logs):
            failures.append("SUSFS compatibility patch does not apply to the fetched filesystem sources")
        native_patch = susfs / "50_add_susfs_in_kernel-4.9.patch"
        report["susfs_kernel_patch_sha256"] = hashlib.sha256(native_patch.read_bytes()).hexdigest()
        if report["susfs_kernel_patch_sha256"] != SUSFS_PATCH_SHA:
            # Preserve the upstream patch-check diagnostics too, rather than
            # silently substituting the older vendor-port patch.
            run(["git", "apply", "--check", native_patch], src,
                logs / "upstream-susfs-kernel-check.log", check=False)
            failures.append("Fetched SUSFS kernel patch differs from the supported vendor-port patch; port review required")
        if ksu_ok and not apply_patch(kernel, "ksu-susfs.patch", logs):
            failures.append("KernelSU/SUSFS interface patch does not apply")
    report["compatibility_failures"] = failures
    if failures:
        raise RuntimeError("; ".join(failures))
    if not apply_patch(src, "kernel-ksu.patch", logs):
        raise RuntimeError("KernelSU source hooks do not apply to the device tree")
    if args.variant == "ksu-susfs" and not apply_patch(src, "kernel-susfs.patch", logs):
        raise RuntimeError("SUSFS filesystem hooks do not apply to the device tree")
    feature_lines = (ROOT / "ci/ksu.config").read_text().splitlines()
    if args.variant == "ksu-susfs":
        feature_lines.extend((ROOT / "ci/susfs.config").read_text().splitlines())
    with defconfig.open("a") as stream:
        stream.write("\n".join(feature_lines) + "\n")
    report["status"] = "prepared"


def build(args, report, logs):
    if report.get("status") != "prepared":
        raise RuntimeError("Preparation did not succeed; refusing to compile partial patches")
    src = args.work / "src"
    toolchain = Path(args.toolchain).resolve() if args.toolchain else args.work / "toolchain"
    if not args.toolchain:
        report["toolchain_revision"] = fetch(TOOLCHAIN_URL, TOOLCHAIN_SHA, toolchain, logs, "toolchain")
    else:
        report["toolchain_revision"] = subprocess.check_output(
            ["git", "-C", str(toolchain), "rev-parse", "HEAD"], text=True).strip()
        if report["toolchain_revision"] != TOOLCHAIN_SHA:
            raise RuntimeError("Local toolchain revision differs from the verified GCC 4.9 build")
    prefix = str(toolchain / "bin/arm-linux-androideabi-")
    out = args.work / "out"
    make = ["make", f"O={out}", "ARCH=arm", f"CROSS_COMPILE={prefix}", "HOSTCFLAGS=-O2 -fcommon"]
    run([*make, "z5157v_defconfig"], src, logs / "configure.log")
    values = config_values(out / ".config")
    expected = {"KSU": args.variant != "stock", "KSU_SUSFS": args.variant == "ksu-susfs",
                "KPROBES": False, "KSU_KPROBES_HOOK": False,
                "SECURITY_SELINUX": True, "MODULE_SIG_FORCE": True}
    if args.variant != "stock":
        expected.update(KSU_MANUAL_HOOK=True, KSU_LSM_SECURITY_HOOKS=True)
    for key, enabled in expected.items():
        if (values.get(key, "n") == "y") != enabled:
            raise RuntimeError(f"Unexpected CONFIG_{key}={values.get(key, 'absent')}")
    if values.get("SECURITY_SELINUX_BOOTPARAM_VALUE") != "1":
        raise RuntimeError("Stock SELinux enforcing boot default was lost")
    panels = values.get("CUSTOM_KERNEL_LCM", "").strip('"').split()
    if len(panels) != 6:
        raise RuntimeError("The six stock panel selections were not retained")
    run([*make, f"-j{args.jobs}", "zImage-dtb", "dtbs", "modules"], src, logs / "build.log")
    nm = subprocess.check_output([prefix + "nm", "-u", str(out / "vmlinux")], text=True)
    report["undefined_symbols"] = nm.splitlines()
    for line in nm.splitlines():
        fields = line.split()
        if len(fields) != 2 or fields[0] != "w" or fields[1] not in OPTIONAL_SYMBOLS:
            raise RuntimeError(f"Unexpected unresolved kernel symbol: {line}")
    symbols = subprocess.check_output([prefix + "nm", str(out / "vmlinux")], text=True)
    for symbol, present in (("ksu_core_init", args.variant != "stock"),
                            ("susfs_init", args.variant == "ksu-susfs")):
        if bool(re.search(r"\b" + symbol + r"$", symbols, re.M)) != present:
            raise RuntimeError(f"Unexpected linked state for {symbol}")
    if re.search(r"\b(register_kprobe|register_kretprobe)$", symbols, re.M):
        raise RuntimeError("Unexpected kprobe implementation in the linked kernel")
    report["status"] = "built"
    report["stock_panel_count"] = len(panels)
    report["device_tested"] = False
    report["android_boot_image"] = False
    report["enabled_susfs_features"] = [k for k, v in values.items() if k.startswith("KSU_SUSFS") and v == "y"]
    package = args.work / "package"
    package.mkdir()
    for source, target in (("arch/arm/boot/zImage-dtb", "zImage-dtb"),
                           ("arch/arm/boot/dts/mango/mt6761.dtb", "mt6761.dtb"),
                           ("arch/arm/boot/dts/mango/k61v1_32_bsp_hdp.dtb", "k61v1_32_bsp_hdp.dtb"),
                           (".config", "kernel.config"), ("System.map", "System.map")):
        shutil.copy2(out / source, package / target)
    (package / "BUILD.json").write_text(json.dumps(report, indent=2) + "\n")
    (package / "SHA256SUMS").write_text("".join(
        hashlib.sha256(p.read_bytes()).hexdigest() + "  " + p.name + "\n"
        for p in sorted(package.iterdir()) if p.is_file()))
    with tarfile.open(logs / f"z5157v-{args.variant}.tar.gz", "w:gz") as stream:
        stream.add(package, arcname=f"z5157v-{args.variant}")


def summary(report, path):
    lines = [f"### Z5157V — {report['variant']}", "", f"Status: **{report['status']}**", ""]
    if report.get("job_status"):
        lines.append(f"Job result before summary: **{report['job_status']}**")
    for key in ("workflow_revision", "kernel_ref", "kernel_revision", "ksu_ref", "ksu_revision", "susfs_ref", "susfs_revision", "toolchain_revision", "anykernel_ref", "anykernel_revision"):
        if report.get(key):
            lines.append(f"- {key}: `{report[key]}`")
    for failure in report.get("compatibility_failures", []):
        lines.append(f"- {failure}")
    if report.get("error") and not report.get("compatibility_failures"):
        lines.extend(["", report["error"]])
    lines.extend(["", "Artifacts contain build logs and resolved revisions. Successful packaging adds an AnyKernel3 ZIP; device operation remains untested.", ""])
    with path.open("a") as stream:
        stream.write("\n".join(lines))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("prepare", "build", "summary"))
    parser.add_argument("--variant", required=True, choices=("stock", "ksu", "ksu-susfs"))
    parser.add_argument("--work", required=True, type=Path)
    parser.add_argument("--kernel-ref", default="main")
    parser.add_argument("--ksu-ref", default="legacy")
    parser.add_argument("--susfs-ref", default="kernel-4.9-v2")
    parser.add_argument("--toolchain", help="Existing verified toolchain for local checks")
    parser.add_argument("--jobs", type=int, default=max(1, os.cpu_count() or 1))
    parser.add_argument("--summary", type=Path)
    args = parser.parse_args()
    args.work = args.work.resolve()
    logs = args.work / "reports"
    logs.mkdir(parents=True, exist_ok=True)
    state = logs / "BUILD.json"
    if state.exists():
        report = json.loads(state.read_text())
    else:
        report = {"variant": args.variant, "status": "pending",
                  "workflow_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
                  "kernel_ref": args.kernel_ref,
                  "ksu_ref": args.ksu_ref if args.variant != "stock" else None,
                  "susfs_ref": args.susfs_ref if args.variant == "ksu-susfs" else None}
    try:
        if args.command == "summary":
            if os.environ.get("CI_JOB_STATUS"):
                report["job_status"] = os.environ["CI_JOB_STATUS"]
            summary(report, args.summary or Path(os.environ["GITHUB_STEP_SUMMARY"]))
        elif args.command == "prepare":
            prepare(args, report, logs)
        else:
            build(args, report, logs)
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as exc:
        report["status"] = args.command + "_failed"
        report["error"] = str(exc)
        print(str(exc), file=sys.stderr)
        return 1
    finally:
        state.write_text(json.dumps(report, indent=2) + "\n")
        if args.command == "prepare" and report.get("kernel_revision") and os.environ.get("GITHUB_OUTPUT"):
            with Path(os.environ["GITHUB_OUTPUT"]).open("a") as stream:
                stream.write("kernel_revision=" + report["kernel_revision"] + "\n")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
