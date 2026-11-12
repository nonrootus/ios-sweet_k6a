#include "sweet_gmu_clock.h"
#include <assert.h>
struct model { uint32_t r[0x1200/4]; int stuck, fail, drop_cfg; unsigned writes; };
static int rd(void *p,uint32_t off,uint32_t *v) {struct model*m=p;if(m->fail)return -1;*v=m->r[off/4];return 0;}
static int wr(void *p,uint32_t off,uint32_t v) {struct model*m=p;if(m->fail)return -1;m->writes++;if (!(m->drop_cfg && off==0x1124)) m->r[off/4]=v;if(!m->stuck && off==0x1120)m->r[off/4]&=~1u;if(!m->stuck && off==0x1098){m->r[off/4]&=~(1u<<31);m->r[0x1120/4]&=~(1u<<31);}return 0;}
static void delay(void *p,unsigned n){(void)p;(void)n;}
int main(void) { struct model m={0};struct sweet_gmu_clock_state s={0};struct sweet_gmu_clock_ops o={&m,rd,wr,delay};
 m.r[0x1120/4]=1u<<31;m.r[0x1098/4]=1u<<31;m.r[0x109c/4]=1;
 assert(sweet_gmu_clock_enable_200(&o,0,&s)==-1 && !m.writes);
 assert(sweet_gmu_clock_enable_200(&o,1,&s)==0 && s.stage==3 && !s.poisoned && (m.r[0x1124/4]&0x71f)==0x602);
 m=(struct model){0};s=(struct sweet_gmu_clock_state){0};m.r[0x1120/4]=1u<<31;m.r[0x1098/4]=(1u<<31);m.r[0x109c/4]=1;m.stuck=1;
 assert(sweet_gmu_clock_enable_200(&o,1,&s)==-4 && s.poisoned && s.stage==1);assert(sweet_gmu_clock_enable_200(&o,1,&s)==-1);
 m=(struct model){0};s=(struct sweet_gmu_clock_state){0};m.r[0x1120/4]=1u<<31;m.r[0x1098/4]=1u<<31;m.r[0x109c/4]=1;m.drop_cfg=1;
 assert(sweet_gmu_clock_enable_200(&o,1,&s)==-5 && s.poisoned && s.stage==1 && m.writes==2);
 m=(struct model){0};s=(struct sweet_gmu_clock_state){0};m.r[0x1120/4]=1u<<31;m.r[0x1098/4]=1;m.r[0x109c/4]=1;
 assert(sweet_gmu_clock_enable_200(&o,1,&s)==-3 && !m.writes);
 return 0;
}
