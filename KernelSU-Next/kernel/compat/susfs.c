// SPDX-License-Identifier: GPL-2.0
/* Legacy SUSFS v1.5.5 control ABI; keeps Next's fd/ioctl interface separate. */
#include <linux/cred.h>
#include <linux/fs.h>
#include <linux/namei.h>
#include <linux/susfs.h>
#include <linux/uaccess.h>
#include "compat/kernel_compat.h"
#include "compat/susfs.h"
#include "manager/manager_identity.h"
#include "policy/allowlist.h"
#include "selinux/selinux.h"
#include "klog.h"

bool susfs_is_allow_su(void)
{
    return is_manager() || ksu_is_allow_uid_for_current(current_uid().val);
}

static bool umount_zygote_system;
extern bool susfs_is_auto_add_sus_ksu_default_mount_enabled;
extern void susfs_run_try_umount_for_current_mnt_ns(void);

bool susfs_should_umount_system(uid_t uid)
{
    return umount_zygote_system && uid >= 1000 && uid < 10000;
}

void ksu_susfs_post_fs_data(void)
{
    struct path path;
    if (!kern_path(DATA_ADB_UMOUNT_FOR_ZYGOTE_SYSTEM_PROCESS, 0, &path)) {
        umount_zygote_system = true;
        path_put(&path);
    }
#ifdef CONFIG_KSU_SUSFS_AUTO_ADD_SUS_KSU_DEFAULT_MOUNT
    if (!kern_path(DATA_ADB_NO_AUTO_ADD_SUS_KSU_DEFAULT_MOUNT, 0, &path)) {
        susfs_is_auto_add_sus_ksu_default_mount_enabled = false;
        path_put(&path);
    }
#endif
}

