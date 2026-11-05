#ifndef __KSU_UAPI_SELINUX_H
#define __KSU_UAPI_SELINUX_H

#include <linux/types.h>

#ifdef __KERNEL__
#define KSU_SEPOLICY_CMD_NORMAL_PERM ((__u32) (1))
#else
static const __u32 KSU_SEPOLICY_CMD_NORMAL_PERM = 1;
#endif
#ifdef __KERNEL__
#define KSU_SEPOLICY_CMD_XPERM ((__u32) (2))
#else
static const __u32 KSU_SEPOLICY_CMD_XPERM = 2;
#endif
#ifdef __KERNEL__
#define KSU_SEPOLICY_CMD_TYPE_STATE ((__u32) (3))
#else
static const __u32 KSU_SEPOLICY_CMD_TYPE_STATE = 3;
#endif
#ifdef __KERNEL__
#define KSU_SEPOLICY_CMD_TYPE ((__u32) (4))
#else
static const __u32 KSU_SEPOLICY_CMD_TYPE = 4;
#endif
#ifdef __KERNEL__
#define KSU_SEPOLICY_CMD_TYPE_ATTR ((__u32) (5))
#else
static const __u32 KSU_SEPOLICY_CMD_TYPE_ATTR = 5;
#endif
#ifdef __KERNEL__
#define KSU_SEPOLICY_CMD_ATTR ((__u32) (6))
#else
static const __u32 KSU_SEPOLICY_CMD_ATTR = 6;
#endif
#ifdef __KERNEL__
#define KSU_SEPOLICY_CMD_TYPE_TRANSITION ((__u32) (7))
#else
static const __u32 KSU_SEPOLICY_CMD_TYPE_TRANSITION = 7;
#endif
#ifdef __KERNEL__
#define KSU_SEPOLICY_CMD_TYPE_CHANGE ((__u32) (8))
#else
static const __u32 KSU_SEPOLICY_CMD_TYPE_CHANGE = 8;
#endif
#ifdef __KERNEL__
#define KSU_SEPOLICY_CMD_GENFSCON ((__u32) (9))
#else
static const __u32 KSU_SEPOLICY_CMD_GENFSCON = 9;
#endif

#ifdef __KERNEL__
#define KSU_SEPOLICY_SUBCMD_NORMAL_PERM_ALLOW ((__u32) (1))
#else
static const __u32 KSU_SEPOLICY_SUBCMD_NORMAL_PERM_ALLOW = 1;
#endif
#ifdef __KERNEL__
#define KSU_SEPOLICY_SUBCMD_NORMAL_PERM_DENY ((__u32) (2))
#else
static const __u32 KSU_SEPOLICY_SUBCMD_NORMAL_PERM_DENY = 2;
#endif
#ifdef __KERNEL__
#define KSU_SEPOLICY_SUBCMD_NORMAL_PERM_AUDITALLOW ((__u32) (3))
#else
static const __u32 KSU_SEPOLICY_SUBCMD_NORMAL_PERM_AUDITALLOW = 3;
#endif
#ifdef __KERNEL__
#define KSU_SEPOLICY_SUBCMD_NORMAL_PERM_DONTAUDIT ((__u32) (4))
#else
static const __u32 KSU_SEPOLICY_SUBCMD_NORMAL_PERM_DONTAUDIT = 4;
#endif

#ifdef __KERNEL__
#define KSU_SEPOLICY_SUBCMD_XPERM_ALLOW ((__u32) (1))
#else
static const __u32 KSU_SEPOLICY_SUBCMD_XPERM_ALLOW = 1;
#endif
#ifdef __KERNEL__
#define KSU_SEPOLICY_SUBCMD_XPERM_AUDITALLOW ((__u32) (2))
#else
static const __u32 KSU_SEPOLICY_SUBCMD_XPERM_AUDITALLOW = 2;
#endif
#ifdef __KERNEL__
#define KSU_SEPOLICY_SUBCMD_XPERM_DONTAUDIT ((__u32) (3))
#else
static const __u32 KSU_SEPOLICY_SUBCMD_XPERM_DONTAUDIT = 3;
#endif

#ifdef __KERNEL__
#define KSU_SEPOLICY_SUBCMD_TYPE_STATE_PERMISSIVE ((__u32) (1))
#else
static const __u32 KSU_SEPOLICY_SUBCMD_TYPE_STATE_PERMISSIVE = 1;
#endif
#ifdef __KERNEL__
#define KSU_SEPOLICY_SUBCMD_TYPE_STATE_ENFORCE ((__u32) (2))
#else
static const __u32 KSU_SEPOLICY_SUBCMD_TYPE_STATE_ENFORCE = 2;
#endif

#ifdef __KERNEL__
#define KSU_SEPOLICY_SUBCMD_TYPE_CHANGE_CHANGE ((__u32) (1))
#else
static const __u32 KSU_SEPOLICY_SUBCMD_TYPE_CHANGE_CHANGE = 1;
#endif
#ifdef __KERNEL__
#define KSU_SEPOLICY_SUBCMD_TYPE_CHANGE_MEMBER ((__u32) (2))
#else
static const __u32 KSU_SEPOLICY_SUBCMD_TYPE_CHANGE_MEMBER = 2;
#endif

#endif
