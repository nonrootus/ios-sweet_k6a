#include "sweet_gpu_pm4.h"
static uint32_t parity(uint32_t v) {
    uint32_t p = 1;
    while (v) { p ^= v & 1u; v >>= 1; }
    return p;
}
int sweet_gpu_pkt7(uint8_t opcode, uint16_t words, uint32_t *out) {
    if (!out || opcode > 0x7f || words > 0x7fff) return -1;
    *out = UINT32_C(0x70000000) | words | (parity(words) << 15) |
        ((uint32_t)opcode << 16) | (parity(opcode) << 23);
    return 0;
}
int sweet_a618_cp_init(uint32_t *out, size_t capacity) {
    uint32_t header;
    if (!out || capacity < 9 || sweet_gpu_pkt7(0x48, 8, &header)) return -1;
    out[0]=header; out[1]=0x2f; out[2]=3; out[3]=0x20000000;
    out[4]=out[5]=out[6]=out[7]=out[8]=0;
    return 0;
}
