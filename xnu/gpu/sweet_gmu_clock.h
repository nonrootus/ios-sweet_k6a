#ifndef SWEET_GMU_CLOCK_H
#define SWEET_GMU_CLOCK_H
#include <stdint.h>
/* GPUCC-relative offsets. Caller must own the clock, establish CX and the
 * 300 MHz divided GPLL0 parent, and serialize all other clock clients.
 * No automatic rollback: failure after a write leaves state uncertain. */
struct sweet_gmu_clock_ops { void *ctx; int (*read)(void *,uint32_t,uint32_t *); int (*write)(void *,uint32_t,uint32_t); void (*delay_us)(void *,unsigned); };
struct sweet_gmu_clock_state { unsigned stage, poisoned; uint32_t last; };
int sweet_gmu_clock_enable_200(const struct sweet_gmu_clock_ops *, int parent_verified, struct sweet_gmu_clock_state *);
#endif
