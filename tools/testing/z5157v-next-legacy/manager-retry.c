#include <assert.h>
#include <dirent.h>
#include <errno.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/types.h>

#define KERNEL_VERSION(a,b,c) (((a)<<16)|((b)<<8)|(c))
#define LINUX_VERSION_CODE KERNEL_VERSION(4,9,190)
#define KSU_MANAGER_PACKAGE "com.rifsxd.ksunext.z5157v.experimental"
#define KSU_MAX_PACKAGE_NAME 256
#define KSU_INVALID_APPID ((uid_t)-1)
#define PER_USER_RANGE 100000
#define GFP_KERNEL 0
#define O_RDONLY 0
#define O_NOFOLLOW 0
#define O_NOATIME 0
#define __init
#define __exit
#define unlikely(x) (x)
#define pr_info(...) ((void)0)
#define pr_err(...) ((void)0)
#define DEFINE_MUTEX(name) int name
#define container_of(p,t,m) ((t *)((char *)(p)-offsetof(t,m)))
#define IS_ERR(p) ((uintptr_t)(p) >= (uintptr_t)-4095)
#define PTR_ERR(p) ((long)(p))
typedef uint32_t u32;
typedef uint64_t u64;

struct list_head { struct list_head *next,*prev; };
#define LIST_HEAD_INIT(h) { &(h), &(h) }
#define INIT_LIST_HEAD(h) (*(h)=(struct list_head)LIST_HEAD_INIT(*(h)))
static void list_add_tail(struct list_head *n,struct list_head *h) {
 n->prev=h->prev;n->next=h;h->prev->next=n;h->prev=n;
}
static void list_del(struct list_head *n) {n->prev->next=n->next;n->next->prev=n->prev;}
#define list_entry(p,t,m) container_of(p,t,m)
#define list_for_each_entry(p,h,m) \
 for(p=list_entry((h)->next,__typeof__(*p),m);&(p)->m!=(h);p=list_entry(p->m.next,__typeof__(*p),m))
#define list_for_each_entry_safe(p,n,h,m) \
 for(p=list_entry((h)->next,__typeof__(*p),m),n=list_entry(p->m.next,__typeof__(*p),m); \
     &(p)->m!=(h);p=n,n=list_entry(n->m.next,__typeof__(*n),m))

