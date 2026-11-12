#ifndef SWEET_SMMU_SNAPSHOT_H
#define SWEET_SMMU_SNAPSHOT_H
#include "sweet_smmu_discover.h"
#include <stdint.h>
#define SWEET_SMMU_SNAPSHOT_MAX 128u
struct sweet_smmu_snapshot_stream { uint32_t smr, s2cr; };
struct sweet_smmu_snapshot_bank {
    uint32_t cbar, cba2r, sctlr, actlr, tcr2, ttbr0_lo, ttbr0_hi, tcr, mair0, mair1, fsr;
};
struct sweet_smmu_snapshot {
    uint32_t id0, id1, id2, id7, scr0, gfsr;
    unsigned page_shift, groups, banks, stage2_banks;
    struct sweet_smmu_snapshot_stream stream[SWEET_SMMU_SNAPSHOT_MAX];
    struct sweet_smmu_snapshot_bank bank[SWEET_SMMU_SNAPSHOT_MAX];
};
/* Read-only nonsecure view. Caller owns synchronization and a powered MMIO
 * window of aperture bytes. Results can be partial on error. Disabled/unmatched
 * entries do not establish ownership, security state or permission to write. */
int sweet_smmu_snapshot(const struct sweet_smmu_ops *, uint32_t aperture,
    struct sweet_smmu_snapshot *);
#endif
