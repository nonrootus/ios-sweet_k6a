#ifndef SWEET_GPU_VA_H
#define SWEET_GPU_VA_H
#include <stddef.h>
#include <stdint.h>
#define SWEET_GPU_VA_CAPACITY 256
#define SWEET_GPU_VA_ALIGN UINT64_C(65536)
struct sweet_gpu_va_extent { uint64_t start, size; };
/* Externally synchronize all operations. Addresses are reservations only. */
struct sweet_gpu_va {
    uint64_t begin, end;
    size_t count;
    struct sweet_gpu_va_extent used[SWEET_GPU_VA_CAPACITY];
};
int sweet_gpu_va_init(struct sweet_gpu_va *v, uint64_t begin, uint64_t end);
int sweet_gpu_va_alloc(struct sweet_gpu_va *v, uint64_t size, uint64_t *address);
int sweet_gpu_va_free(struct sweet_gpu_va *v, uint64_t address, uint64_t size);
#endif
