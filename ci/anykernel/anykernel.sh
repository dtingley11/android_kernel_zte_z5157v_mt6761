### AnyKernel3 configuration for ZTE Blade A3 Prime (Z5157V)
# AnyKernel3 by osm0sis; see the bundled LICENSE.
properties() { '
kernel.string=ZTE Blade A3 Prime (@VARIANT@)
do.devicecheck=1
do.modules=0
do.systemless=0
do.cleanup=1
do.cleanuponabort=0
device.name1=Z5157
device.name2=Z5157V
supported.versions=
supported.patchlevels=
supported.vendorpatchlevels=
'; }

BLOCK=boot;
IS_SLOT_DEVICE=0;
RAMDISK_COMPRESSION=auto;
PATCH_VBMETA_FLAG=0;
NO_VBMETA_PARTITION_PATCH=1;
NO_MAGISK_CHECK=1;

. tools/ak3-core.sh;

# Replace the kernel while retaining the installed boot image's ramdisk,
# header, command line and separate device-tree sections.
split_boot;
# magiskboot retains the installed zImage loader and compresses this Image.
# Keep the kernel's appended FDT distinct from the boot header's DTB table.
cp -f "$AKHOME/kernel_dtb" "$SPLITIMG/kernel_dtb" || abort "Cannot stage kernel DTB";
flash_boot;
