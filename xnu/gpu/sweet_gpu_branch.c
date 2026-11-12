#include "sweet_gpu_branch.h"
#define VOTE 1u
#define OFF (1u<<31)
int sweet_gpu_branch_acquire(const struct sweet_gpu_branch_ops *o, struct sweet_gpu_branch_state *s) {
    uint32_t v;
    if (!o || !s || !o->read || !o->write || !o->delay_us || s->acquired || s->poisoned) return -1;
    if(o->read(o->ctx,&v)) return -1;
    s->last=v;
    if(v==0xffffffffu) return -1;
    if (!(v & VOTE)) {
        s->poisoned=1;
        if(o->write(o->ctx,v|VOTE)) return -1;
        s->owned=1;
    } else {
        /* An existing vote is shared and must never be released by us. */
        s->poisoned=1;
    }
    o->delay_us(o->ctx,5);
    for(unsigned i=0;i<200;i++) {
        if(o->read(o->ctx,&v)) return -1;
        s->last=v;
        if(v==0xffffffffu || !(v&VOTE)) return -1;
        if(!(v&OFF)) {s->acquired=1; s->poisoned=0; return 0;}
        o->delay_us(o->ctx,1);
    }
    return -2;
}
