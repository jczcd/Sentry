#ifndef SENTINEL_WIRE_PROTOCOL_H
#define SENTINEL_WIRE_PROTOCOL_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define SENTINEL_MAGIC UINT16_C(0x534E)
#define SENTINEL_PROTOCOL_VERSION UINT8_C(1)
#define SENTINEL_TYPE_COMMAND UINT8_C(1)
#define SENTINEL_TYPE_TELEMETRY UINT8_C(2)
#define SENTINEL_MAX_PAYLOAD 256U
#define SENTINEL_HEADER_SIZE 12U
#define SENTINEL_CRC_SIZE 2U
#define SENTINEL_MAX_FRAME_SIZE \
    (SENTINEL_HEADER_SIZE + SENTINEL_MAX_PAYLOAD + SENTINEL_CRC_SIZE)

typedef struct {
    int16_t vx_mm_s;
    int16_t vy_mm_s;
    int16_t wz_mrad_s;
    int8_t target_slot;
    bool weapons_free;
    bool estop;
} sentinel_command_t;

typedef struct {
    int32_t x_mm;
    int32_t y_mm;
    int32_t yaw_mrad;
    int16_t vx_mm_s;
    int16_t vy_mm_s;
    int16_t wz_mrad_s;
    uint16_t heat_17;
    uint16_t heat_17_limit;
    uint16_t ammo_remaining;
    uint16_t battery_mv;
    uint32_t fault_flags;
} sentinel_telemetry_t;

typedef struct {
    uint8_t message_type;
    uint16_t sequence;
    uint32_t timestamp_ms;
    uint16_t payload_size;
    uint8_t payload[SENTINEL_MAX_PAYLOAD];
} sentinel_frame_t;

typedef struct {
    uint8_t buffer[SENTINEL_MAX_FRAME_SIZE];
    size_t length;
} sentinel_parser_t;

uint16_t sentinel_crc16_ccitt(
    const uint8_t *data,
    size_t length,
    uint16_t initial
);

size_t sentinel_encode_frame(
    uint8_t message_type,
    uint16_t sequence,
    uint32_t timestamp_ms,
    const uint8_t *payload,
    uint16_t payload_size,
    uint8_t *output,
    size_t capacity
);

size_t sentinel_encode_command(
    const sentinel_command_t *command,
    uint16_t sequence,
    uint32_t timestamp_ms,
    uint8_t *output,
    size_t capacity
);

size_t sentinel_encode_telemetry(
    const sentinel_telemetry_t *telemetry,
    uint16_t sequence,
    uint32_t timestamp_ms,
    uint8_t *output,
    size_t capacity
);

bool sentinel_decode_command(
    const sentinel_frame_t *frame,
    sentinel_command_t *command
);

bool sentinel_decode_telemetry(
    const sentinel_frame_t *frame,
    sentinel_telemetry_t *telemetry
);

void sentinel_parser_init(sentinel_parser_t *parser);

/*
 * Push one byte. Returns true exactly when a complete, CRC-valid frame is
 * written to ``frame``. Calling this for every USB CDC/UART/UDP byte handles
 * partial reads, concatenated frames and noise before the magic bytes.
 */
bool sentinel_parser_push(
    sentinel_parser_t *parser,
    uint8_t byte,
    sentinel_frame_t *frame
);

#ifdef __cplusplus
}
#endif

#endif
