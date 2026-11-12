#include "sweet_smmu_discover.h"
#include <assert.h>
#include <string.h>
struct model { uint32_t r[0x1000/4]; int fail; };
static int rd(void *p, uint32_t offset, uint32_t *value) {
    struct model *m=p; if (m->fail || offset>=sizeof(m->r)) return -1;
    *value=m->r[offset/4]; return 0;
}
int main(void) {
    struct model m; struct sweet_smmu_match out; struct sweet_smmu_ops op={&m,rd};
    memset(&m,0,sizeof m); m.r[0x20/4]=(1u<<27)|(1u<<30)|5; m.r[0x24/4]=8; m.r[0x28/4]=1u<<12;
    assert(sweet_smmu_discover(&op,4,&out)==SWEET_SMMU_NO_MATCH);
    m.r[0x800/4]=(1u<<31)|(1u<<16)|4; m.r[0xc00/4]=7;
    assert(sweet_smmu_discover(&op,5,&out)==0 && out.index==0 && out.context_bank==7 && out.type==0);
    m.r[0x804/4]=(1u<<31)|5;
    assert(sweet_smmu_discover(&op,5,&out)==SWEET_SMMU_AMBIGUOUS);
    m.r[0x804/4]=0; m.r[0xc00/4]=8;
    assert(sweet_smmu_discover(&op,4,&out)==SWEET_SMMU_INVALID);
    m.r[0xc00/4]=1u<<16;
    assert(sweet_smmu_discover(&op,4,&out)==0 && out.type==1);
    m.r[0x20/4]|=1u<<8;
    assert(sweet_smmu_discover(&op,4,&out)==SWEET_SMMU_UNSUPPORTED);
    m.fail=1; assert(sweet_smmu_discover(&op,4,&out)==SWEET_SMMU_IO);
    return 0;
}
