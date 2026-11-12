#include "sweet_hfi_ring.h"
#include <assert.h>
int main(void) {
    uint32_t ring[8] = {0}, msg[3] = {3u << 8 | 1u, 11, 22}, out[3];
    size_t r = 6, w = 6, n = 99;
    assert(!sweet_hfi_ring_write(ring, 8, r, &w, msg, 3) && w == 1);
    assert(!sweet_hfi_ring_read(ring, 8, &r, w, out, 3, &n));
    assert(r == 1 && n == 3 && out[0] == msg[0] && out[1] == 11 && out[2] == 22);
    assert(sweet_hfi_ring_read(ring, 8, &r, w, out, 3, &n) == 1);
    r = 2; w = 0;
    assert(sweet_hfi_ring_write(ring, 8, r, &w, msg, 3) == 1 && w == 0);
    r = 6; w = 0; ring[6] = msg[0]; ring[7] = 11;
    assert(sweet_hfi_ring_read(ring, 8, &r, w, out, 3, &n) == 1 && r == 6);
    ring[6] = 0;
    assert(sweet_hfi_ring_read(ring, 8, &r, w, out, 3, &n) == -1 && r == 6);
    ring[6] = msg[0]; w = 1;
    assert(sweet_hfi_ring_read(ring, 8, &r, w, out, 2, &n) == -1 && r == 6);
    assert(sweet_hfi_ring_write(ring, 8, 8, &w, msg, 3) == -1);
    return 0;
}
