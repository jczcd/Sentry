"""Little-endian, CRC-protected protocol shared by ROS 2 and STM32."""

from __future__ import annotations

from dataclasses import dataclass
import struct


MAGIC = 0x534E
VERSION = 1
TYPE_COMMAND = 1
TYPE_TELEMETRY = 2
MAX_PAYLOAD = 256

HEADER = struct.Struct("<HBBHHI")
COMMAND = struct.Struct("<hhhbBBB")
TELEMETRY = struct.Struct("<iiihhhHHHHI")
CRC = struct.Struct("<H")
MAGIC_BYTES = struct.pack("<H", MAGIC)


@dataclass(slots=True)
class Frame:
    message_type: int
    sequence: int
    timestamp_ms: int
    payload: bytes


@dataclass(slots=True)
class Telemetry:
    x_m: float
    y_m: float
    yaw_rad: float
    vx_m_s: float
    vy_m_s: float
    wz_rad_s: float
    heat_17: float
    heat_17_limit: float
    ammo_remaining: float
    battery_voltage: float
    fault_flags: int


def crc16_ccitt(data: bytes, initial: int = 0xFFFF) -> int:
    crc = initial & 0xFFFF
    for value in data:
        crc ^= value << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) & 0xFFFF if crc & 0x8000 else (crc << 1) & 0xFFFF
    return crc


def _clamp_int(value: float, low: int, high: int) -> int:
    return min(max(int(round(value)), low), high)


def encode_frame(
    message_type: int, sequence: int, timestamp_ms: int, payload: bytes
) -> bytes:
    if len(payload) > MAX_PAYLOAD:
        raise ValueError("payload is too large")
    header = HEADER.pack(
        MAGIC,
        VERSION,
        int(message_type) & 0xFF,
        len(payload),
        int(sequence) & 0xFFFF,
        int(timestamp_ms) & 0xFFFFFFFF,
    )
    body = header + payload
    return body + CRC.pack(crc16_ccitt(body))


def encode_command(
    *,
    sequence: int,
    timestamp_ms: int,
    vx_m_s: float,
    vy_m_s: float,
    wz_rad_s: float,
    target_slot: int,
    weapons_free: bool,
    estop: bool,
) -> bytes:
    payload = COMMAND.pack(
        _clamp_int(vx_m_s * 1000.0, -32768, 32767),
        _clamp_int(vy_m_s * 1000.0, -32768, 32767),
        _clamp_int(wz_rad_s * 1000.0, -32768, 32767),
        _clamp_int(target_slot, -1, 127),
        int(bool(weapons_free)),
        int(bool(estop)),
        0,
    )
    return encode_frame(TYPE_COMMAND, sequence, timestamp_ms, payload)


def encode_telemetry(
    *,
    sequence: int,
    timestamp_ms: int,
    x_m: float,
    y_m: float,
    yaw_rad: float,
    vx_m_s: float,
    vy_m_s: float,
    wz_rad_s: float,
    heat_17: float,
    heat_17_limit: float,
    ammo_remaining: float,
    battery_voltage: float,
    fault_flags: int,
) -> bytes:
    payload = TELEMETRY.pack(
        _clamp_int(x_m * 1000.0, -(2**31), 2**31 - 1),
        _clamp_int(y_m * 1000.0, -(2**31), 2**31 - 1),
        _clamp_int(yaw_rad * 1000.0, -(2**31), 2**31 - 1),
        _clamp_int(vx_m_s * 1000.0, -32768, 32767),
        _clamp_int(vy_m_s * 1000.0, -32768, 32767),
        _clamp_int(wz_rad_s * 1000.0, -32768, 32767),
        _clamp_int(heat_17, 0, 65535),
        _clamp_int(heat_17_limit, 0, 65535),
        _clamp_int(ammo_remaining, 0, 65535),
        _clamp_int(battery_voltage * 1000.0, 0, 65535),
        int(fault_flags) & 0xFFFFFFFF,
    )
    return encode_frame(TYPE_TELEMETRY, sequence, timestamp_ms, payload)


def decode_telemetry(frame: Frame) -> Telemetry:
    if frame.message_type != TYPE_TELEMETRY or len(frame.payload) != TELEMETRY.size:
        raise ValueError("not a telemetry frame")
    (
        x_mm,
        y_mm,
        yaw_mrad,
        vx_mm_s,
        vy_mm_s,
        wz_mrad_s,
        heat,
        heat_limit,
        ammo,
        battery_mv,
        faults,
    ) = TELEMETRY.unpack(frame.payload)
    return Telemetry(
        x_m=x_mm / 1000.0,
        y_m=y_mm / 1000.0,
        yaw_rad=yaw_mrad / 1000.0,
        vx_m_s=vx_mm_s / 1000.0,
        vy_m_s=vy_mm_s / 1000.0,
        wz_rad_s=wz_mrad_s / 1000.0,
        heat_17=float(heat),
        heat_17_limit=float(heat_limit),
        ammo_remaining=float(ammo),
        battery_voltage=battery_mv / 1000.0,
        fault_flags=int(faults),
    )


class FrameParser:
    def __init__(self) -> None:
        self._buffer = bytearray()

    def feed(self, data: bytes) -> list[Frame]:
        self._buffer.extend(data)
        frames: list[Frame] = []
        while True:
            index = self._buffer.find(MAGIC_BYTES)
            if index < 0:
                if self._buffer[-1:] != MAGIC_BYTES[:1]:
                    self._buffer.clear()
                elif len(self._buffer) > 1:
                    del self._buffer[:-1]
                break
            if index:
                del self._buffer[:index]
            if len(self._buffer) < HEADER.size:
                break
            magic, version, kind, size, sequence, timestamp = HEADER.unpack_from(
                self._buffer
            )
            if magic != MAGIC or version != VERSION or size > MAX_PAYLOAD:
                del self._buffer[0]
                continue
            total = HEADER.size + size + CRC.size
            if len(self._buffer) < total:
                break
            body = bytes(self._buffer[: HEADER.size + size])
            expected_crc = CRC.unpack_from(self._buffer, HEADER.size + size)[0]
            if crc16_ccitt(body) != expected_crc:
                del self._buffer[0]
                continue
            frames.append(
                Frame(
                    message_type=kind,
                    sequence=sequence,
                    timestamp_ms=timestamp,
                    payload=body[HEADER.size:],
                )
            )
            del self._buffer[:total]
        return frames
