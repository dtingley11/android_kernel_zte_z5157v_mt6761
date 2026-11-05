//! SUSFS v1.5.5's root-only prctl interface for the Z5157V legacy kernel.
use anyhow::{Result, ensure};
use libc::{c_int, c_ulong, c_void};

const KERNEL_SU_OPTION: c_int = 0xDEADBEEFu32 as c_int;
const SHOW_VERSION: c_ulong = 0x555e1;
const SHOW_FEATURES: c_ulong = 0x555e2;
const SHOW_VARIANT: c_ulong = 0x555e3;

fn query(command: c_ulong, output: *mut c_void) -> Result<()> {
    let mut error: c_int = 126;
    // Variadic arguments must be native words on ARM32, not u64 registers.
    unsafe { libc::prctl(KERNEL_SU_OPTION, command, output, 0 as c_ulong, &mut error); }
    ensure!(error == 0, "Legacy SUSFS command 0x{command:x} failed: {error}");
    Ok(())
}

fn query_string(command: c_ulong) -> Result<String> {
    let mut bytes = [0u8; 16];
    query(command, bytes.as_mut_ptr().cast())?;
    let length = bytes.iter().position(|b| *b == 0).unwrap_or(bytes.len());
    ensure!(length != 0, "Empty SUSFS response");
    Ok(String::from_utf8_lossy(&bytes[..length]).into_owned())
}

pub(super) fn version() -> Result<String> { query_string(SHOW_VERSION) }
pub(super) fn variant() -> Result<String> { query_string(SHOW_VARIANT) }

pub(super) fn features(check_only: bool) -> Result<()> {
    let mut bits: u64 = 0;
    query(SHOW_FEATURES, (&mut bits as *mut u64).cast())?;
    ensure!(bits != 0, "Unsupported");
    if check_only {
        println!("Supported");
        return Ok(());
    }
    // Names and bit positions from the upstream v1.5.5 userspace helper.
    let names = [
        "CONFIG_KSU_SUSFS_SUS_PATH",
        "CONFIG_KSU_SUSFS_SUS_MOUNT",
        "CONFIG_KSU_SUSFS_AUTO_ADD_SUS_KSU_DEFAULT_MOUNT",
        "CONFIG_KSU_SUSFS_AUTO_ADD_SUS_BIND_MOUNT",
        "CONFIG_KSU_SUSFS_SUS_KSTAT",
        "CONFIG_KSU_SUSFS_SUS_OVERLAYFS",
        "CONFIG_KSU_SUSFS_TRY_UMOUNT",
        "CONFIG_KSU_SUSFS_AUTO_ADD_TRY_UMOUNT_FOR_BIND_MOUNT",
        "CONFIG_KSU_SUSFS_SPOOF_UNAME",
        "CONFIG_KSU_SUSFS_ENABLE_LOG",
        "CONFIG_KSU_SUSFS_HIDE_KSU_SUSFS_SYMBOLS",
        "CONFIG_KSU_SUSFS_SPOOF_CMDLINE_OR_BOOTCONFIG",
        "CONFIG_KSU_SUSFS_OPEN_REDIRECT",
        "CONFIG_KSU_SUSFS_SUS_SU",
        "CONFIG_KSU_SUSFS_HAS_MAGIC_MOUNT",
    ];
    for (bit, name) in names.iter().enumerate() {
        if bits & (1 << bit) != 0 { println!("{name}"); }
    }
    Ok(())
}
