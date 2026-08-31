"""Publish Point-LIO-compatible PointCloud2 directly from Isaac RTX GMO returns."""
from __future__ import annotations

import math


class Mid360SimAdapter:
    """Convert native GMO XYZ/intensity/timeOffsetNs without synthesizing points or time."""

    WRITER_NAME = "SentinelMid360GmoPointCloudWriter"

    def __init__(self, node, topic: str, frame: str, simulation_manager) -> None:
        from sensor_msgs.msg import PointCloud2, PointField
        from rclpy.qos import qos_profile_sensor_data

        self.PointCloud2 = PointCloud2
        self.PointField = PointField
        self.frame = frame
        self.simulation_manager = simulation_manager
        self.publisher = node.create_publisher(PointCloud2, topic, qos_profile_sensor_data)
        self.received = 0
        self.published = 0
        self.rejected = 0

    def attach(self, sensor) -> None:
        import omni.replicator.core as rep
        from isaacsim.sensors.experimental.rtx import parse_generic_model_output_data
        from omni.replicator.core import Writer, WriterRegistry

        sink = self

        class SentinelMid360GmoPointCloudWriter(Writer):
            def __init__(self) -> None:
                self.data_structure = "renderProduct"
                self.annotators = [rep.annotators.get("GenericModelOutput")]

            def write(self, data) -> None:
                for rp_data in data.get("renderProducts", {}).values():
                    raw = rp_data.get("GenericModelOutput")
                    if isinstance(raw, dict):
                        raw = raw.get("data")
                    if raw is None:
                        continue
                    gmo = parse_generic_model_output_data(raw)
                    if gmo.numElements > 0:
                        sink.publish_gmo(gmo)

        SentinelMid360GmoPointCloudWriter.__name__ = self.WRITER_NAME
        try:
            WriterRegistry.register(SentinelMid360GmoPointCloudWriter)
        except Exception:
            pass
        sensor.attach_writer(self.WRITER_NAME)

    @staticmethod
    def _stamp(seconds: float):
        from builtin_interfaces.msg import Time
        stamp = Time()
        stamp.sec = int(seconds)
        stamp.nanosec = int((seconds - stamp.sec) * 1_000_000_000)
        return stamp

    def publish_gmo(self, gmo) -> None:
        import numpy as np

        self.received += 1
        count = int(gmo.numElements)
        try:
            offsets = np.ctypeslib.as_array(gmo.timeOffsetNs, shape=(count,)).astype(np.uint64, copy=True)
            # Example_Rotary GMO stores spherical azimuth/elevation in degrees
            # and distance in metres. This is the exact conversion exercised by
            # the installed IsaacExtractRTXSensorPointCloud official test.
            azimuth = np.deg2rad(np.ctypeslib.as_array(gmo.x, shape=(count,)).copy())
            elevation = np.deg2rad(np.ctypeslib.as_array(gmo.y, shape=(count,)).copy())
            distance = np.ctypeslib.as_array(gmo.z, shape=(count,)).copy()
            radial = distance * np.cos(elevation)
            xs = radial * np.cos(azimuth)
            ys = radial * np.sin(azimuth)
            zs = distance * np.sin(elevation)
            scalar = getattr(gmo, "scalar", None)
            intensities = (
                np.ctypeslib.as_array(scalar, shape=(count,)).copy()
                if scalar is not None else np.zeros(count, dtype=np.float32)
            )
        except (AttributeError, IndexError, TypeError, ValueError):
            self.rejected += 1
            return
        mask = np.isfinite(xs) & np.isfinite(ys) & np.isfinite(zs) & np.isfinite(intensities)
        if not np.any(mask):
            self.rejected += 1
            return
        order = np.argsort(offsets[mask], kind="stable")
        offsets = offsets[mask][order]
        xs, ys, zs, intensities = (values[mask][order] for values in (xs, ys, zs, intensities))
        output = np.empty(
            len(offsets),
            dtype=np.dtype([("x", "<f4"), ("y", "<f4"), ("z", "<f4"), ("intensity", "<f4"), ("time", "<f4")]),
        )
        output["x"], output["y"], output["z"], output["intensity"] = xs, ys, zs, intensities
        output["time"] = (offsets - offsets[0]).astype(np.float64) * 1e-9
        msg = self.PointCloud2()
        sim_time = float(self.simulation_manager.get_simulation_time())
        if sim_time <= 0.0:
            self.rejected += 1
            return
        msg.header.stamp = self._stamp(sim_time)
        msg.header.frame_id = self.frame
        msg.height = 1
        msg.width = len(output)
        msg.fields = [
            self.PointField(name="x", offset=0, datatype=self.PointField.FLOAT32, count=1),
            self.PointField(name="y", offset=4, datatype=self.PointField.FLOAT32, count=1),
            self.PointField(name="z", offset=8, datatype=self.PointField.FLOAT32, count=1),
            self.PointField(name="intensity", offset=12, datatype=self.PointField.FLOAT32, count=1),
            self.PointField(name="time", offset=16, datatype=self.PointField.FLOAT32, count=1),
        ]
        msg.is_bigendian = False
        msg.point_step = 20
        msg.row_step = msg.point_step * msg.width
        msg.data = output.tobytes()
        msg.is_dense = True
        self.publisher.publish(msg)
        self.published += 1
