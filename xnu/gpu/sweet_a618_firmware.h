#ifndef SWEET_A618_FIRMWARE_H
#define SWEET_A618_FIRMWARE_H
#include <stddef.h>
#include <stdint.h>

/* No MMIO or allocations: these views remain valid while input buffers live. */
struct sweet_a618_firmware_view {
    const uint8_t *gmu;
    size_t gmu_size;
    const uint8_t *sqe_payload;
    size_t sqe_payload_size;
    uint32_t sqe_version_word;
    uint32_t sqe_patch_word;
};

enum sweet_a618_fw_result {
    SWEET_A618_FW_OK = 0,
    SWEET_A618_FW_BAD_ARGUMENT = -1,
    SWEET_A618_FW_BAD_GMU_SIZE = -2,
    SWEET_A618_FW_BAD_SQE_SIZE = -3,
    SWEET_A618_FW_OLD_SQE = -4
};

/* Checks format/version, not cryptographic authenticity or SoC compatibility. */
int sweet_a618_firmware_prepare(const void *gmu, size_t gmu_size,
    const void *sqe, size_t sqe_size, struct sweet_a618_firmware_view *out);
#endif
