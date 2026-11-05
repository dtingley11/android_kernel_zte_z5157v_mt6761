#!/usr/bin/env python3
"""Package a successful kernel build with freshly fetched AnyKernel3 tools."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import zipfile

from build import fetch

ROOT = Path(__file__).resolve().parent.parent
ANYKERNEL_URL = "https://github.com/osm0sis/AnyKernel3.git"
LABELS = {"stock": "Stock", "ksu": "KernelSU Next", "ksu-susfs": "KernelSU Next + SUSFS"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--variant", required=True, choices=LABELS)
    parser.add_argument("--work", required=True, type=Path)
    parser.add_argument("--anykernel-ref", default="master")
    parser.add_argument("--anykernel-source", type=Path, help="Existing upstream checkout for local packaging")
    args = parser.parse_args()
    work = args.work.resolve()
    reports = work / "reports"
    state = reports / "BUILD.json"
    report = json.loads(state.read_text())
    report["anykernel_ref"] = args.anykernel_ref
    try:
        if report.get("variant") != args.variant or report.get("status") != "built":
            raise RuntimeError("Only a successful matching kernel build can be packaged")
        upstream = args.anykernel_source.resolve() if args.anykernel_source else work / "anykernel-upstream"
        if args.anykernel_source:
            revision = subprocess.check_output(["git", "-C", str(upstream), "rev-parse", "HEAD"], text=True).strip()
        else:
            revision = fetch(ANYKERNEL_URL, args.anykernel_ref, upstream, reports, "anykernel")
        report["anykernel_revision"] = revision
        template = (ROOT / "ci/anykernel/anykernel.sh").read_text()
        script = template.replace("@VARIANT@", LABELS[args.variant])
        stage = work / "anykernel-package"
        stage.mkdir()
        for name in ("META-INF", "tools"):
            shutil.copytree(upstream / name, stage / name, symlinks=True)
        shutil.copy2(upstream / "LICENSE", stage / "LICENSE")
        shutil.copy2(work / "out/arch/arm/boot/Image", stage / "Image")
        shutil.copy2(work / "package/mt6761.dtb", stage / "kernel_dtb")
        report["anykernel_image_sha256"] = hashlib.sha256((stage / "Image").read_bytes()).hexdigest()
        report["anykernel_kernel_dtb_sha256"] = hashlib.sha256((stage / "kernel_dtb").read_bytes()).hexdigest()
        (stage / "anykernel.sh").write_text(script)
        (stage / "anykernel.sh").chmod(0o755)
        report["status"] = "packaged"
        report["package_type"] = "AnyKernel3 ZIP targeting the non-A/B boot partition"
        report["ramdisk_source"] = "installed boot image"
        report["device_tested"] = False
        (stage / "BUILD.json").write_text(json.dumps(report, indent=2) + "\n")
        files = sorted(p for p in stage.rglob("*") if p.is_file())
        required = {"anykernel.sh", "Image", "kernel_dtb", "LICENSE", "tools/ak3-core.sh",
                    "tools/magiskboot", "META-INF/com/google/android/update-binary"}
        if not required.issubset({str(p.relative_to(stage)) for p in files}):
            raise RuntimeError("AnyKernel3 checkout is missing required installer files")
        # Separate Android DTB tables and overlays stay in the installed image.
        # A raw dtb from the build must not replace an Android DT table here.
        (stage / "SHA256SUMS").write_text("".join(
            hashlib.sha256(p.read_bytes()).hexdigest() + "  " + str(p.relative_to(stage)) + "\n"
            for p in files))
        manager_suffix = "-android10-manager" if report.get("manager") else ""
        init_suffix = "-init-rc" if report.get("init_rc_proxy_upstream_revision") else ""
        if report.get("init_rc_launcher") == "system-shell":
            init_suffix += "-shell"
        uname_suffix = "-stock-uname" if report.get("uname", {}).get("mode") == "stock" else ""
        archive = reports / f"AnyKernel3-Z5157V-{args.variant}-{report['kernel_revision'][:9]}{manager_suffix}{init_suffix}{uname_suffix}.zip"
        temporary = work / "anykernel-package.zip"
        with zipfile.ZipFile(temporary, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as stream:
            for path in sorted(stage.rglob("*")):
                if path.is_file():
                    stream.write(path, str(path.relative_to(stage)))
        with zipfile.ZipFile(temporary) as stream:
            if stream.testzip():
                raise RuntimeError("ZIP integrity check failed")
            if stream.read("Image") != (work / "out/arch/arm/boot/Image").read_bytes():
                raise RuntimeError("Packaged kernel differs from the build output")
            if stream.read("kernel_dtb") != (work / "package/mt6761.dtb").read_bytes():
                raise RuntimeError("Packaged kernel DTB differs from the build output")
            mode = stream.getinfo("META-INF/com/google/android/update-binary").external_attr >> 16
            if not mode & stat.S_IXUSR:
                raise RuntimeError("Installer executable permission was lost")
        digest = hashlib.sha256(temporary.read_bytes()).hexdigest()
        temporary.replace(archive)
        archive.with_suffix(".zip.sha256").write_text(digest + "  " + archive.name + "\n")
        print(archive)
        print("AnyKernel3 revision:", revision)
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as exc:
        report["status"] = "package_failed"
        report["error"] = str(exc)
        print(str(exc), file=sys.stderr)
        return 1
    finally:
        state.write_text(json.dumps(report, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
