#include <assert.h>
#include <errno.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/types.h>
#define __user
#define KERNEL_SU_DOMAIN "ksu"
#define KSUD_PATH "/data/adb/ksud"
#define min(a,b) ((a)<(b)?(a):(b))
struct file { const char *data; size_t size; int error; };
struct kiocb { struct file *file; loff_t pos; };
struct iov_iter { char *buf; size_t count; };
static size_t copy_limit = (size_t)-1;
static size_t copy_to_user(void *to, const void *from, size_t count) {
    size_t copied=min(count,copy_limit);memcpy(to,from,copied);return count-copied;
}
static size_t copy_to_iter(const void *from,size_t count,struct iov_iter *to) {
    size_t copied=min(min(count,to->count),copy_limit);memcpy(to->buf,from,copied);
    to->buf+=copied;to->count-=copied;return copied;
}
static size_t iov_iter_count(struct iov_iter *to) { return to->count; }
static ssize_t mock_read(struct file *file,char *buf,size_t count,loff_t *pos) {
    if(file->error)return file->error;
    size_t copied=min(count,file->size-(size_t)*pos);
    memcpy(buf,file->data+*pos,copied);*pos+=copied;return copied;
}
static ssize_t mock_iter(struct kiocb *io,struct iov_iter *to) {
    size_t count=to->count;
    ssize_t n=mock_read(io->file,to->buf,count,&io->pos);
    if(n>0){to->buf+=n;to->count-=n;}
    return n;
}
static ssize_t (*orig_read)(struct file *,char *,size_t,loff_t *)=mock_read;
static ssize_t (*orig_read_iter)(struct kiocb *,struct iov_iter *)=mock_iter;
static size_t ksu_rc_pos, module_rc_pos, module_rc_len;
static char *module_rc_buf;
static int freed;
static void free_module_rc(void) {
    free(module_rc_buf); module_rc_buf=NULL; module_rc_len=0; freed++;
}
static void reset_module(bool enabled) {
    assert(!module_rc_buf); freed=0; module_rc_pos=0;
    module_rc_len=enabled ? strlen("\non boot\n    setprop test.module 1\n") : 0;
    module_rc_buf=enabled ? strdup("\non boot\n    setprop test.module 1\n") : NULL;
}
/* Real RC text is included before the proxies so sizeof is evaluated here. */
#include "actual-proxies.inc"
static ssize_t read_one(bool iter,struct file *file,loff_t *pos,char *buf,size_t count) {
    if(!iter)return read_proxy(file,buf,count,pos);
    struct kiocb io={file,*pos};struct iov_iter to={buf,count};
    ssize_t n=read_iter_proxy(&io,&to);*pos=io.pos;return n;
}
int main(int argc, char **argv) {
    if(argc==2 && !strcmp(argv[1],"--dump-rc")) {
        fputs(KERNEL_SU_RC,stdout);
        return 0;
    }
    char body[34300];for(size_t i=0;i<sizeof(body);i++)body[i]='a'+i%26;
    const size_t sizes[]={1,2,7,64,1024,4096,32768};
    for(int iter=0;iter<2;iter++) {
        for(int custom=0;custom<2;custom++) for(size_t i=0;i<sizeof(sizes)/sizeof(sizes[0]);i++) {
            reset_module(custom);size_t custom_len=module_rc_len;
            char *custom_rc=module_rc_buf ? strdup(module_rc_buf) : NULL;
            struct file file={body,sizeof(body),0};loff_t pos=0;ksu_rc_pos=0;copy_limit=(size_t)-1;
            char *all=malloc(sizeof(body)+ksu_rc_len+custom_len+sizes[i]);size_t used=0;ssize_t n;
            assert(read_one(iter,&file,&pos,all,0)==0 && pos==0 && ksu_rc_pos==0);
            while((n=read_one(iter,&file,&pos,all+used,sizes[i]))>0)used+=n;
            assert(n==0 && used==sizeof(body)+ksu_rc_len+custom_len && pos==sizeof(body));
            assert(!memcmp(all,body,sizeof(body)));
            assert(!memcmp(all+sizeof(body),KERNEL_SU_RC,ksu_rc_len));
            assert(read_one(iter,&file,&pos,all,1)==0);
            if(custom){assert(!memcmp(all+sizeof(body)+ksu_rc_len,custom_rc,custom_len));assert(freed==1);}
            else assert(freed==0);
            free(custom_rc);free(all);
        }
        reset_module(false);
        char buf[4096];struct file file={body,sizeof(body),-EIO};loff_t pos=0;ksu_rc_pos=0;
        assert(read_one(iter,&file,&pos,buf,sizeof(buf))==-EIO && ksu_rc_pos==0);
        file.error=0;pos=sizeof(body);copy_limit=0;
        assert(read_one(iter,&file,&pos,buf,sizeof(buf))==-EFAULT && ksu_rc_pos==0);
        copy_limit=3;
        assert(read_one(iter,&file,&pos,buf,sizeof(buf))==3 && ksu_rc_pos==3);
        assert(!memcmp(buf,KERNEL_SU_RC,3));
        copy_limit=(size_t)-1;
        assert(read_one(iter,&file,&pos,buf,sizeof(buf))==(ssize_t)ksu_rc_len-3);
        assert(!memcmp(buf,KERNEL_SU_RC+3,ksu_rc_len-3));
        assert(read_one(iter,&file,&pos,buf,sizeof(buf))==0);
        reset_module(true);size_t custom_len=module_rc_len;
        copy_limit=0;
        assert(read_one(iter,&file,&pos,buf,sizeof(buf))==-EFAULT && module_rc_pos==0 && freed==0);
        copy_limit=3;
        assert(read_one(iter,&file,&pos,buf,sizeof(buf))==3 && module_rc_pos==3 && freed==0);
        assert(!memcmp(buf,module_rc_buf,3));
        char *remaining=strdup(module_rc_buf+3);copy_limit=(size_t)-1;
        assert(read_one(iter,&file,&pos,buf,sizeof(buf))==(ssize_t)custom_len-3);
        assert(!memcmp(buf,remaining,custom_len-3) && freed==1);free(remaining);
        assert(read_one(iter,&file,&pos,buf,sizeof(buf))==0 && freed==1);
    }
    puts("PASS: read/read_iter preserve 34300 original bytes, append core and optional module RC exactly once, and handle short reads, zero reads, errors and partial faults");
}