int ksu_susfs_task_prctl(int option, unsigned long arg2, unsigned long arg3,
                        unsigned long arg4, unsigned long arg5)
{
    uid_t current_uid_val = current_uid().val;
    if ((u32)option != 0xDEADBEEF || current_uid_val != 0)
        return -ENOSYS;
	if (current_uid_val == 0) {
#ifdef CONFIG_KSU_SUSFS_SUS_PATH
		if (arg2 == CMD_SUSFS_ADD_SUS_PATH) {
			int error = 0;
			if (!ksu_access_ok((void __user*)arg3, sizeof(struct st_susfs_sus_path))) {
				pr_err("susfs: CMD_SUSFS_ADD_SUS_PATH -> arg3 is not accessible\n");
				return 0;
			}
			if (!ksu_access_ok((void __user*)arg5, sizeof(error))) {
				pr_err("susfs: CMD_SUSFS_ADD_SUS_PATH -> arg5 is not accessible\n");
				return 0;
			}
			error = susfs_add_sus_path((struct st_susfs_sus_path __user*)arg3);
			pr_info("susfs: CMD_SUSFS_ADD_SUS_PATH -> ret: %d\n", error);
			if (copy_to_user((void __user*)arg5, &error, sizeof(error)))
				pr_info("susfs: copy_to_user() failed\n");
			return 0;
		}
#endif //#ifdef CONFIG_KSU_SUSFS_SUS_PATH
#ifdef CONFIG_KSU_SUSFS_SUS_MOUNT
		if (arg2 == CMD_SUSFS_ADD_SUS_MOUNT) {
			int error = 0;
			if (!ksu_access_ok((void __user*)arg3, sizeof(struct st_susfs_sus_mount))) {
				pr_err("susfs: CMD_SUSFS_ADD_SUS_MOUNT -> arg3 is not accessible\n");
				return 0;
			}
			if (!ksu_access_ok((void __user*)arg5, sizeof(error))) {
				pr_err("susfs: CMD_SUSFS_ADD_SUS_MOUNT -> arg5 is not accessible\n");
				return 0;
			}
			error = susfs_add_sus_mount((struct st_susfs_sus_mount __user*)arg3);
			pr_info("susfs: CMD_SUSFS_ADD_SUS_MOUNT -> ret: %d\n", error);
			if (copy_to_user((void __user*)arg5, &error, sizeof(error)))
				pr_info("susfs: copy_to_user() failed\n");
			return 0;
		}
#endif //#ifdef CONFIG_KSU_SUSFS_SUS_MOUNT
#ifdef CONFIG_KSU_SUSFS_SUS_KSTAT
		if (arg2 == CMD_SUSFS_ADD_SUS_KSTAT) {
			int error = 0;
			if (!ksu_access_ok((void __user*)arg3, sizeof(struct st_susfs_sus_kstat))) {
				pr_err("susfs: CMD_SUSFS_ADD_SUS_KSTAT -> arg3 is not accessible\n");
				return 0;
			}
			if (!ksu_access_ok((void __user*)arg5, sizeof(error))) {
				pr_err("susfs: CMD_SUSFS_ADD_SUS_KSTAT -> arg5 is not accessible\n");
				return 0;
			}
			error = susfs_add_sus_kstat((struct st_susfs_sus_kstat __user*)arg3);
			pr_info("susfs: CMD_SUSFS_ADD_SUS_KSTAT -> ret: %d\n", error);
			if (copy_to_user((void __user*)arg5, &error, sizeof(error)))
				pr_info("susfs: copy_to_user() failed\n");
			return 0;
		}
		if (arg2 == CMD_SUSFS_UPDATE_SUS_KSTAT) {
			int error = 0;
			if (!ksu_access_ok((void __user*)arg3, sizeof(struct st_susfs_sus_kstat))) {
				pr_err("susfs: CMD_SUSFS_UPDATE_SUS_KSTAT -> arg3 is not accessible\n");
				return 0;
			}
			if (!ksu_access_ok((void __user*)arg5, sizeof(error))) {
				pr_err("susfs: CMD_SUSFS_UPDATE_SUS_KSTAT -> arg5 is not accessible\n");
				return 0;
			}
			error = susfs_update_sus_kstat((struct st_susfs_sus_kstat __user*)arg3);
			pr_info("susfs: CMD_SUSFS_UPDATE_SUS_KSTAT -> ret: %d\n", error);
			if (copy_to_user((void __user*)arg5, &error, sizeof(error)))
				pr_info("susfs: copy_to_user() failed\n");
			return 0;
		}
		if (arg2 == CMD_SUSFS_ADD_SUS_KSTAT_STATICALLY) {
			int error = 0;
			if (!ksu_access_ok((void __user*)arg3, sizeof(struct st_susfs_sus_kstat))) {
				pr_err("susfs: CMD_SUSFS_ADD_SUS_KSTAT_STATICALLY -> arg3 is not accessible\n");
				return 0;
			}
			if (!ksu_access_ok((void __user*)arg5, sizeof(error))) {
				pr_err("susfs: CMD_SUSFS_ADD_SUS_KSTAT_STATICALLY -> arg5 is not accessible\n");
				return 0;
			}
			error = susfs_add_sus_kstat((struct st_susfs_sus_kstat __user*)arg3);
			pr_info("susfs: CMD_SUSFS_ADD_SUS_KSTAT_STATICALLY -> ret: %d\n", error);
			if (copy_to_user((void __user*)arg5, &error, sizeof(error)))
				pr_info("susfs: copy_to_user() failed\n");
			return 0;
        }
#endif //#ifdef CONFIG_KSU_SUSFS_SUS_KSTAT
#ifdef CONFIG_KSU_SUSFS_TRY_UMOUNT
		if (arg2 == CMD_SUSFS_ADD_TRY_UMOUNT) {
			int error = 0;
			if (!ksu_access_ok((void __user*)arg3, sizeof(struct st_susfs_try_umount))) {
				pr_err("susfs: CMD_SUSFS_ADD_TRY_UMOUNT -> arg3 is not accessible\n");
				return 0;
			}
			if (!ksu_access_ok((void __user*)arg5, sizeof(error))) {
				pr_err("susfs: CMD_SUSFS_ADD_TRY_UMOUNT -> arg5 is not accessible\n");
				return 0;
			}
			error = susfs_add_try_umount((struct st_susfs_try_umount __user*)arg3);
			pr_info("susfs: CMD_SUSFS_ADD_TRY_UMOUNT -> ret: %d\n", error);
			if (copy_to_user((void __user*)arg5, &error, sizeof(error)))
				pr_info("susfs: copy_to_user() failed\n");
			return 0;
		}
		if (arg2 == CMD_SUSFS_RUN_UMOUNT_FOR_CURRENT_MNT_NS) {
			int error = 0;
			susfs_run_try_umount_for_current_mnt_ns();
			if (copy_to_user((void __user *)arg5, &error, sizeof(error)))
                return -EFAULT;
            return 0;
		}
#endif //#ifdef CONFIG_KSU_SUSFS_TRY_UMOUNT
#ifdef CONFIG_KSU_SUSFS_SPOOF_UNAME
		if (arg2 == CMD_SUSFS_SET_UNAME) {
			int error = 0;
			if (!ksu_access_ok((void __user*)arg3, sizeof(struct st_susfs_uname))) {
				pr_err("susfs: CMD_SUSFS_SET_UNAME -> arg3 is not accessible\n");
				return 0;
			}
			if (!ksu_access_ok((void __user*)arg5, sizeof(error))) {
				pr_err("susfs: CMD_SUSFS_SET_UNAME -> arg5 is not accessible\n");
				return 0;
			}
			error = susfs_set_uname((struct st_susfs_uname __user*)arg3);
			pr_info("susfs: CMD_SUSFS_SET_UNAME -> ret: %d\n", error);
			if (copy_to_user((void __user*)arg5, &error, sizeof(error)))
				pr_info("susfs: copy_to_user() failed\n");
			return 0;
		}
#endif //#ifdef CONFIG_KSU_SUSFS_SPOOF_UNAME
#ifdef CONFIG_KSU_SUSFS_ENABLE_LOG
		if (arg2 == CMD_SUSFS_ENABLE_LOG) {
			int error = 0;
			if (arg3 != 0 && arg3 != 1) {
				pr_err("susfs: CMD_SUSFS_ENABLE_LOG -> arg3 can only be 0 or 1\n");
				return 0;
			}
			susfs_set_log(arg3);
			if (copy_to_user((void __user*)arg5, &error, sizeof(error)))
				pr_info("susfs: copy_to_user() failed\n");
			return 0;
		}
#endif //#ifdef CONFIG_KSU_SUSFS_ENABLE_LOG
#ifdef CONFIG_KSU_SUSFS_SPOOF_CMDLINE_OR_BOOTCONFIG
		if (arg2 == CMD_SUSFS_SET_CMDLINE_OR_BOOTCONFIG) {
			int error = 0;
			if (!ksu_access_ok((void __user*)arg3, SUSFS_FAKE_CMDLINE_OR_BOOTCONFIG_SIZE)) {
				pr_err("susfs: CMD_SUSFS_SET_CMDLINE_OR_BOOTCONFIG -> arg3 is not accessible\n");
				return 0;
			}
			if (!ksu_access_ok((void __user*)arg5, sizeof(error))) {
				pr_err("susfs: CMD_SUSFS_SET_CMDLINE_OR_BOOTCONFIG -> arg5 is not accessible\n");
				return 0;
			}
			error = susfs_set_cmdline_or_bootconfig((char __user*)arg3);
			pr_info("susfs: CMD_SUSFS_SET_CMDLINE_OR_BOOTCONFIG -> ret: %d\n", error);
			if (copy_to_user((void __user*)arg5, &error, sizeof(error)))
				pr_info("susfs: copy_to_user() failed\n");
			return 0;
		}
#endif //#ifdef CONFIG_KSU_SUSFS_SPOOF_CMDLINE_OR_BOOTCONFIG
#ifdef CONFIG_KSU_SUSFS_OPEN_REDIRECT
		if (arg2 == CMD_SUSFS_ADD_OPEN_REDIRECT) {
			int error = 0;
			if (!ksu_access_ok((void __user*)arg3, sizeof(struct st_susfs_open_redirect))) {
				pr_err("susfs: CMD_SUSFS_ADD_OPEN_REDIRECT -> arg3 is not accessible\n");
				return 0;
			}
			if (!ksu_access_ok((void __user*)arg5, sizeof(error))) {
				pr_err("susfs: CMD_SUSFS_ADD_OPEN_REDIRECT -> arg5 is not accessible\n");
				return 0;
			}
			error = susfs_add_open_redirect((struct st_susfs_open_redirect __user*)arg3);
			pr_info("susfs: CMD_SUSFS_ADD_OPEN_REDIRECT -> ret: %d\n", error);
			if (copy_to_user((void __user*)arg5, &error, sizeof(error)))
				pr_info("susfs: copy_to_user() failed\n");
			return 0;
		}
#endif //#ifdef CONFIG_KSU_SUSFS_OPEN_REDIRECT
		if (arg2 == CMD_SUSFS_SHOW_VERSION) {
			int error = 0;
			int len_of_susfs_version = strlen(SUSFS_VERSION);
			char *susfs_version = SUSFS_VERSION;
			if (!ksu_access_ok((void __user*)arg3, len_of_susfs_version+1)) {
				pr_err("susfs: CMD_SUSFS_SHOW_VERSION -> arg3 is not accessible\n");
				return 0;
			}
			if (!ksu_access_ok((void __user*)arg5, sizeof(error))) {
				pr_err("susfs: CMD_SUSFS_SHOW_VERSION -> arg5 is not accessible\n");
				return 0;
			}
			error = copy_to_user((void __user*)arg3, (void*)susfs_version, len_of_susfs_version+1);
			pr_info("susfs: CMD_SUSFS_SHOW_VERSION -> ret: %d\n", error);
			if (copy_to_user((void __user*)arg5, &error, sizeof(error)))
				pr_info("susfs: copy_to_user() failed\n");
			return 0;
		}
		if (arg2 == CMD_SUSFS_SHOW_ENABLED_FEATURES) {
			int error = 0;
			u64 enabled_features = 0;
			if (!ksu_access_ok((void __user*)arg3, sizeof(u64))) {
				pr_err("susfs: CMD_SUSFS_SHOW_ENABLED_FEATURES -> arg3 is not accessible\n");
				return 0;
			}
			if (!ksu_access_ok((void __user*)arg5, sizeof(error))) {
				pr_err("susfs: CMD_SUSFS_SHOW_ENABLED_FEATURES -> arg5 is not accessible\n");
				return 0;
			}
#ifdef CONFIG_KSU_SUSFS_SUS_PATH
			enabled_features |= (1 << 0);
#endif
#ifdef CONFIG_KSU_SUSFS_SUS_MOUNT
			enabled_features |= (1 << 1);
#endif
#ifdef CONFIG_KSU_SUSFS_AUTO_ADD_SUS_KSU_DEFAULT_MOUNT
			enabled_features |= (1 << 2);
#endif
#ifdef CONFIG_KSU_SUSFS_AUTO_ADD_SUS_BIND_MOUNT
			enabled_features |= (1 << 3);
#endif
#ifdef CONFIG_KSU_SUSFS_SUS_KSTAT
			enabled_features |= (1 << 4);
#endif
#ifdef CONFIG_KSU_SUSFS_SUS_OVERLAYFS
			enabled_features |= (1 << 5);
#endif
#ifdef CONFIG_KSU_SUSFS_TRY_UMOUNT
			enabled_features |= (1 << 6);
#endif
#ifdef CONFIG_KSU_SUSFS_AUTO_ADD_TRY_UMOUNT_FOR_BIND_MOUNT
			enabled_features |= (1 << 7);
#endif
#ifdef CONFIG_KSU_SUSFS_SPOOF_UNAME
			enabled_features |= (1 << 8);
#endif
#ifdef CONFIG_KSU_SUSFS_ENABLE_LOG
			enabled_features |= (1 << 9);
#endif
#ifdef CONFIG_KSU_SUSFS_HIDE_KSU_SUSFS_SYMBOLS
			enabled_features |= (1 << 10);
#endif
#ifdef CONFIG_KSU_SUSFS_SPOOF_CMDLINE_OR_BOOTCONFIG
			enabled_features |= (1 << 11);
#endif
#ifdef CONFIG_KSU_SUSFS_OPEN_REDIRECT
			enabled_features |= (1 << 12);
#endif
#ifdef CONFIG_KSU_SUSFS_HAS_MAGIC_MOUNT
			enabled_features |= (1 << 14);
#endif
			error = copy_to_user((void __user*)arg3, (void*)&enabled_features, sizeof(enabled_features));
			pr_info("susfs: CMD_SUSFS_SHOW_ENABLED_FEATURES -> ret: %d\n", error);
			if (copy_to_user((void __user*)arg5, &error, sizeof(error)))
				pr_info("susfs: copy_to_user() failed\n");
			return 0;
		}
		if (arg2 == CMD_SUSFS_SHOW_VARIANT) {
			int error = 0;
			int len_of_variant = strlen(SUSFS_VARIANT);
			char *susfs_variant = SUSFS_VARIANT;
			if (!ksu_access_ok((void __user*)arg3, len_of_variant+1)) {
				pr_err("susfs: CMD_SUSFS_SHOW_VARIANT -> arg3 is not accessible\n");
				return 0;
			}
			if (!ksu_access_ok((void __user*)arg5, sizeof(error))) {
				pr_err("susfs: CMD_SUSFS_SHOW_VARIANT -> arg5 is not accessible\n");
				return 0;
			}
			error = copy_to_user((void __user*)arg3, (void*)susfs_variant, len_of_variant+1);
			pr_info("susfs: CMD_SUSFS_SHOW_VARIANT -> ret: %d\n", error);
			if (copy_to_user((void __user*)arg5, &error, sizeof(error)))
				pr_info("susfs: copy_to_user() failed\n");
			return 0;
		}
	}

    return -ENOSYS;
}
