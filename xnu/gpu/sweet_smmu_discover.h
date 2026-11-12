#ifndef SWEET_SMMU_DISCOVER_H
#define SWEET_SMMU_DISCOVER_H
#include <stdint.h>
/* The caller must ensure SMMU register access is powered, clocks are enabled,
 * and mappings cannot change during the scan. This helper never writes MMIO.
 * It does not establish ownership or authorize changes to a mapping. */
struct sweet_smmu_ops { void *ctx; int (*read32)(void *, uint32_t, uint32_t *); };
enum sweet_smmu_result { SWEET_SMMU_OK=0, SWEET_SMMU_NO_MATCH=1,
    SWEET_SMMU_UNSUPPORTED=-1, SWEET_SMMU_IO=-2, SWEET_SMMU_AMBIGUOUS=-3,
    SWEET_SMMU_INVALID=-4 };
struct sweet_smmu_match { uint32_t id0, id1, id2, smr, s2cr; unsigned index, type, context_bank; };
int sweet_smmu_discover(const struct sweet_smmu_ops *, uint16_t, struct sweet_smmu_match *);
#endif
