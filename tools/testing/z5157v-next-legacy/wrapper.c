/* Run the real private-inode constructor and SELinux initializer with failures. */
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#define __read_mostly
#define unlikely(x) (x)
#define ERR_PTR(x) ((void *)(intptr_t)(x))
#define PTR_ERR(x) ((intptr_t)(x))
#define IS_ERR(x) ((uintptr_t)(x) >= (uintptr_t)-4095)
#define ERR_CAST(x) ((void *)(x))
#define S_PRIVATE 1
#define LABEL_INITIALIZED 1
#define SECCLASS_FILE 6
#define FILE__CREATE 4
#define LSM_AUDIT_DATA_INODE 3
#define OPEN_FMODE(x) (((x)+1)&3)
#define O_ACCMODE 3
#define O_NONBLOCK 04000
struct task_security_struct { unsigned sid; };
struct inode_security_struct { int initialized, sclass; unsigned sid; };
struct inode { unsigned i_flags; void *i_mapping; struct inode_security_struct sec; };
struct qstr { const char *name; size_t len; unsigned hash; };
struct common_audit_data { int type; union {struct inode *inode;} u; };
struct vfsmount { void *mnt_sb; };
struct dentry { struct inode *inode; };
struct path { struct vfsmount *mnt; struct dentry *dentry; };
struct file_operations { int *owner; };
struct file { struct path path; int f_flags; void *f_mapping, *private_data; const struct file_operations *ops; };
static int ss_initialized = 1;
static int inodes, dentries, files, mounts, module_refs;
static int fault, avc_calls, transition_calls;
static struct task_security_struct caller = { .sid = 42 };
static const void *current_cred(void) { return &caller; }
static const struct task_security_struct *selinux_cred(const void *p) { return p; }
static struct inode_security_struct *selinux_inode(const struct inode *p) { return (void *)&p->sec; }
static int security_transition_sid(unsigned a, unsigned b, int cls, const struct qstr *name, unsigned *sid) {
    assert(a==42 && b==42 && cls==SECCLASS_FILE && name->len && name->name);
    transition_calls++; if(fault==5)return -EINVAL; *sid=84; return 0;
}
static int avc_has_perm(unsigned source, unsigned target, int cls, unsigned perm, struct common_audit_data *ad) {
    assert(source==42 && target==ad->u.inode->sec.sid && cls==SECCLASS_FILE && perm==FILE__CREATE);
    assert(ad->type==LSM_AUDIT_DATA_INODE && !(ad->u.inode->i_flags&S_PRIVATE));
    assert(ad->u.inode->sec.initialized==LABEL_INITIALIZED);
    avc_calls++; return fault==6 ? -EACCES : 0;
}
static bool try_module_get(int *owner) { assert(owner);if(fault==1)return false; module_refs++;return true; }
static void module_put(int *owner) { if(owner){assert(module_refs>0);module_refs--;} }
static struct inode *alloc_anon_inode(void *sb) {
    assert(sb);if(fault==2)return ERR_PTR(-ENOMEM);
    struct inode *p=calloc(1,sizeof(*p));assert(p);p->i_flags=S_PRIVATE;p->i_mapping=p;inodes++;return p;
}
static void iput(struct inode *p) { assert(inodes>0);inodes--;free(p); }
static struct dentry *d_alloc_pseudo(void *sb,const struct qstr *name) {
    assert(sb&&name);if(fault==3)return NULL;
    struct dentry *p=calloc(1,sizeof(*p));assert(p);dentries++;return p;
}
static struct vfsmount *mntget(struct vfsmount *p) { mounts++;return p; }
static void d_instantiate(struct dentry *d,struct inode *i) { d->inode=i; }
static void path_put(struct path *p) { assert(mounts>0&&dentries>0);mounts--;dentries--;iput(p->dentry->inode);free(p->dentry); }
static struct file *alloc_file(struct path *path,int mode,const struct file_operations *ops) {
    assert(mode==3 && path->dentry->inode->sec.initialized==LABEL_INITIALIZED);
    if(fault==4)return ERR_PTR(-ENOMEM);
    struct file *p=calloc(1,sizeof(*p));assert(p);p->path=*path;p->ops=ops;files++;return p;
}
static void close_file(struct file *p) { assert(files>0);files--;path_put(&p->path);module_put(p->ops->owner);free(p); }
#include "actual-wrapper.inc"
static void clean(void) { assert(!inodes&&!dentries&&!files&&!mounts&&!module_refs); }
int main(void) {
    struct vfsmount mount = { .mnt_sb=&mount };
    int owner=1;struct file_operations ops={.owner=&owner};
    struct file *a,*b;
    a=ksu_anon_inode_create_getfile_compat("test",&ops,NULL,2,NULL);
    assert(PTR_ERR(a)==-ENODEV);clean();anon_inode_mnt=&mount;
    for(fault=1;fault<=6;fault++) {
        avc_calls=transition_calls=0;
        a=ksu_anon_inode_create_getfile_compat("test",&ops,&owner,2,NULL);
        assert(IS_ERR(a));
        assert(PTR_ERR(a)==(fault==1 ? -ENOENT : fault==5 ? -EINVAL : fault==6 ? -EACCES : -ENOMEM));
        if(fault==5)assert(transition_calls==1&&avc_calls==0);
        if(fault==6)assert(transition_calls==1&&avc_calls==1);
        clean();
    }
    fault=0;avc_calls=transition_calls=0;
    a=ksu_anon_inode_create_getfile_compat("test",&ops,&owner,2|O_NONBLOCK,NULL);
    b=ksu_anon_inode_create_getfile_compat("test",&ops,&owner,2,NULL);
    assert(!IS_ERR(a)&&!IS_ERR(b)&&a->path.dentry->inode!=b->path.dentry->inode);
    assert(a->private_data==&owner && a->f_flags==(2|O_NONBLOCK));
    a->path.dentry->inode->sec.sid=99;
    assert(b->path.dentry->inode->sec.sid==84 && avc_calls==2);
    close_file(a);close_file(b);clean();
    struct inode context={.sec={.initialized=0,.sid=123,.sclass=SECCLASS_FILE}};
    a=ksu_anon_inode_create_getfile_compat("test",&ops,NULL,2,&context);
    assert(PTR_ERR(a)==-EACCES);clean();context.sec.initialized=LABEL_INITIALIZED;
    transition_calls=0;
    a=ksu_anon_inode_create_getfile_compat("test",&ops,NULL,2,&context);
    assert(!IS_ERR(a)&&a->path.dentry->inode->sec.sid==123&&transition_calls==0);
    close_file(a);clean();
    puts("PASS: private inodes, SELinux transition/CREATE denials, context validation and all allocation failure paths");
}
