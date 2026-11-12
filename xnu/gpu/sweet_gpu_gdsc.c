#include "sweet_gpu_gdsc.h"
/* Derived from the captured sweet_k6a FDT and Qualcomm GDSC register protocol.
 * No address mapping or power/clock vote occurs here. Do not wire to boot
 * until parent supplies, the root clock, and shared ownership are established. */
#define GX_RESET 0x1008u
#define GX_GDSC 0x100cu
#define GX_DOMAIN 0x1508u
#define PWR_ON (1u << 31)
#define HW_CTRL (1u << 1)
#define COLLAPSE (1u << 0)
#define RESET (1u << 0)
#define GMEM_RESET (1u << 4)
#define GMEM_CLAMP (1u << 0)
static int change(const struct sweet_gpu_gdsc_ops *o, uint32_t reg,
    uint32_t set, uint32_t clear) {
    uint32_t value, check;
    if (o->read32(o->ctx, reg, &value)) return -1;
    value = (value | set) & ~clear;
    if (o->write32(o->ctx, reg, value) || o->read32(o->ctx, reg, &check)) return -1;
    return ((check & (set | clear)) == (value & (set | clear))) ? 0 : -1;
}
int sweet_gpu_gx_enable(const struct sweet_gpu_gdsc_ops *o,
    struct sweet_gpu_gdsc_result *result) {
    uint32_t state;
    if (!o || !result || !o->read32 || !o->write32 || !o->root_clock || !o->delay_us) return -1;
    result->root_held=0; result->stage=0; result->status=0;
    if (o->root_clock(o->ctx, 1)) return -2;
    result->root_held=1; result->stage=1;
    if (o->read32(o->ctx, GX_GDSC, &state)) return -2;
    result->status=state;
    /* Do not reset a running or hardware-controlled domain. */
    if ((state & (PWR_ON | HW_CTRL)) || !(state & COLLAPSE)) return -3;
    if (change(o, GX_RESET, RESET, 0)) return -2;
    result->stage=2; o->delay_us(o->ctx, 1);
    if (change(o, GX_RESET, 0, RESET)) return -2;
    if (change(o, GX_DOMAIN, GMEM_RESET, 0)) return -2;
    result->stage=3; o->delay_us(o->ctx, 1);
    if (change(o, GX_DOMAIN, 0, GMEM_RESET)) return -2;
    if (change(o, GX_DOMAIN, 0, GMEM_CLAMP)) return -2;
    if (change(o, GX_GDSC, 0, COLLAPSE)) return -2;
    result->stage=4; o->delay_us(o->ctx, 1);
    for (unsigned i=0; i<100; ++i) {
        if (o->read32(o->ctx, GX_GDSC, &state)) return -2;
        result->status=state;
        if (state & PWR_ON) {
            result->stage=5;
            if (o->root_clock(o->ctx, 0)) return -2;
            result->root_held=0; return 0;
        }
        o->delay_us(o->ctx, 1);
    }
    return -4; /* Keep clock held after uncertain failure for caller recovery. */
}

/* Root generator for GX GFX3D at GPUCC + 0x101c. Parent must be prepared;
 * this does not configure PLL, source mux, voltage or bus access. */
int sweet_gpu_root_acquire(const struct sweet_gpu_gdsc_ops *o, struct sweet_gpu_root_state *s) {
    uint32_t value;
    if (!o || !s || !o->read32 || !o->write32 || !o->delay_us || s->active) return -1;
    if (o->read32(o->ctx, 0x101c, &value)) return -2;
    s->active=1; s->owned=!(value & 2u);
    if (s->owned && o->write32(o->ctx, 0x101c, value | 2u)) return -2;
    for (unsigned i=0;i<500;i++) {
        if (o->read32(o->ctx, 0x101c, &value)) return -2;
        if (!(value & (1u << 31))) return 0;
        o->delay_us(o->ctx, 1);
    }
    return -4;
}
int sweet_gpu_root_release(const struct sweet_gpu_gdsc_ops *o, struct sweet_gpu_root_state *s) {
    uint32_t value;
    if (!o || !s || !s->active || !o->read32 || !o->write32 || !o->delay_us) return -1;
    if (s->owned) {
        if (o->read32(o->ctx, 0x101c, &value) || o->write32(o->ctx, 0x101c, value & ~2u)) return -2;
        o->delay_us(o->ctx, 100);
    }
    s->active=0; s->owned=0; return 0;
}

/* CX GDSC has a separate hardware status register on sweet_k6a. Parent
 * supply and the configuration bus must already be enabled by the caller. */
int sweet_gpu_cx_enable(const struct sweet_gpu_gdsc_ops *o,
    struct sweet_gpu_gdsc_result *result) {
    uint32_t ctrl, status;
    if (!o || !result || !o->read32 || !o->write32 || !o->delay_us) return -1;
    result->root_held=0; result->stage=0; result->status=0;
    if (o->read32(o->ctx, 0x106c, &ctrl) || o->read32(o->ctx, 0x1540, &status)) return -2;
    result->status=status;
    if ((ctrl & HW_CTRL) || (status & PWR_ON) || !(ctrl & COLLAPSE)) return -3;
    if (change(o, 0x106c, 0, COLLAPSE)) return -2;
    result->stage=1; o->delay_us(o->ctx, 1);
    for (unsigned i=0;i<500;i++) {
        if (o->read32(o->ctx, 0x1540, &status)) return -2;
        result->status=status;
        if (status & PWR_ON) { result->stage=2; return 0; }
        o->delay_us(o->ctx, 1);
    }
    return -4; /* state unknown; no automatic rollback */
}