struct cred { int unused; };
static struct cred credentials;
static const struct cred *ksu_cred=&credentials;
static int lock_depth,override_depth,checks,prunes;
static bool trusted_apk,package_present=true;
static uid_t package_uid=10136;
static char packages[512];
static void mutex_lock(int *m) {(void)m;assert(!lock_depth++);}
static void mutex_unlock(int *m) {(void)m;assert(lock_depth--==1);}
static const struct cred *override_creds(const struct cred *c) {
 assert(c==ksu_cred&&!override_depth++);return c;
}
static void revert_creds(const struct cred *c) {assert(c==ksu_cred&&override_depth--==1);}
static void *kzalloc(size_t n,int flags) {(void)flags;return calloc(1,n);}
static void kfree(void *p) {free(p);}
static size_t strscpy(char *out,const char *in,size_t n) {
 size_t len=strlen(in);assert(len<n);memcpy(out,in,len+1);return len;
}
static int kstrtou32(const char *text,int base,u32 *out) {
 char *end;*out=strtoul(text,&end,base);return *end ? -EINVAL : 0;
}
static int get_pkg_from_apk_dir_path(char *out,const char *path) {
 const char *name=strrchr(path,'/');assert(name);name++;
 const char *dash=strchr(name,'-');assert(dash);
 size_t n=dash-name;memcpy(out,name,n);out[n]=0;return 0;
}
struct super_block { unsigned long s_magic; };
struct inode { struct super_block *i_sb; };
struct file { struct inode *f_inode;char path[384]; };
static struct super_block sb={0xf2f52010};
static struct inode inode={&sb};
struct dir_context {
 int (*actor)(struct dir_context *,const char *,int,loff_t,u64,unsigned int);
};
static struct file *filp_open(const char *path,int flags,int mode) {
 (void)flags;(void)mode;struct file *f=calloc(1,sizeof(*f));assert(f);
 strscpy(f->path,path,sizeof(f->path));f->f_inode=&inode;return f;
}
static struct file *ksu_filp_open_nonotify(const char *path,int flags) {
 return filp_open(path,flags,0);
}
static void filp_close(struct file *f,void *unused) {(void)unused;free(f);}
static ssize_t ksu_kernel_read_compat(struct file *f,void *out,size_t n,loff_t *pos) {
 assert(!strcmp(f->path,"/data/system/packages.list"));
 size_t len=strlen(packages);if((size_t)*pos>=len)return 0;
 if(n>len-(size_t)*pos)n=len-(size_t)*pos;
 memcpy(out,packages+*pos,n);*pos+=n;return n;
}
static int iterate_dir(struct file *f,struct dir_context *ctx) {
 const char *name=!strcmp(f->path,"/data/app") ? KSU_MANAGER_PACKAGE "-same-path==" : "base.apk";
 return ctx->actor(ctx,name,strlen(name),0,1,!strcmp(f->path,"/data/app") ? DT_DIR : DT_REG);
}
/* Compatibility with the old path-cache branch for the regression control. */
struct path { int unused; };
static inline int kern_path(const char *name,int flags,struct path *p) {
 (void)name;(void)flags;(void)p;return 0;
}
static inline void path_put(struct path *p) {(void)p;}
static bool ksu_is_manager_appid_valid(void);
static uid_t ksu_get_manager_appid(void);
static void ksu_set_manager_appid(uid_t uid);
static void ksu_invalidate_manager_uid(void);
static void ksu_prune_allowlist(bool (*exists)(uid_t,char *,void *),void *data) {
 prunes++;
 assert(exists(package_uid,KSU_MANAGER_PACKAGE,data)==package_present);
}
bool is_manager_apk(char *path) {
 assert(strstr(path,KSU_MANAGER_PACKAGE "-same-path==/base.apk"));
 checks++;return trusted_apk;
}
#include "actual-manager-retry.inc"
static bool ksu_is_manager_appid_valid(void) {return ksu_manager_appid!=KSU_INVALID_APPID;}
static uid_t ksu_get_manager_appid(void) {return ksu_manager_appid;}
static void ksu_set_manager_appid(uid_t uid) {ksu_manager_appid=uid;}
static void ksu_invalidate_manager_uid(void) {ksu_manager_appid=KSU_INVALID_APPID;}
static void scan(bool prune_only) {
 snprintf(packages,sizeof(packages),"%s %u 0 data default\n",
          package_present ? KSU_MANAGER_PACKAGE : "com.example.other",package_uid);
 track_throne(prune_only);assert(!lock_depth&&!override_depth);
}
int main(void) {
 /* Transient open/read failure, followed by a trusted APK at the same path. */
 scan(false);assert(checks==1&&!ksu_is_manager_appid_valid());
 trusted_apk=true;scan(false);assert(checks==2&&ksu_get_manager_appid()==10136);
 scan(false);assert(checks==2); /* Verified unchanged UID keeps its fast path. */
 package_present=false;scan(false);assert(!ksu_is_manager_appid_valid());
 package_present=true;trusted_apk=false;
 for(int i=0;i<3;i++){scan(false);assert(!ksu_is_manager_appid_valid());}
 assert(checks==5); /* Rejected signatures never authorize a manager. */
 trusted_apk=true;scan(true);assert(checks==5&&!ksu_is_manager_appid_valid());
 scan(false);assert(checks==6&&ksu_get_manager_appid()==10136);
 package_uid=10137;trusted_apk=false;scan(false);
 assert(checks==7&&!ksu_is_manager_appid_valid()); /* UID change must reverify. */
 trusted_apk=true;scan(false);assert(checks==8&&ksu_get_manager_appid()==10137);
 assert(prunes==11);
 puts("PASS: actual manager tracker retries failed verification, retains verified-UID fast path and rejects untrusted APKs/UID changes");
}
