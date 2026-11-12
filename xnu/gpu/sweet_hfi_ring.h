#ifndef SWEET_HFI_RING_H
#define SWEET_HFI_RING_H
#include <stddef.h>
#include <stdint.h>
/* Offline legacy HFI ring: caller owns synchronization, cache and barriers.
 * The API does not touch a hardware queue or signal the GMU. */
int sweet_hfi_ring_write(uint32_t *ring, size_t size, size_t read_index,
    size_t *write_index, const uint32_t *message, size_t words);
/* 0 success, 1 empty or incomplete, -1 invalid or output too small. */
int sweet_hfi_ring_read(const uint32_t *ring, size_t size, size_t *read_index,
    size_t write_index, uint32_t *output, size_t capacity, size_t *words);
#endif
