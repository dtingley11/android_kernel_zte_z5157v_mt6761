#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 2 || $# -gt 3 ]]; then
    echo "Usage: CROSS_COMPILE=/path/to/prefix- $0 DEFCONFIG OUT_DIR [objects|image]" >&2
    exit 2
fi

repo_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
kernel_dir="$repo_dir"
defconfig=$1
out_dir=$(realpath -m -- "$2")
mode=${3:-image}
build_arch=${ARCH:-arm}
: "${CROSS_COMPILE:?Set CROSS_COMPILE to the target compiler prefix}"

case "$mode" in
    objects|image) ;;
    *) echo "Unknown build mode: $mode" >&2; exit 2 ;;
esac

mkdir -p -- "$out_dir"
make_args=(-C "$kernel_dir" "O=$out_dir" "ARCH=$build_arch"
    "CROSS_COMPILE=$CROSS_COMPILE" "HOSTCFLAGS=${HOSTCFLAGS:--O2 -fcommon}")
config_fragments=()
if [[ -n "${KERNEL_EXTRA_CONFIG:-}" ]]; then
    config_fragments+=("$(realpath -- "$KERNEL_EXTRA_CONFIG")")
fi

make "${make_args[@]}" "$defconfig"
if [[ ${#config_fragments[@]} -gt 0 ]]; then
    (cd "$kernel_dir" && scripts/kconfig/merge_config.sh -m -O "$out_dir" \
        "$out_dir/.config" "${config_fragments[@]}")
fi
make "${make_args[@]}" olddefconfig

for option in KSU KSU_MANUAL_HOOK KSU_LSM_SECURITY_HOOKS SECURITY_SELINUX; do
    if ! grep -qx "CONFIG_$option=y" "$out_dir/.config"; then
        echo "Required option CONFIG_$option was not enabled; check the base defconfig." >&2
        exit 1
    fi
done
if grep -Eq '^CONFIG_(KPROBES|KSU_KPROBES_HOOK)=y$' "$out_dir/.config"; then
    echo "Kprobes must be disabled for this integration." >&2
    exit 1
fi

hook_objects=(fs/exec.o fs/open.o fs/stat.o fs/read_write.o fs/namespace.o
    drivers/input/input.o)
if grep -qx 'CONFIG_KSU_SUSFS=y' "$out_dir/.config"; then
    hook_objects+=(fs/susfs.o fs/dcache.o fs/namei.o fs/notify/fdinfo.o
        fs/proc/cmdline.o fs/proc/fd.o fs/proc/task_mmu.o fs/proc_namespace.o
        fs/readdir.o fs/statfs.o kernel/kallsyms.o kernel/sys.o)
fi
make "${make_args[@]}" -j"${JOBS:-$(nproc)}" KernelSU-Next/kernel/ "${hook_objects[@]}"

link_inputs=("$out_dir/KernelSU-Next/kernel/kernelsu.o")
for object in "${hook_objects[@]}"; do
    link_inputs+=("$out_dir/$object")
done
"${CROSS_COMPILE}ld" -r -o "$out_dir/ksu-hook-linkcheck.o" "${link_inputs[@]}"
"${CROSS_COMPILE}nm" -u "$out_dir/ksu-hook-linkcheck.o" > "$out_dir/ksu-hook-undefined.txt"
if grep -Eq '[[:space:]](ksu_|kernelsu_|susfs_)' "$out_dir/ksu-hook-undefined.txt"; then
    echo "Unresolved KernelSU/SUSFS hook symbols; see $out_dir/ksu-hook-undefined.txt" >&2
    exit 1
fi
"${CROSS_COMPILE}nm" "$out_dir/KernelSU-Next/kernel/kernelsu.o" > "$out_dir/ksu-symbols.txt"
if grep -Eq '[[:space:]](register_kprobe|register_kretprobe|unregister_kprobe|unregister_kretprobe)$' \
    "$out_dir/ksu-symbols.txt"; then
    echo "Unexpected kprobe dependency in KernelSU." >&2
    exit 1
fi

echo "KernelSU and source-hook objects compiled and linked together without unresolved KernelSU/SUSFS hooks."
if [[ "$mode" == image ]]; then
    case "$build_arch" in
        arm)
            image_target=zImage
            if grep -qx 'CONFIG_BUILD_ARM_APPENDED_DTB_IMAGE=y' "$out_dir/.config"; then
                image_target=zImage-dtb
            fi
            ;;
        arm64) image_target=Image.gz ;;
        *) image_target=bzImage ;;
    esac
    make "${make_args[@]}" -j"${JOBS:-$(nproc)}" "$image_target" dtbs
fi
