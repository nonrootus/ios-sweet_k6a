#include "sweet_gpu_pm4.h"
#include <stdio.h>
#include <string.h>
#define CHECK(x) do {if (!(x)) {fprintf(stderr,"failed line %d\n",__LINE__);return 1;}}while(0)
static unsigned ones(unsigned v){unsigned c=0;while(v){c+=v&1;v>>=1;}return c;}
int main(void){uint32_t h,b[9],saved[9]; unsigned op,n;
 for(op=0;op<128;op++) for(n=0;n<32768;n+=97){
  CHECK(!sweet_gpu_pkt7(op,n,&h));CHECK((h&0xffff0000u)>>28==7);CHECK((h&0x7fff)==n);
  CHECK(((h>>16)&0x7f)==op);CHECK((ones(n)+((h>>15)&1))%2==1);
  CHECK((ones(op)+((h>>23)&1))%2==1);
 }
 CHECK(sweet_gpu_pkt7(128,1,&h)); CHECK(sweet_gpu_pkt7(1,32768,&h));
 memset(b,0xa5,sizeof(b));memcpy(saved,b,sizeof(b));CHECK(sweet_a618_cp_init(b,8));CHECK(!memcmp(b,saved,sizeof(b)));
 CHECK(!sweet_a618_cp_init(b,9));CHECK(b[0]==0x70c80008 && b[1]==0x2f && b[2]==3 && b[3]==0x20000000);
 for(n=4;n<9;n++) { CHECK(b[n]==0); } puts("GPU packet construction checks passed");return 0;}
