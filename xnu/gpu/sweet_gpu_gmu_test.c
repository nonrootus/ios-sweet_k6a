#include "sweet_gpu_gmu.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
struct sim { uint32_t reset, ram[0x8000/4]; size_t fail_at, writes; };
static int rd(void *c,uint32_t off,uint32_t *v) { struct sim *s=c; if(off==0x14000) *v=s->reset; else if(off>=0x3000 && off<0xb000 && !(off&3)) *v=s->ram[(off-0x3000)/4]; else return -1; return 0; }
static int wr(void *c,uint32_t off,uint32_t v) { struct sim *s=c; if(off<0x3000 || off>=0xb000 || (off&3) || s->writes==s->fail_at)return -1; s->ram[(off-0x3000)/4]=v;s->writes++;return 0; }
int main(int argc,char **argv) {
 assert(argc==2);FILE *f=fopen(argv[1],"rb");assert(f);unsigned char b[0x8000];
 assert(fread(b,1,sizeof(b),f)==sizeof(b));assert(fgetc(f)==EOF);fclose(f);
 struct sim *s=calloc(1,sizeof(*s));assert(s);s->fail_at=(size_t)-1;
 struct sweet_gpu_gmu_ops o={s,rd,wr};size_t n=123;
 assert(sweet_gpu_gmu_load_legacy(&o,b,sizeof(b),&n)==-3 && !n && !s->writes);
 s->reset=1;assert(!sweet_gpu_gmu_load_legacy(&o,b,sizeof(b),&n));
 assert(n==sizeof(b) && s->writes==sizeof(b)/4 && !memcmp(s->ram,b,sizeof(b)));
 assert(!sweet_gpu_gmu_verify_legacy(&o,b,sizeof(b),&n) && n==sizeof(b));
 s->ram[10]^=1; assert(sweet_gpu_gmu_verify_legacy(&o,b,sizeof(b),&n)==-4 && n==40); s->ram[10]^=1;
 s->reset=0; assert(sweet_gpu_gmu_verify_legacy(&o,b,sizeof(b),&n)==-3 && n==0); s->reset=1;
 s->writes=0;s->fail_at=4096;
 assert(sweet_gpu_gmu_load_legacy(&o,b,sizeof(b),&n)==-2 && n==16384);
 assert(sweet_gpu_gmu_load_legacy(&o,b,sizeof(b)-1,&n)==-1);
 free(s);return 0;
}
