#include "sweet_hfi_ring.h"
/* Keep one unused word to distinguish full from empty. Legacy HFI v1 has
 * no four-word padding. Never publish indexes to a live device from here. */
int sweet_hfi_ring_write(uint32_t *ring, size_t size, size_t read_index,
    size_t *write_index, const uint32_t *message, size_t words) {
    size_t used, index, i;
    if (!ring || !write_index || !message || size < 2 || read_index >= size ||
        *write_index >= size || !words || words > 255 || words >= size ||
        ((message[0] >> 8) & 255u) != words) return -1;
    index = *write_index;
    used = index >= read_index ? index - read_index : size - read_index + index;
    if (words > size - used - 1) return 1;
    for (i = 0; i < words; ++i) {
        ring[index] = message[i];
        if (++index == size) index = 0;
    }
    *write_index = index;
    return 0;
}
int sweet_hfi_ring_read(const uint32_t *ring, size_t size, size_t *read_index,
    size_t write_index, uint32_t *output, size_t capacity, size_t *words) {
    size_t available, count, index, i;
    if (!ring || !read_index || !output || !words || size < 2 ||
        *read_index >= size || write_index >= size) return -1;
    index = *read_index;
    available = write_index >= index ? write_index - index : size - index + write_index;
    if (!available) return 1;
    count = (ring[index] >> 8) & 255u;
    if (!count || count >= size || count > capacity) return -1;
    if (count > available) return 1;
    for (i = 0; i < count; ++i) {
        output[i] = ring[index];
        if (++index == size) index = 0;
    }
    *read_index = index;
    *words = count;
    return 0;
}
