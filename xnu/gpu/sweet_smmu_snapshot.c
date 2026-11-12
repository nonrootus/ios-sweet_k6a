#include "sweet_smmu_snapshot.h"
/* ARM SMMUv2 GR0/GR1 and context bank layout. All offsets in bytes. */
static int read_valid(const struct sweet_smmu_ops *ops, uint32_t off, uint32_t *v) {
    if (ops->read32(ops->ctx,off,v)) return SWEET_SMMU_IO;
    return *v == 0xffffffffu ? SWEET_SMMU_UNSUPPORTED : SWEET_SMMU_OK;
}
int sweet_smmu_snapshot(const struct sweet_smmu_ops *ops, uint32_t aperture,
    struct sweet_smmu_snapshot *out) {
    uint32_t id0,id1,id2,id7,cr0,gfsr,shift,pages,half;
    unsigned groups,banks,s2;
    int rc;
    if (!ops || !ops->read32 || !out || aperture < 0x2000u) return SWEET_SMMU_INVALID;
    if ((rc=read_valid(ops,0x20u,&id0)) || (rc=read_valid(ops,0x24u,&id1)) ||
        (rc=read_valid(ops,0x28u,&id2)) || (rc=read_valid(ops,0x3cu,&id7)) ||
        (rc=read_valid(ops,0u,&cr0)) || (rc=read_valid(ops,0x48u,&gfsr))) return rc;
    if (!(id0 & (1u<<27)) || !(id0 & (1u<<30)) || (id0 & (1u<<8)) ||
        !(id2 & (1u<<12))) return SWEET_SMMU_UNSUPPORTED;
    shift=(id1 & (1u<<31)) ? 16u : 12u;
    pages=1u << (((id1>>28)&7u)+1u);
    half=pages<<shift;
    groups=id0&0xffu; banks=id1&0xffu; s2=(id1>>16)&0xffu;
    if (!groups || groups>SWEET_SMMU_SNAPSHOT_MAX || !banks ||
        banks>SWEET_SMMU_SNAPSHOT_MAX || s2>banks || banks>pages ||
        half > UINT32_MAX/2u || 2u*half != aperture ||
        0xc00u+4u*groups > (1u<<shift) || 0x800u+4u*banks > (1u<<shift))
        return SWEET_SMMU_UNSUPPORTED;
    out->id0=id0;out->id1=id1;out->id2=id2;out->id7=id7;out->scr0=cr0;out->gfsr=gfsr;
    out->page_shift=shift;out->groups=groups;out->banks=banks;out->stage2_banks=s2;
    for (unsigned i=0;i<groups;i++) {
        if ((rc=read_valid(ops,0x800u+4u*i,&out->stream[i].smr)) ||
            (rc=read_valid(ops,0xc00u+4u*i,&out->stream[i].s2cr))) return rc;
    }
    for (unsigned i=0;i<banks;i++) {
        uint32_t cb=half+(i<<shift);
        struct sweet_smmu_snapshot_bank *b=&out->bank[i];
        if ((rc=read_valid(ops,(1u<<shift)+4u*i,&b->cbar)) ||
            (rc=read_valid(ops,(1u<<shift)+0x800u+4u*i,&b->cba2r)) ||
            (rc=read_valid(ops,cb,&b->sctlr)) || (rc=read_valid(ops,cb+0x04u,&b->actlr)) ||
            (rc=read_valid(ops,cb+0x10u,&b->tcr2)) || (rc=read_valid(ops,cb+0x20u,&b->ttbr0_lo)) ||
            (rc=read_valid(ops,cb+0x24u,&b->ttbr0_hi)) || (rc=read_valid(ops,cb+0x30u,&b->tcr)) ||
            (rc=read_valid(ops,cb+0x38u,&b->mair0)) || (rc=read_valid(ops,cb+0x3cu,&b->mair1)) ||
            (rc=read_valid(ops,cb+0x58u,&b->fsr))) return rc;
    }
    return SWEET_SMMU_OK;
}
