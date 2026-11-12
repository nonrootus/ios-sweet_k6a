#include "sweet_gpu_branch.h"
#include <assert.h>
struct model { uint32_t r; unsigned reads,writes,delays,on_after; int fail; };
static int rd(void *p,uint32_t *v) {struct model *m=p; if(m->fail==1)return -1; if(++m->reads>m->on_after && (m->r&1))m->r &= ~(1u<<31); *v=m->r;return 0;}
static int wr(void *p,uint32_t v) {struct model*m=p;m->writes++;if(m->fail==2)return -1;m->r=v;return 0;}
static void delay(void *p,unsigned n){((struct model*)p)->delays+=n;}
int main(void) {
 struct model m={(1u<<31)|0x220,0,0,0,4,0}; struct sweet_gpu_branch_state s={0}; struct sweet_gpu_branch_ops o={&m,rd,wr,delay};
 assert(!sweet_gpu_branch_acquire(&o,&s)); assert(s.acquired && s.owned && !s.poisoned && m.writes==1 && m.delays>=5);
 m=(struct model){1,0,0,0,0,0}; s=(struct sweet_gpu_branch_state){0}; assert(!sweet_gpu_branch_acquire(&o,&s) && !s.owned && !m.writes);
 m=(struct model){1u<<31,0,0,0,1000,0}; s=(struct sweet_gpu_branch_state){0}; assert(sweet_gpu_branch_acquire(&o,&s)==-2 && s.poisoned && s.owned); assert(sweet_gpu_branch_acquire(&o,&s)==-1);
 m=(struct model){1u<<31,0,0,0,1,2}; s=(struct sweet_gpu_branch_state){0}; assert(sweet_gpu_branch_acquire(&o,&s)==-1 && s.poisoned);
 m=(struct model){0xffffffffu,0,0,0,1000,0}; s=(struct sweet_gpu_branch_state){0}; assert(sweet_gpu_branch_acquire(&o,&s)==-1 && !m.writes);
 return 0;
}
