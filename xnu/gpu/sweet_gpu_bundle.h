#ifndef SWEET_GPU_BUNDLE_H
#define SWEET_GPU_BUNDLE_H
#include <stddef.h>
#include <stdint.h>
#define SWEET_GPU_BUNDLE_FILES 4
struct sweet_gpu_blob { const uint8_t *data; size_t size; const uint8_t *sha256; };
/* Caller must verify hashes, signatures, source and memory lifetime. */
int sweet_gpu_bundle_parse(const void *buffer, size_t size, struct sweet_gpu_blob out[SWEET_GPU_BUNDLE_FILES]);
#endif
