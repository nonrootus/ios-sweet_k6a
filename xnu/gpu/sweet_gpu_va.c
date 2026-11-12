#include "sweet_gpu_va.h"
#include <stdint.h>

static int
rounded(uint64_t n, uint64_t *out)
{
    const uint64_t mask = SWEET_GPU_VA_ALIGN - 1;
    if (!n || n > UINT64_MAX - mask) return -1;
    *out = (n + mask) & ~mask;
    return 0;
}

int
sweet_gpu_va_init(struct sweet_gpu_va *v, uint64_t begin, uint64_t end)
{
    if (!v || !begin || begin >= end || (begin & (SWEET_GPU_VA_ALIGN-1)) ||
        (end & (SWEET_GPU_VA_ALIGN-1))) return -1;
    v->begin = begin; v->end = end; v->count = 0;
    return 0;
}

int
sweet_gpu_va_alloc(struct sweet_gpu_va *v, uint64_t size, uint64_t *address)
{
    uint64_t n, cursor;
    size_t at, i;
    if (!v || !address || rounded(size, &n) || v->count >= SWEET_GPU_VA_CAPACITY)
        return -1;
    cursor = v->begin;
    for (at = 0; at < v->count; at++) {
        if (cursor <= v->used[at].start && n <= v->used[at].start - cursor) break;
        cursor = v->used[at].start + v->used[at].size;
    }
    if (cursor > v->end || n > v->end - cursor) return -1;
    for (i = v->count; i > at; i--) v->used[i] = v->used[i-1];
    v->used[at].start = cursor; v->used[at].size = n; v->count++;
    *address = cursor;
    return 0;
}

int
sweet_gpu_va_free(struct sweet_gpu_va *v, uint64_t address, uint64_t size)
{
    uint64_t n; size_t i;
    if (!v || rounded(size, &n)) return -1;
    for (i = 0; i < v->count; i++) {
        if (v->used[i].start == address && v->used[i].size == n) {
            for (; i + 1 < v->count; i++) v->used[i] = v->used[i+1];
            v->count--;
            return 0;
        }
    }
    return -1;
}
