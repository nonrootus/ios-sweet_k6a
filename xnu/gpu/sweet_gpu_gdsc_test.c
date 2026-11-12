#include "sweet_gpu_gdsc.h"
#include <assert.h>
#include <stddef.h>
struct sim { uint32_t regs[0x1600/4]; int root, writes, enable_power; unsigned us; };
static int rd(void *c,uint32_t off,uint32_t *v) { struct sim *s=c; if(off>=0x1600)return -1; *v=s->regs[off/4];return 0; }
static int wr(void *c,uint32_t off,uint32_t v) { struct sim *s=c; if(off>=0x1600)return -1; ++s->writes; s->regs[off/4]=v; if(off==0x100c && !(v&1) && s->enable_power)s->regs[off/4]|=1u<<31; if(off==0x106c && !(v&1) && s->enable_power)s->regs[0x1540/4]|=1u<<31; return 0; }
static int root(void *c,int on) {struct sim *s=c;s->root=on;return 0;}
static void delay(void *c,unsigned us) {((struct sim *)c)->us+=us;}
int main(void) {
 struct sim s={0};struct sweet_gpu_gdsc_ops ops={&s,rd,wr,root,delay};struct sweet_gpu_gdsc_result r;
 s.regs[0x100c/4]=1;s.regs[0x1508/4]=1;s.enable_power=1;
 assert(!sweet_gpu_gx_enable(&ops,&r));assert(r.stage==5 && !r.root_held && !s.root && (r.status>>31));
 assert(!(s.regs[0x1508/4]&17) && !(s.regs[0x1008/4]&1) && s.us>=3);
 s.regs[0x100c/4]=1u<<31;s.writes=0;
 assert(sweet_gpu_gx_enable(&ops,&r)==-3 && s.writes==0 && r.root_held);
 s.regs[0x100c/4]=1;s.enable_power=0;s.writes=0;s.us=0;
 assert(sweet_gpu_gx_enable(&ops,&r)==-4 && r.stage==4 && r.root_held && s.root && s.us>=100);
 assert(sweet_gpu_gx_enable(NULL,&r)==-1);
 struct sweet_gpu_root_state clock={0};
 s.regs[0x101c/4]=0;s.us=0;
 assert(!sweet_gpu_root_acquire(&ops,&clock) && clock.owned && (s.regs[0x101c/4]&2));
 assert(!sweet_gpu_root_release(&ops,&clock) && !(s.regs[0x101c/4]&2) && s.us==100);
 s.regs[0x101c/4]=2;s.us=0;
 assert(!sweet_gpu_root_acquire(&ops,&clock) && !clock.owned);
 assert(!sweet_gpu_root_release(&ops,&clock) && (s.regs[0x101c/4]&2) && s.us==0);
 s.regs[0x101c/4]=(1u<<31);s.us=0;
 assert(sweet_gpu_root_acquire(&ops,&clock)==-4 && clock.active && clock.owned && s.us==500);
 assert(!sweet_gpu_root_release(&ops,&clock));
 s.regs[0x106c/4]=1;s.regs[0x1540/4]=0;s.enable_power=1;
 assert(!sweet_gpu_cx_enable(&ops,&r) && r.stage==2 && (r.status>>31));
 s.regs[0x106c/4]=1;s.regs[0x1540/4]=0;s.enable_power=0;s.us=0;
 assert(sweet_gpu_cx_enable(&ops,&r)==-4 && r.stage==1 && s.us>=500);
 s.regs[0x106c/4]=1;s.regs[0x1540/4]=1u<<31;s.writes=0;
 assert(sweet_gpu_cx_enable(&ops,&r)==-3 && s.writes==0);
 return 0;
}
