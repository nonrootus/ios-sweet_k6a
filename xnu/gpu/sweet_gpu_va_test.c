#include "sweet_gpu_va.h"
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#define N 96
#define CHECK(c) do { if (!(c)) {fprintf(stderr,"failure line %d\n",__LINE__);return 1;} } while (0)
static uint32_t state=12345;
static uint32_t next(void) {state=state*1664525u+1013904223u;return state;}
int main(void) {
    struct sweet_gpu_va v; uint8_t bitmap[N]={0};
    struct {uint64_t addr; unsigned len;} live[N]={{0}};
    unsigned i,step; uint64_t a; const uint64_t base=0x10000;
    CHECK(sweet_gpu_va_init(&v,0,0x10000)!=0);
    CHECK(sweet_gpu_va_init(&v,base,base+N*SWEET_GPU_VA_ALIGN)==0);
    CHECK(sweet_gpu_va_alloc(&v,0,&a)!=0);
    CHECK(sweet_gpu_va_alloc(&v,UINT64_MAX,&a)!=0);
    for(step=0;step<30000;step++) {
        unsigned slot=next()%N;
        if(live[slot].addr) {
            unsigned idx=(unsigned)((live[slot].addr-base)/SWEET_GPU_VA_ALIGN);
            CHECK(sweet_gpu_va_free(&v,live[slot].addr,(uint64_t)live[slot].len*SWEET_GPU_VA_ALIGN)==0);
            for(i=0;i<live[slot].len;i++){CHECK(bitmap[idx+i]);bitmap[idx+i]=0;}
            CHECK(sweet_gpu_va_free(&v,live[slot].addr,(uint64_t)live[slot].len*SWEET_GPU_VA_ALIGN)!=0);
            live[slot].addr=0;
        } else {
            unsigned len=next()%5+1, start=N;
            for(i=0;i+len<=N;i++){unsigned j; for(j=0;j<len&&bitmap[i+j]==0;j++){} if(j==len){start=i;break;}}
            if(start==N) CHECK(sweet_gpu_va_alloc(&v,(uint64_t)len*SWEET_GPU_VA_ALIGN,&a)!=0);
            else {
                CHECK(sweet_gpu_va_alloc(&v,(uint64_t)len*SWEET_GPU_VA_ALIGN-1,&a)==0);
                CHECK(a==base+(uint64_t)start*SWEET_GPU_VA_ALIGN);
                for(i=0;i<len;i++){CHECK(!bitmap[start+i]);bitmap[start+i]=1;}
                live[slot].addr=a;live[slot].len=len;
            }
        }
    }
    puts("GPU VA allocator stress test passed");return 0;
}
