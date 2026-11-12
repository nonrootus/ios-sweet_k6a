#include "sweet_smmu_snapshot.h"
#include <assert.h>
#include <stdlib.h>
struct model { uint32_t r[0x10000/4]; unsigned reads; int fail; };
static int rd(void *p,uint32_t off,uint32_t *v) {
    struct model *m=p; m->reads++;
    if (m->fail || (off&3u) || off>=sizeof(m->r)) return -1;
    *v=m->r[off/4]; return 0;
}
int main(void) {
    struct model *m=calloc(1,sizeof(*m)); struct sweet_smmu_snapshot *s=calloc(1,sizeof(*s));
    assert(m && s); struct sweet_smmu_ops ops={m,rd};
    m->r[0x20/4]=0x48016605; m->r[0x24/4]=0x20008005; m->r[0x28/4]=0x00007511;
    m->r[0x800/4]=0x80000005; m->r[0xc00/4]=3; m->r[0x8000/4]=1;
    m->r[0x1800/4]=1; m->r[0xc000/4]=0x41; m->r[0xc058/4]=0x23;
    assert(sweet_smmu_snapshot(&ops,0x10000,s)==0);
    assert(s->groups==5 && s->banks==5 && s->stage2_banks==0 && s->page_shift==12);
    assert(s->stream[0].smr==0x80000005 && s->stream[0].s2cr==3);
    assert(s->bank[0].sctlr==1 && s->bank[0].cba2r==1 && s->bank[4].sctlr==0x41 && s->bank[4].fsr==0x23);
    assert(sweet_smmu_snapshot(&ops,0x8000,s)==SWEET_SMMU_UNSUPPORTED);
    m->r[0x24/4]=0x20008009; assert(sweet_smmu_snapshot(&ops,0x10000,s)==SWEET_SMMU_UNSUPPORTED);
    m->r[0x24/4]=0x20008005; m->r[0x8000/4]=0xffffffffu;
    assert(sweet_smmu_snapshot(&ops,0x10000,s)==SWEET_SMMU_UNSUPPORTED);
    m->fail=1; assert(sweet_smmu_snapshot(&ops,0x10000,s)==SWEET_SMMU_IO);
    free(s);free(m);return 0;
}
