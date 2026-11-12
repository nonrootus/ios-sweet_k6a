#ifndef SWEET_GPU_PM4_H
#define SWEET_GPU_PM4_H
#include <stddef.h>
#include <stdint.h>
/* Offline PM4 packet construction; caller owns and synchronizes output. */
int sweet_gpu_pkt7(uint8_t opcode, uint16_t words, uint32_t *out);
int sweet_a618_cp_init(uint32_t *out, size_t capacity);
#endif
