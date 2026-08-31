#!/usr/bin/env python3
"""Generate the semantic Stage5D URDF and an auditable USD-to-URDF mapping."""
import json, math
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
SIM=Path("/home/xkddyl/RoboMaster/Sentinel/sentinelusd/Sentry_IsaacSim_Linux")
stage4=json.loads((SIM/"output/stage4_report.json").read_text())
build=json.loads((SIM/"output/stage5d_build_report.json").read_text())
sensor_config=json.loads((ROOT/"isaac_sim/config/phase_i_sensors.json").read_text())
mpu=float(build["meters_per_unit"])

def rpy(q):
    w,x,y,z=map(float,q)
    roll=math.atan2(2*(w*x+y*z),1-2*(x*x+y*y))
    s=2*(w*y-z*x); pitch=math.copysign(math.pi/2,s) if abs(s)>=1 else math.asin(s)
    yaw=math.atan2(2*(w*z+x*y),1-2*(y*y+z*z))
    return [roll,pitch,yaw]

records=[]
for j in stage4["joint_records"]:
    xyz=[float(v)*mpu for v in j["localPos0"]]; angles=rpy(j["localRot0_wxyz"])
    axis={"X":[1,0,0],"Y":[0,1,0],"Z":[0,0,1]}[j["axis"]]
    records.append({"joint":j["joint"],"parent":j["parent"],"child":j["child"],"usd_path":j["path"],"body0":j["parent_path"],"body1":j["child_path"],"meters_per_unit":mpu,"usd_localPos0":j["localPos0"],"usd_localRot0_wxyz":j["localRot0_wxyz"],"usd_localPos1":[0,0,0],"usd_localRot1_wxyz":[1,0,0,0],"urdf_origin_xyz_m":xyz,"urdf_origin_rpy_rad":angles,"urdf_axis_xyz":axis,"type":"continuous","limits_note":"physical limits not calibrated"})

def fmt(v): return " ".join(f"{x:.12g}" for x in v)
lines=['<?xml version="1.0"?>','<robot xmlns:xacro="http://www.ros.org/wiki/xacro" name="sentinel_stage5d">','  <!-- Generated from the validated Stage4 joint frames; semantic/RViz model only. -->','  <!-- Isaac Stage5D USD remains the sole physics and collision truth. -->','  <!-- All joints are continuous until physical limits are calibrated. -->','  <link name="base_link"><visual><geometry><box size="0.42 0.42 0.20"/></geometry></visual></link>']
for link in [r["child"] for r in records]:
    shape='<cylinder radius="0.052" length="0.056"/>' if link.startswith('drive_') else '<box size="0.06 0.06 0.06"/>'
    lines.append(f'  <link name="{link}"><visual><geometry>{shape}</geometry></visual></link>')
lines += ['  <!-- base_link -> lidar_link is a diagnostic placeholder; NOT HARDWARE CALIBRATED.',
          '       lidar_link -> imu_link is Mid-360 hardware internal geometry. -->',
          '  <link name="lidar_link"/>','  <link name="imu_link"/>']
for r in records:
    lines += [f'  <joint name="{r["joint"]}" type="continuous">',f'    <parent link="{r["parent"]}"/>',f'    <child link="{r["child"]}"/>',f'    <origin xyz="{fmt(r["urdf_origin_xyz_m"])}" rpy="{fmt(r["urdf_origin_rpy_rad"])}"/>',f'    <axis xyz="{fmt(r["urdf_axis_xyz"])}"/>','  </joint>']
cfg=sensor_config["lidar"]
lines += ['  <joint name="lidar_joint" type="fixed">','    <parent link="base_link"/>','    <child link="lidar_link"/>',f'    <origin xyz="{fmt(cfg["pose_xyz_m"])}" rpy="{fmt(cfg["pose_rpy_rad"])}"/>','  </joint>']
internal=sensor_config["mid360_internal_extrinsic"]
lines += ['  <joint name="imu_joint" type="fixed">','    <parent link="lidar_link"/>','    <child link="imu_link"/>',f'    <origin xyz="{fmt(internal["translation_m"])}" rpy="{fmt(internal["rotation_rpy_rad"])}"/>','  </joint>']
lines.append('</robot>')
(ROOT/"ros2_ws/src/sentinel_description/urdf/sentinel.urdf.xacro").write_text("\n".join(lines)+"\n")
out=ROOT/"isaac_sim/output/phase_h_usd_to_urdf_mapping.json";out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps({"source":str(SIM/"output/stage4_report.json"),"meters_per_unit":mpu,"root_link":"base_link","joint_count":len(records),"USD_TO_URDF_JOINT_MAPPING":records},indent=2)+"\n")
