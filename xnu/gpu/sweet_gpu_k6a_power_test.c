#include "sweet_gpu_k6a_power.h"
#include <assert.h>
#include <stdint.h>
static uint32_t mmio[0x9000/4], gmu[0x31000/4];
static unsigned char fw[0x8000];
int sweet_gpu_firmware_get(unsigned n,const void **data,size_t *size) { if(n) return -1; *data=fw;*size=sizeof(fw);return 0; }
static void delay(void *ctx,unsigned us) {
    (void)ctx;(void)us;
    if (!(mmio[0x106c/4]&1u)) mmio[0x1540/4]|=1u<<31;
    if (!(mmio[0x100c/4]&1u)) mmio[0x100c/4]|=1u<<31;
}
int main(void) {
    struct sweet_gpu_k6a_power p;
    assert(sweet_gpu_k6a_power_init(&p,mmio,0x100,delay,0)==-1);
    mmio[0x106c/4]=1;mmio[0x100c/4]=1;mmio[0x1508/4]=1;
    assert(!sweet_gpu_k6a_power_init(&p,mmio,sizeof(mmio),delay,0));
    assert(!sweet_gpu_k6a_power_start(&p));
    assert(p.started && !p.poisoned && p.cx.stage==2 && p.gx.stage==5);
    assert(!(mmio[0x101c/4]&2u) && !p.root.active);
    assert(sweet_gpu_k6a_power_start(&p)==-1);
    size_t written=0;fw[0]=0x12;fw[sizeof(fw)-1]=0x34;gmu[0x14000/4]=1;
    assert(sweet_gpu_k6a_gmu_load(&p,gmu,sizeof(gmu),0,&written)==-1);
    assert(!sweet_gpu_k6a_gmu_load(&p,gmu,sizeof(gmu),1,&written));
    assert(written==sizeof(fw) && gmu[0x3000/4]==0x12 && gmu[0xaffc/4]==0x34000000u);
    gmu[0x14000/4]=0;
    assert(sweet_gpu_k6a_gmu_load(&p,gmu,sizeof(gmu),1,&written)==-3 && p.poisoned);
    mmio[0x1540/4]=1u<<31;mmio[0x106c/4]=1;
    assert(!sweet_gpu_k6a_power_init(&p,mmio,sizeof(mmio),delay,0));
    assert(sweet_gpu_k6a_power_start(&p)==-3 && p.poisoned);
    assert(sweet_gpu_k6a_power_start(&p)==-1);
    return 0;
}
