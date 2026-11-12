#ifndef SWEET_GPU_GMU_H
#define SWEET_GPU_GMU_H
#include <stddef.h>
#include <stdint.h>
/* Offsets relative to GMU window 0x0506a000. Caller must ensure power,
 * clocks, ownership, bus access and CM3 reset before using this interface. */
struct sweet_gpu_gmu_ops {
    void *ctx;
    int (*read32)(void *, uint32_t, uint32_t *);
    int (*write32)(void *, uint32_t, uint32_t);
};
int sweet_gpu_gmu_load_legacy(const struct sweet_gpu_gmu_ops *,
    const void *, size_t, size_t *written);
int sweet_gpu_gmu_verify_legacy(const struct sweet_gpu_gmu_ops *,
    const void *, size_t, size_t *matched);
#endif
