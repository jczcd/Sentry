#include "sentinel_wire_protocol.h"

#include <string.h>

#define COMMAND_PAYLOAD_SIZE 10U
#define TELEMETRY_PAYLOAD_SIZE 30U

static void put_u16(uint8_t *p, uint16_t value) {
    p[0] = (uint8_t)(value & 0xFFU);
    p[1] = (uint8_t)((value >> 8U) & 0xFFU);
}

static void put_u32(uint8_t *p, uint32_t value) {
    p[0] = (uint8_t)(value & 0xFFU);
    p[1] = (uint8_t)((value >> 8U) & 0xFFU);
    p[2] = (uint8_t)((value >> 16U) & 0xFFU);
    p[3] = (uint8_t)((value >> 24U) & 0xFFU);
}

static uint16_t get_u16(const uint8_t *p) {
    return (uint16_t)((uint16_t)p[0] | ((uint16_t)p[1] << 8U));
}

static uint32_t get_u32(const uint8_t *p) {
    return (uint32_t)p[0]
        | ((uint32_t)p[1] << 8U)
        | ((uint32_t)p[2] << 16U)
        | ((uint32_t)p[3] << 24U);
}

static void discard_first(sentinel_parser_t *parser) {
    if (parser->length > 1U) {
        memmove(parser->buffer, parser->buffer + 1U, parser->length - 1U);
    }
    if (parser->length > 0U) {
        parser->length--;
    }
}

uint16_t sentinel_crc16_ccitt(
    const uint8_t *data,
    size_t length,
    uint16_t initial
) {
    uint16_t crc = initial;
    size_t index;
    for (index = 0U; index < length; ++index) {
        unsigned bit;
        crc ^= (uint16_t)((uint16_t)data[index] << 8U);
        for (bit = 0U; bit < 8U; ++bit) {
            if ((crc & UINT16_C(0x8000)) != 0U) {
                crc = (uint16_t)((crc << 1U) ^ UINT16_C(0x1021));
            } else {
                crc = (uint16_t)(crc << 1U);
            }
        }
    }
    return crc;
}

size_t sentinel_encode_frame(
    uint8_t message_type,
    uint16_t sequence,
    uint32_t timestamp_ms,
    const uint8_t *payload,
    uint16_t payload_size,
    uint8_t *output,
    size_t capacity
) {
    uint16_t crc;
    size_t total = SENTINEL_HEADER_SIZE + (size_t)payload_size
        + SENTINEL_CRC_SIZE;
    if (output == NULL || payload_size > SENTINEL_MAX_PAYLOAD
        || capacity < total || (payload == NULL && payload_size != 0U)) {
        return 0U;
    }
    put_u16(output, SENTINEL_MAGIC);
    output[2] = SENTINEL_PROTOCOL_VERSION;
    output[3] = message_type;
    put_u16(output + 4U, payload_size);
    put_u16(output + 6U, sequence);
    put_u32(output + 8U, timestamp_ms);
    if (payload_size != 0U) {
        memcpy(output + SENTINEL_HEADER_SIZE, payload, payload_size);
    }
    crc = sentinel_crc16_ccitt(
        output,
        SENTINEL_HEADER_SIZE + payload_size,
        UINT16_C(0xFFFF)
    );
    put_u16(output + SENTINEL_HEADER_SIZE + payload_size, crc);
    return total;
}

size_t sentinel_encode_command(
    const sentinel_command_t *command,
    uint16_t sequence,
    uint32_t timestamp_ms,
    uint8_t *output,
    size_t capacity
) {
    uint8_t payload[COMMAND_PAYLOAD_SIZE];
    if (command == NULL) {
        return 0U;
    }
    put_u16(payload, (uint16_t)command->vx_mm_s);
    put_u16(payload + 2U, (uint16_t)command->vy_mm_s);
    put_u16(payload + 4U, (uint16_t)command->wz_mrad_s);
    payload[6] = (uint8_t)command->target_slot;
    payload[7] = command->weapons_free ? 1U : 0U;
    payload[8] = command->estop ? 1U : 0U;
    payload[9] = 0U;
    return sentinel_encode_frame(
        SENTINEL_TYPE_COMMAND,
        sequence,
        timestamp_ms,
        payload,
        COMMAND_PAYLOAD_SIZE,
        output,
        capacity
    );
}

