#include <assert.h>
#include <errno.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <sys/types.h>
#define __user
#define pr_info(...) ((void)0)
#define pr_err(...) ((void)0)
#define CONFIG_KSU_SUSFS_SUS_MOUNT 1
#define CONFIG_KSU_SUSFS_AUTO_ADD_SUS_KSU_DEFAULT_MOUNT 1
#define CONFIG_KSU_SUSFS_SUS_KSTAT 1
#define CONFIG_KSU_SUSFS_TRY_UMOUNT 1
#define CONFIG_KSU_SUSFS_SPOOF_UNAME 1
#define CONFIG_KSU_SUSFS_ENABLE_LOG 1
#define CONFIG_KSU_SUSFS_SPOOF_CMDLINE_OR_BOOTCONFIG 1
#define SUSFS_VERSION "v1.5.5"
#define SUSFS_VARIANT "NON-GKI"
typedef uint32_t u32;
typedef uint64_t u64;
static uid_t uid;
struct uid {uid_t val;};
static struct uid current_uid(void) {return (struct uid){uid};}
static bool ksu_access_ok(const void *p,size_t size) {return size && (uintptr_t)p>1;}
static size_t copy_to_user(void *to,const void *from,size_t size) {
 if(!ksu_access_ok(to,size))return size;memcpy(to,from,size);return 0;
}
/* Setter payloads are opaque here; only delegation and access checks are tested. */
struct st_susfs_sus_mount {int unused;};
struct st_susfs_sus_kstat {int unused;};
struct st_susfs_try_umount {int unused;};
struct st_susfs_uname {int unused;};
static int susfs_add_sus_mount(struct st_susfs_sus_mount *p) {assert(p);return 7;}
static int susfs_add_sus_kstat(struct st_susfs_sus_kstat *p) {assert(p);return 0;}
static int susfs_update_sus_kstat(struct st_susfs_sus_kstat *p) {assert(p);return 0;}
static int susfs_add_try_umount(struct st_susfs_try_umount *p) {assert(p);return 0;}
static int susfs_set_uname(struct st_susfs_uname *p) {assert(p);return 0;}
static void susfs_set_log(unsigned long enabled) {assert(enabled<=1);}
static int susfs_set_cmdline_or_bootconfig(char *p) {assert(p);return 0;}
static void susfs_run_try_umount_for_current_mnt_ns(void) {}
#include "actual-susfs-control.inc"
int main(void) {
 char version[16]={0},variant[16]={0};int error=126;u64 bits=0;
 int option=(int)0xDEADBEEF;
 uid=2000;
 assert(ksu_susfs_task_prctl(option,CMD_SUSFS_SHOW_VERSION,(unsigned long)version,0,(unsigned long)&error)==-ENOSYS);
 assert(error==126&&!version[0]);uid=0;
 assert(ksu_susfs_task_prctl(123,CMD_SUSFS_SHOW_VERSION,(unsigned long)version,0,(unsigned long)&error)==-ENOSYS);
 assert(!ksu_susfs_task_prctl(option,CMD_SUSFS_SHOW_VERSION,(unsigned long)version,0,(unsigned long)&error));
 assert(!error&&!strcmp(version,SUSFS_VERSION));
 assert(!ksu_susfs_task_prctl(option,CMD_SUSFS_SHOW_VARIANT,(unsigned long)variant,0,(unsigned long)&error));
 assert(!error&&!strcmp(variant,SUSFS_VARIANT));
 assert(!ksu_susfs_task_prctl(option,CMD_SUSFS_SHOW_ENABLED_FEATURES,(unsigned long)&bits,0,(unsigned long)&error));
 assert(!error&&bits==((1ULL<<1)|(1ULL<<2)|(1ULL<<4)|(1ULL<<6)|(1ULL<<8)|(1ULL<<9)|(1ULL<<11)));
 error=126;assert(!ksu_susfs_task_prctl(option,CMD_SUSFS_SHOW_VERSION,0,0,(unsigned long)&error));assert(error==126);
 assert(ksu_susfs_task_prctl(option,CMD_SUSFS_ADD_SUS_PATH,0,0,(unsigned long)&error)==-ENOSYS);
 assert(ksu_susfs_task_prctl(option,1,0,0,(unsigned long)&error)==-ENOSYS);
 struct st_susfs_sus_mount request={0};
 assert(!ksu_susfs_task_prctl(option,CMD_SUSFS_ADD_SUS_MOUNT,(unsigned long)&request,0,(unsigned long)&error)&&error==7);
 puts("PASS: SUSFS root-only access, unsupported commands, seven feature bits, version/variant replies, invalid buffers and setter status");
}
