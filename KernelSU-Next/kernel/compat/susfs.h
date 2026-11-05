/* SPDX-License-Identifier: GPL-2.0 */
#ifndef __KSU_COMPAT_SUSFS_H
#define __KSU_COMPAT_SUSFS_H
#include <linux/types.h>
#ifdef CONFIG_KSU_SUSFS
int ksu_susfs_task_prctl(int option, unsigned long arg2, unsigned long arg3,
                       unsigned long arg4, unsigned long arg5);
void ksu_susfs_post_fs_data(void);
bool susfs_should_umount_system(uid_t uid);
#endif
#endif