size_t sentinel_encode_telemetry(
    const sentinel_telemetry_t *telemetry,
    uint16_t sequence,
    uint32_t timestamp_ms,
    uint8_t *output,
    size_t capacity
) {
    uint8_t payload[TELEMETRY_PAYLOAD_SIZE];
    if (telemetry == NULL) {
        return 0U;
    }
    put_u32(payload, (uint32_t)telemetry->x_mm);
    put_u32(payload + 4U, (uint32_t)telemetry->y_mm);
    put_u32(payload + 8U, (uint32_t)telemetry->yaw_mrad);
    put_u16(payload + 12U, (uint16_t)telemetry->vx_mm_s);
    put_u16(payload + 14U, (uint16_t)telemetry->vy_mm_s);
    put_u16(payload + 16U, (uint16_t)telemetry->wz_mrad_s);
    put_u16(payload + 18U, telemetry->heat_17);
    put_u16(payload + 20U, telemetry->heat_17_limit);
    put_u16(payload + 22U, telemetry->ammo_remaining);
    put_u16(payload + 24U, telemetry->battery_mv);
    put_u32(payload + 26U, telemetry->fault_flags);
    return sentinel_encode_frame(
        SENTINEL_TYPE_TELEMETRY,
        sequence,
        timestamp_ms,
        payload,
        TELEMETRY_PAYLOAD_SIZE,
        output,
        capacity
    );
}

bool sentinel_decode_command(
    const sentinel_frame_t *frame,
    sentinel_command_t *command
) {
    const uint8_t *payload;
    if (frame == NULL || command == NULL
        || frame->message_type != SENTINEL_TYPE_COMMAND
        || frame->payload_size != COMMAND_PAYLOAD_SIZE) {
        return false;
    }
    payload = frame->payload;
    command->vx_mm_s = (int16_t)get_u16(payload);
    command->vy_mm_s = (int16_t)get_u16(payload + 2U);
    command->wz_mrad_s = (int16_t)get_u16(payload + 4U);
    command->target_slot = (int8_t)payload[6];
    command->weapons_free = payload[7] != 0U;
    command->estop = payload[8] != 0U;
    return true;
}

bool sentinel_decode_telemetry(
    const sentinel_frame_t *frame,
    sentinel_telemetry_t *telemetry
) {
    const uint8_t *payload;
    if (frame == NULL || telemetry == NULL
        || frame->message_type != SENTINEL_TYPE_TELEMETRY
        || frame->payload_size != TELEMETRY_PAYLOAD_SIZE) {
        return false;
    }
    payload = frame->payload;
    telemetry->x_mm = (int32_t)get_u32(payload);
    telemetry->y_mm = (int32_t)get_u32(payload + 4U);
    telemetry->yaw_mrad = (int32_t)get_u32(payload + 8U);
    telemetry->vx_mm_s = (int16_t)get_u16(payload + 12U);
    telemetry->vy_mm_s = (int16_t)get_u16(payload + 14U);
    telemetry->wz_mrad_s = (int16_t)get_u16(payload + 16U);
    telemetry->heat_17 = get_u16(payload + 18U);
    telemetry->heat_17_limit = get_u16(payload + 20U);
    telemetry->ammo_remaining = get_u16(payload + 22U);
    telemetry->battery_mv = get_u16(payload + 24U);
    telemetry->fault_flags = get_u32(payload + 26U);
    return true;
}

void sentinel_parser_init(sentinel_parser_t *parser) {
    if (parser != NULL) {
        parser->length = 0U;
    }
}

bool sentinel_parser_push(
    sentinel_parser_t *parser,
    uint8_t byte,
    sentinel_frame_t *frame
) {
    uint16_t payload_size;
    size_t total;
    uint16_t expected_crc;
    uint16_t actual_crc;
    if (parser == NULL || frame == NULL) {
        return false;
    }
    if (parser->length == SENTINEL_MAX_FRAME_SIZE) {
        discard_first(parser);
    }
    parser->buffer[parser->length++] = byte;

    while (parser->length >= 2U
        && get_u16(parser->buffer) != SENTINEL_MAGIC) {
        discard_first(parser);
    }
    if (parser->length < SENTINEL_HEADER_SIZE) {
        return false;
    }
    payload_size = get_u16(parser->buffer + 4U);
    if (parser->buffer[2] != SENTINEL_PROTOCOL_VERSION
        || payload_size > SENTINEL_MAX_PAYLOAD) {
        discard_first(parser);
        return false;
    }
    total = SENTINEL_HEADER_SIZE + (size_t)payload_size + SENTINEL_CRC_SIZE;
    if (parser->length < total) {
        return false;
    }
    expected_crc = get_u16(
        parser->buffer + SENTINEL_HEADER_SIZE + payload_size
    );
    actual_crc = sentinel_crc16_ccitt(
        parser->buffer,
        SENTINEL_HEADER_SIZE + payload_size,
        UINT16_C(0xFFFF)
    );
    if (expected_crc != actual_crc) {
        discard_first(parser);
        return false;
    }
    frame->message_type = parser->buffer[3];
    frame->payload_size = payload_size;
    frame->sequence = get_u16(parser->buffer + 6U);
    frame->timestamp_ms = get_u32(parser->buffer + 8U);
    if (payload_size != 0U) {
        memcpy(
            frame->payload,
            parser->buffer + SENTINEL_HEADER_SIZE,
            payload_size
        );
    }
    if (parser->length > total) {
        memmove(parser->buffer, parser->buffer + total, parser->length - total);
    }
    parser->length -= total;
    return true;
}
