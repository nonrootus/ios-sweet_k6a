#include "sweet_smmu_discover.h"
#define ID0 0x20u
#define ID1 0x24u
#define ID2 0x28u
#define SMR 0x800u
#define S2CR 0xc00u
int sweet_smmu_discover(const struct sweet_smmu_ops *ops, uint16_t sid,
    struct sweet_smmu_match *out) {
    uint32_t id0, id1, id2, smr, s2cr;
    unsigned n, count, banks, found=0;
    if (!ops || !ops->read32 || !out || sid>0x7fff) return SWEET_SMMU_INVALID;
    if (ops->read32(ops->ctx,ID0,&id0) || ops->read32(ops->ctx,ID1,&id1) ||
        ops->read32(ops->ctx,ID2,&id2)) return SWEET_SMMU_IO;
    if (id0==0xffffffffu || id1==0xffffffffu || id2==0xffffffffu ||
        !(id0 & (1u<<27)) || !(id0 & (1u<<30)) || (id0 & (1u<<8)) ||
        !(id2 & (1u<<12))) return SWEET_SMMU_UNSUPPORTED;
    count=id0 & 0xffu; banks=id1 & 0xffu;
    if (!count || count>128 || !banks || banks>128) return SWEET_SMMU_UNSUPPORTED;
    out->id0=id0; out->id1=id1; out->id2=id2;
    for (n=0; n<count; ++n) {
        uint32_t mask, id;
        if (ops->read32(ops->ctx,SMR+4u*n,&smr)) return SWEET_SMMU_IO;
        if (!(smr & (1u<<31))) continue;
        mask=(smr>>16)&0x7fffu; id=smr&0x7fffu;
        if (((sid^id)&(~mask&0x7fffu)) != 0) continue;
        if (found) return SWEET_SMMU_AMBIGUOUS;
        if (ops->read32(ops->ctx,S2CR+4u*n,&s2cr)) return SWEET_SMMU_IO;
        out->index=n; out->smr=smr; out->s2cr=s2cr;
        out->type=(s2cr>>16)&3u; out->context_bank=s2cr&0xffu;
        if (out->type==3 || (out->type==0 && out->context_bank>=banks)) return SWEET_SMMU_INVALID;
        found=1;
    }
    return found ? SWEET_SMMU_OK : SWEET_SMMU_NO_MATCH;
}
