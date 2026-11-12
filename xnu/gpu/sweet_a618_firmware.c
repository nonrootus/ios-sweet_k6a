/* A618 legacy GMU and a630 SQE firmware validation, with no hardware access.
 * Linux reference: adreno_gpu.c adreno_fw_create_bo and
 * a6xx_gpu.c a6xx_ucode_check_version; a6xx_gmu.c legacy loader.
 */
#include "sweet_a618_firmware.h"

static uint32_t
le32(const uint8_t *p)
{
    return (uint32_t)p[0] | (uint32_t)p[1] << 8 |
        (uint32_t)p[2] << 16 | (uint32_t)p[3] << 24;
}

int
sweet_a618_firmware_prepare(const void *gmu, size_t gmu_size,
    const void *sqe, size_t sqe_size, struct sweet_a618_firmware_view *out)
{
    const uint8_t *payload;
    uint32_t v, p;
    if (!gmu || !sqe || !out) return SWEET_A618_FW_BAD_ARGUMENT;
    if (!gmu_size || gmu_size > 0x8000 || (gmu_size & 3))
        return SWEET_A618_FW_BAD_GMU_SIZE;
    if (sqe_size < 16 || (sqe_size & 3)) return SWEET_A618_FW_BAD_SQE_SIZE;
    payload = (const uint8_t *)sqe + 4; /* first word is not loaded */
    v = le32(payload);
    p = le32(payload + 8);
    if (!(((v & 0xf) == 0xa && (p & 0xf) >= 1) || (v & 0xfff) >= 0x190))
        return SWEET_A618_FW_OLD_SQE;
    out->gmu = gmu;
    out->gmu_size = gmu_size;
    out->sqe_payload = payload;
    out->sqe_payload_size = sqe_size - 4;
    out->sqe_version_word = v;
    out->sqe_patch_word = p;
    return SWEET_A618_FW_OK;
}
