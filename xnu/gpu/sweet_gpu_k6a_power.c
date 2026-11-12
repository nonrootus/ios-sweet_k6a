#include "sweet_gpu_k6a_power.h"
#include "sweet_gpu_gmu.h"
/* Only specific sdmmagpie GPUCC registers used in the GX/CX sequence. */
static int allowed(uint32_t off) {
    return off==0x1008 || off==0x100c || off==0x101c ||
        off==0x106c || off==0x1508 || off==0x1540;
}
static void barrier_read(void) {
#if defined(__aarch64__)
    __asm__ volatile("dmb oshld" ::: "memory");
#else
    __atomic_thread_fence(__ATOMIC_SEQ_CST);
#endif
}
static void barrier_write(void) {
#if defined(__aarch64__)
    __asm__ volatile("dsb osh" ::: "memory");
#else
    __atomic_thread_fence(__ATOMIC_SEQ_CST);
#endif
}
static int reg_read(void *ctx, uint32_t off, uint32_t *value) {
    struct sweet_gpu_k6a_power *p=ctx;
    if (!value || !allowed(off) || off>p->mapped_size || p->mapped_size-off<4) return -1;
    *value=p->gpucc[off/4]; barrier_read(); return 0;
}
static int reg_write(void *ctx, uint32_t off, uint32_t value) {
    struct sweet_gpu_k6a_power *p=ctx;
    if (!allowed(off) || off==0x1540 || off>p->mapped_size || p->mapped_size-off<4) return -1;
    barrier_write(); p->gpucc[off/4]=value; barrier_write(); return 0;
}
static void sleep_us(void *ctx, unsigned us) {
    struct sweet_gpu_k6a_power *p=ctx; p->delay(p->delay_context,us);
}
static int root_clock(void *ctx, int enable) {
    struct sweet_gpu_k6a_power *p=ctx;
    return enable ? sweet_gpu_root_acquire(&p->ops,&p->root) : sweet_gpu_root_release(&p->ops,&p->root);
}
int sweet_gpu_k6a_power_init(struct sweet_gpu_k6a_power *p, volatile void *base,
    size_t size, void (*delay)(void *, unsigned), void *delay_context) {
    if (!p || !base || ((uintptr_t)base & 3u) || size<0x1544 || !delay) return -1;
    *p=(struct sweet_gpu_k6a_power){0};
    p->gpucc=base;p->mapped_size=size;p->delay=delay;p->delay_context=delay_context;
    p->ops=(struct sweet_gpu_gdsc_ops){p,reg_read,reg_write,root_clock,sleep_us};
    return 0;
}
int sweet_gpu_k6a_power_start(struct sweet_gpu_k6a_power *p) {
    int rc;
    if (!p || !p->gpucc || !p->delay || p->started || p->poisoned) return -1;
    /* After first hardware access, any error leaves state uncertain. */
    p->poisoned=1;
    rc=sweet_gpu_cx_enable(&p->ops,&p->cx);
    if (rc) return rc;
    rc=sweet_gpu_gx_enable(&p->ops,&p->gx);
    if (rc) return rc;
    p->started=1;p->poisoned=0;return 0;
}

/* Firmware copy is supplied by the early-boot kernel store. */
extern int sweet_gpu_firmware_get(unsigned, const void **, size_t *);
struct sweet_gmu_window { volatile uint32_t *base; size_t size; };
static int gmu_read(void *ctx, uint32_t off, uint32_t *value) {
    struct sweet_gmu_window *w=ctx;
    if (!value || off!=0x14000 || off>w->size || w->size-off<4) return -1;
    *value=w->base[off/4];barrier_read();return 0;
}
static int gmu_write(void *ctx, uint32_t off, uint32_t value) {
    struct sweet_gmu_window *w=ctx;
    if (off<0x3000 || off>=0xb000 || (off&3u) || off>w->size || w->size-off<4) return -1;
    barrier_write();w->base[off/4]=value;barrier_write();return 0;
}
int sweet_gpu_k6a_gmu_load(struct sweet_gpu_k6a_power *p, volatile void *base,
    size_t size, int clocks_verified, size_t *written) {
    const void *fw; size_t fw_size; int rc;
    if (!p || !p->started || p->poisoned || !base || ((uintptr_t)base&3u) ||
        size<0x14004 || !clocks_verified || !written) return -1;
    if (sweet_gpu_firmware_get(0,&fw,&fw_size)) return -1;
    struct sweet_gmu_window window={(volatile uint32_t *)base,size};
    struct sweet_gpu_gmu_ops ops={&window,gmu_read,gmu_write};
    p->poisoned=1;
    rc=sweet_gpu_gmu_load_legacy(&ops,fw,fw_size,written);
    if (!rc) p->poisoned=0;
    return rc;
}
