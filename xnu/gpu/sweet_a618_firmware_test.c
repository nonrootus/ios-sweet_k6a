#include "sweet_a618_firmware.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static unsigned char *load(const char *path, size_t *len) {
    FILE *f = fopen(path,"rb"); long n; unsigned char *p;
    if (!f || fseek(f,0,SEEK_END) || (n=ftell(f)) < 0 || fseek(f,0,SEEK_SET)) exit(2);
    p=malloc((size_t)n+1); if (!p || fread(p,1,(size_t)n,f)!=(size_t)n) exit(2);
    fclose(f); *len=(size_t)n; return p;
}
#define CHECK(x) do {if (!(x)) {fprintf(stderr,"check failed at %d\n",__LINE__); return 1;}} while (0)
int main(int argc,char **argv) {
    size_t gn,sn; struct sweet_a618_firmware_view v; unsigned char *g,*s; unsigned char fake[16]={0};
    if(argc!=3) return 2;
    g=load(argv[1],&gn); s=load(argv[2],&sn);
    CHECK(sweet_a618_firmware_prepare(g,gn,s,sn,&v)==SWEET_A618_FW_OK);
    CHECK(v.gmu==g && v.gmu_size==gn && v.sqe_payload==s+4 && v.sqe_payload_size==sn-4);
    CHECK(sweet_a618_firmware_prepare(g,0,s,sn,&v)==SWEET_A618_FW_BAD_GMU_SIZE);
    CHECK(sweet_a618_firmware_prepare(g,0x8001,s,sn,&v)==SWEET_A618_FW_BAD_GMU_SIZE);
    CHECK(sweet_a618_firmware_prepare(g,gn,s,15,&v)==SWEET_A618_FW_BAD_SQE_SIZE);
    CHECK(sweet_a618_firmware_prepare(g,gn,fake,sizeof(fake),&v)==SWEET_A618_FW_OLD_SQE);
    fake[4]=0x0a;fake[12]=1;
    CHECK(sweet_a618_firmware_prepare(g,gn,fake,sizeof(fake),&v)==SWEET_A618_FW_OK);
    CHECK(sweet_a618_firmware_prepare(NULL,gn,s,sn,&v)==SWEET_A618_FW_BAD_ARGUMENT);
    free(g);free(s);puts("A618 firmware checks passed");return 0;
}
