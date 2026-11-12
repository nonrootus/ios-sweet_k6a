#ifndef SWEET_GPU_K6A_POWER_H
#define SWEET_GPU_K6A_POWER_H
#include "sweet_gpu_gdsc.h"
#include <stddef.h>
/* The caller owns the mapping, parent supplies, clock parents and all locks.
 * This experimental code is not called during boot. */
struct sweet_gpu_k6a_power {
    volatile uint32_t *gpucc;
    size_t mapped_size;
    void *delay_context;
    void (*delay)(void *, unsigned);
    struct sweet_gpu_gdsc_ops ops;
    struct sweet_gpu_root_state root;
    struct sweet_gpu_gdsc_result cx, gx;
    unsigned started, poisoned;
};
int sweet_gpu_k6a_power_init(struct sweet_gpu_k6a_power *, volatile void *, size_t,
    void (*)(void *, unsigned), void *);
int sweet_gpu_k6a_power_start(struct sweet_gpu_k6a_power *);
/* Caller must separately establish and verify GMU clock/bus readiness. */
int sweet_gpu_k6a_gmu_load(struct sweet_gpu_k6a_power *, volatile void *, size_t, int, size_t *);
#endif
