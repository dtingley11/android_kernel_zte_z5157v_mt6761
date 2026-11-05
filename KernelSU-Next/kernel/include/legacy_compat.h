/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef __KSU_LEGACY_COMPAT_H
#define __KSU_LEGACY_COMPAT_H

#include <linux/version.h>
#include <linux/compiler.h>
#include <linux/fs.h>
#include <linux/poll.h>
#include <linux/task_work.h>

#ifndef __nocfi
#define __nocfi
#endif

#if LINUX_VERSION_CODE < KERNEL_VERSION(4, 10, 0)
/* This vendor tree's task_work_add() takes a bool notify argument. */
#define TWA_RESUME true
#endif

#if LINUX_VERSION_CODE < KERNEL_VERSION(4, 16, 0)
typedef unsigned int __poll_t;
#define EPOLLIN POLLIN
#define EPOLLOUT POLLOUT
#define EPOLLERR POLLERR
#define EPOLLHUP POLLHUP
#define EPOLLRDNORM POLLRDNORM
#define EPOLLWRNORM POLLWRNORM
#endif

#if LINUX_VERSION_CODE < KERNEL_VERSION(4, 14, 0)
/* Same offset translation as the existing v1.0.8 vendor port. */
static inline ssize_t ksu_legacy_kernel_read(struct file *file, void *buf,
                                            size_t size, loff_t *pos)
{
    loff_t offset = pos ? *pos : 0;
    ssize_t ret = kernel_read(file, offset, buf, size);
    if (pos && ret > 0)
        *pos = offset + ret;
    return ret;
}

static inline ssize_t ksu_legacy_kernel_write(struct file *file, const void *buf,
                                             size_t size, loff_t *pos)
{
    loff_t offset = pos ? *pos : 0;
    ssize_t ret = kernel_write(file, buf, size, offset);
    if (pos && ret > 0)
        *pos = offset + ret;
    return ret;
}
#define kernel_read ksu_legacy_kernel_read
#define kernel_write ksu_legacy_kernel_write
#endif

#endif
