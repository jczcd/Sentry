#include "sentinel_wire_protocol.h"

#include <stdio.h>

int main(void) {
    const sentinel_command_t command = {
        .vx_mm_s = 1250,
        .vy_mm_s = -500,
        .wz_mrad_s = 0,
        .target_slot = 5,
        .weapons_free = true,
        .estop = false,
    };
    uint8_t frame[SENTINEL_MAX_FRAME_SIZE];
    size_t index;
    size_t size = sentinel_encode_command(
        &command,
        UINT16_C(513),
        UINT32_C(123456789),
        frame,
        sizeof(frame)
    );
    if (size == 0U) {
        return 1;
    }
    for (index = 0U; index < size; ++index) {
        printf("%02x", frame[index]);
    }
    putchar('\n');
    return 0;
}
