#ifndef SWEET_GPU_GDSC_H
#define SWEET_GPU_GDSC_H
#include <stdint.h>
/* All offsets relative to sdmmagpie GPUCC (0x05090000). Call only after
 * parent rails and the configuration bus are safely enabled. Caller owns
 * serialization, clock/reference accounting and recovery on partial failure. */
struct sweet_gpu_gdsc_ops {
    void *ctx;
    int (*read32)(void *, uint32_t, uint32_t *);
    int (*write32)(void *, uint32_t, uint32_t);
    int (*root_clock)(void *, int enable);
    void (*delay_us)(void *, unsigned);
};
struct sweet_gpu_gdsc_result { unsigned root_held, stage; uint32_t status; };
int sweet_gpu_cx_enable(const struct sweet_gpu_gdsc_ops *, struct sweet_gpu_gdsc_result *);
int sweet_gpu_gx_enable(const struct sweet_gpu_gdsc_ops *, struct sweet_gpu_gdsc_result *);
/* Caller must serialize all root-clock clients and ensure the parent clock
 * is running. Releases only a force-enable bit acquired by this helper. */
struct sweet_gpu_root_state { unsigned active, owned; };
int sweet_gpu_root_acquire(const struct sweet_gpu_gdsc_ops *, struct sweet_gpu_root_state *);
int sweet_gpu_root_release(const struct sweet_gpu_gdsc_ops *, struct sweet_gpu_root_state *);
#endif
