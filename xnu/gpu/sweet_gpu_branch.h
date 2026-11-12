#ifndef SWEET_GPU_BRANCH_H
#define SWEET_GPU_BRANCH_H
#include <stdint.h>
/* Caller owns serialization and must provide the parent power/clock.
 * A failure after write leaves state uncertain: do not retry or release. */
struct sweet_gpu_branch_ops { void *ctx; int (*read)(void *,uint32_t *); int (*write)(void *,uint32_t); void (*delay_us)(void *,unsigned); };
struct sweet_gpu_branch_state { unsigned acquired, owned, poisoned; uint32_t last; };
int sweet_gpu_branch_acquire(const struct sweet_gpu_branch_ops *,struct sweet_gpu_branch_state *);
#endif
