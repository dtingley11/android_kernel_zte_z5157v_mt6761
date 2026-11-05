/* Exercise the real manual exec hook's authorization and failure behavior. */
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include <errno.h>
#define __user
#define unlikely(x) (x)
#define likely(x) (x)
#define ERR_PTR(x) ((void *)(intptr_t)(x))
#define IS_ERR(x) ((uintptr_t)(x)>=(uintptr_t)-4095)
#define IS_ERR_OR_NULL(x) (!(x)||IS_ERR(x))
#define GFP_KERNEL 0
#define O_RDONLY 0
#define SU_PATH "/system/bin/su"
#define SH_PATH "/system/bin/sh"
#define KSUD_PATH "/data/adb/ksud"
#define pr_info(...) ((void)0)
struct filename { char *name; };
struct user_arg_ptr { union {const char *const *native;} ptr; };
struct ksu_sulog_pending_event { int unused; };
struct file { int unused; };
struct uid { int val; };
static bool ksu_su_compat_enabled=true,allowed=true,daemon_present=true;
static int profile_result,grants,captures,emits,opens,closes,last_result;
static struct user_arg_ptr *expected_argv;
static struct ksu_sulog_pending_event pending;
static struct file daemon;
static struct uid current_uid(void) { return (struct uid){.val=10000}; }
static bool ksu_is_allow_uid_for_current(int uid) { assert(uid==10000);return allowed; }
static int escape_with_root_profile(void) { grants++;return profile_result; }
static struct ksu_sulog_pending_event *ksu_sulog_capture_sucompat_manual(const char *filename,const struct user_arg_ptr *argv,int flags) {
    assert(!strcmp(filename,SU_PATH)&&argv==expected_argv&&flags==GFP_KERNEL);captures++;return &pending;
}
static void ksu_sulog_emit_pending(struct ksu_sulog_pending_event *p,int result,int flags) {
    assert(p==&pending&&flags==GFP_KERNEL);emits++;last_result=result;
}
static struct file *ksu_filp_open_compat(const char *path,int flags,int mode) {
    assert(!strcmp(path,KSUD_PATH)&&flags==O_RDONLY&&!mode);opens++;return daemon_present?&daemon:ERR_PTR(-ENOENT);
}
static void filp_close(struct file *f,void *owner) { assert(f==&daemon&&!owner);closes++; }
#include "actual-sucompat.inc"
int main(void) {
    const char *user_strings[]={SU_PATH,"-c","id",NULL};struct user_arg_ptr argv={.ptr.native=user_strings};expected_argv=&argv;
    char path[128];struct filename name={.name=path},*p=&name;int fd=-100,flags=0;
    assert(!ksu_handle_execveat_sucompat(&fd,NULL,&argv,NULL,&flags));
    p=ERR_PTR(-EFAULT);assert(!ksu_handle_execveat_sucompat(&fd,&p,&argv,NULL,&flags));p=NULL;
    assert(!ksu_handle_execveat_sucompat(&fd,&p,&argv,NULL,&flags));p=&name;
    strcpy(path,SU_PATH);allowed=false;assert(!ksu_handle_execveat_sucompat(&fd,&p,&argv,NULL,&flags));
    assert(!strcmp(path,SU_PATH)&&!grants&&!captures);allowed=true;
    ksu_su_compat_enabled=false;assert(!ksu_handle_execveat_sucompat(&fd,&p,&argv,NULL,&flags));assert(!grants);ksu_su_compat_enabled=true;
    strcpy(path,"/system/bin/id");assert(!ksu_handle_execveat_sucompat(&fd,&p,&argv,NULL,&flags));assert(!grants);
    strcpy(path,SU_PATH);profile_result=-ENOMEM;
    assert(ksu_handle_execveat_sucompat(&fd,&p,&argv,NULL,&flags)==-ENOMEM);
    assert(!strcmp(path,SU_PATH)&&!opens&&last_result==-ENOMEM&&emits==1);
    for(int state=0;state<3;state++) {
        strcpy(path,SU_PATH);profile_result=state==2?-EALREADY:0;daemon_present=state!=0;
        assert(!ksu_handle_execveat_sucompat(&fd,&p,&argv,NULL,&flags));
        assert(!strcmp(path,daemon_present?KSUD_PATH:SH_PATH)&&last_result==0);
    }
    assert(grants==4&&captures==4&&emits==4&&opens==3&&closes==2);
    puts("PASS: manual su authorization, failed credentials, first-install shell fallback, existing daemon and nested root");
}
