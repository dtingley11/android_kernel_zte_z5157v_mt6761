// SPDX-License-Identifier: GPL-2.0-only
/*
 * SELinux anonymous-inode initialization adapted from Linux v5.15
 * security/selinux/hooks.c:selinux_inode_init_security_anon().
 *
 * This Android 10 policy lacks the anon_inode class and denies unknown
 * classes. Use its existing file class for KSU's private file wrappers.
 * Keep SID transitions, context validation, and the FILE__CREATE check.
 */
#include <linux/version.h>
#if LINUX_VERSION_CODE < KERNEL_VERSION(4, 19, 0)
#include <linux/cred.h>
#include <linux/fs.h>
#include <linux/lsm_audit.h>
#include "selinux.h"
#include "security.h"
#include "avc.h"

extern int ss_initialized;

int ksu_inode_init_security_anon_compat(struct inode *inode,
                                      const struct qstr *name,
                                      const struct inode *context_inode)
{
    const struct task_security_struct *tsec = selinux_cred(current_cred());
    struct common_audit_data ad;
    struct inode_security_struct *isec = selinux_inode(inode);
    int rc;

    if (unlikely(!ss_initialized))
        return 0;
    if (context_inode) {
        const struct inode_security_struct *context_isec = selinux_inode(context_inode);
        if (context_isec->initialized != LABEL_INITIALIZED)
            return -EACCES;
        isec->sclass = context_isec->sclass;
        isec->sid = context_isec->sid;
    } else {
        isec->sclass = SECCLASS_FILE;
        rc = security_transition_sid(tsec->sid, tsec->sid, isec->sclass,
                                     name, &isec->sid);
        if (rc)
            return rc;
    }
    isec->initialized = LABEL_INITIALIZED;
    ad.type = LSM_AUDIT_DATA_INODE;
    ad.u.inode = inode;
    return avc_has_perm(tsec->sid, isec->sid, isec->sclass, FILE__CREATE, &ad);
}
#endif
