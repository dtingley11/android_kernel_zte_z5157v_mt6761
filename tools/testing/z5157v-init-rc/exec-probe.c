/* Device-only regression probe: executes ksud --version, never boot stages. */
#include <stdio.h>
#include <unistd.h>
#include <fcntl.h>
#include <string.h>
#include <errno.h>
#include <sys/wait.h>
static int context(const char *path,const char *value) {
 int fd=open(path,O_WRONLY);if(fd<0){perror(path);return 1;}
 int n=write(fd,value,strlen(value));int e=errno;close(fd);errno=e;
 if(n<0){perror(path);return 1;}return 0;
}
int main(int argc,char **argv) {
 if(argc!=2)return 2;
 pid_t child=fork();
 if(child<0){perror("fork");return 5;}
 if(child>0){int status;if(waitpid(child,&status,0)<0){perror("waitpid");return 6;}printf("%s: child status=%d\n",argv[1],WIFEXITED(status)?WEXITSTATUS(status):128+WTERMSIG(status));return 0;}

 if(context("/proc/self/attr/current","u:r:init:s0"))return 3;
 if(context("/proc/self/attr/exec","u:r:su:s0"))return 4;
 if(!strcmp(argv[1],"direct")) {
  char *args[]={"/data/adb/ksud","--version",NULL};execv(args[0],args);
 } else if(!strcmp(argv[1],"shell")) {
  char *args[]={"/system/bin/sh","-c","exec /data/adb/ksud --version",NULL};execv(args[0],args);
 } else return 2;
 int result=errno==EACCES?13:1;perror("exec probe");return result;
}
