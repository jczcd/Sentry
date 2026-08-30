#!/usr/bin/env python3
"""Observe and validate real PHASE G ROS state feedback."""
import argparse, json, math, os, time, xml.etree.ElementTree as ET
from pathlib import Path

from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
import rclpy
from rclpy.node import Node
from rosgraph_msgs.msg import Clock
from sensor_msgs.msg import JointState
from tf2_msgs.msg import TFMessage

EXPECTED = {"steer_FL_joint","drive_FL_joint","steer_FR_joint","drive_FR_joint","steer_RL_joint","drive_RL_joint","steer_RR_joint","drive_RR_joint","yaw_big_joint","yaw_small_joint","pitch_joint"}

def yaw(q): return math.atan2(2*(q.w*q.z+q.x*q.y),1-2*(q.y*q.y+q.z*q.z))
def wrap(v): return (v+math.pi)%(2*math.pi)-math.pi
def stamp(m): return m.sec + m.nanosec/1e9

class Observer(Node):
    NAMES=("straight","lateral","rotate")
    def __init__(self,evidence,report,urdf=None):
        super().__init__("phase_g_state_observer"); self.evidence_path=evidence; self.report_path=report
        self.counts={"clock":0,"odom":0,"joint_states":0,"tf":0}; self.types={}; self.latest_odom=None; self.latest_tf=None; self.latest_joint=None; self.tf_edges={}; self.tf_initial={}; self.tf_max_rotation={}
        self.urdf_path=urdf; self.urdf_root=ET.parse(urdf).getroot() if urdf else None
        self.last_stamps={"clock":-1.0,"odom":-1.0,"joint_states":-1.0,"tf":-1.0}; self.timestamps_valid=True; self.finite=True
        self.initial=None; self.stationary=None; self.active=None; self.pending_since=None; self.tests=[]; self.command_events=[]; self.drive_nonzero=False; self.steer_changed=False
        self.create_subscription(Clock,"/clock",self.on_clock,100); self.create_subscription(Odometry,"/sentry/odom",self.on_odom,100)
        self.create_subscription(JointState,"/joint_states",self.on_joint,100); self.create_subscription(TFMessage,"/tf",self.on_tf,100)
        self.create_subscription(Twist,"/cmd_vel",self.on_cmd,50); self.create_timer(.1,self.tick)
    def check_stamp(self,key,value):
        if value<=0 or value+1e-9<self.last_stamps[key]: self.timestamps_valid=False
        self.last_stamps[key]=value
    def on_clock(self,m): self.counts["clock"]+=1; self.check_stamp("clock",stamp(m.clock))
    def on_odom(self,m):
        self.counts["odom"]+=1; self.check_stamp("odom",stamp(m.header.stamp)); self.latest_odom=m
        vals=[m.pose.pose.position.x,m.pose.pose.position.y,m.pose.pose.position.z,m.pose.pose.orientation.x,m.pose.pose.orientation.y,m.pose.pose.orientation.z,m.pose.pose.orientation.w,m.twist.twist.linear.x,m.twist.twist.linear.y,m.twist.twist.angular.z]
        self.finite &= all(math.isfinite(v) for v in vals)
        if self.initial is None: self.initial=self.pose(m)
    def on_joint(self,m):
        self.counts["joint_states"]+=1; self.check_stamp("joint_states",stamp(m.header.stamp)); self.latest_joint=m
        self.finite &= len(m.name)==len(m.position)==len(m.velocity) and len(set(m.name))==len(m.name) and all(math.isfinite(v) for v in list(m.position)+list(m.velocity))
        d=dict(zip(m.name,m.velocity)); p=dict(zip(m.name,m.position)); self.drive_nonzero |= any(abs(d.get(n,0))>.15 for n in EXPECTED if n.startswith("drive_")); self.steer_changed |= any(abs(p.get(n,0))>.05 for n in EXPECTED if n.startswith("steer_"))
    def on_tf(self,m):
        for t in m.transforms:
            key=(t.header.frame_id,t.child_frame_id); q=t.transform.rotation; current=(q.x,q.y,q.z,q.w); self.tf_edges[key]=current
            if key not in self.tf_initial:self.tf_initial[key]=current
            a=self.tf_initial[key]; dot=min(1.0,abs(sum(a[i]*current[i] for i in range(4)))); self.tf_max_rotation[key]=max(self.tf_max_rotation.get(key,0.0),2*math.acos(dot))
            if t.header.frame_id=="odom" and t.child_frame_id=="base_link":
                self.counts["tf"]+=1; self.check_stamp("tf",stamp(t.header.stamp)); self.latest_tf=t
    def on_cmd(self,m):
        nonzero=math.hypot(m.linear.x,m.linear.y)>1e-4 or abs(m.angular.z)>1e-4
        self.command_events.append({"monotonic":time.monotonic(),"vx":m.linear.x,"vy":m.linear.y,"wz":m.angular.z})
        if nonzero and self.active is None and len(self.tests)<3 and self.latest_odom:
            self.active={"name":self.NAMES[len(self.tests)],"command":{"vx":m.linear.x,"vy":m.linear.y,"wz":m.angular.z},"start":self.pose(self.latest_odom),"joint_start":dict(zip(self.latest_joint.name,self.latest_joint.position)) if self.latest_joint else {}}; self.pending_since=None
        elif not nonzero and self.active is not None and self.pending_since is None:
            self.pending_since=time.monotonic()
    @staticmethod
    def pose(m): return {"x":m.pose.pose.position.x,"y":m.pose.pose.position.y,"z":m.pose.pose.position.z,"yaw":yaw(m.pose.pose.orientation),"stamp":stamp(m.header.stamp)}
    def finish_case(self):
        e=self.pose(self.latest_odom); s=self.active["start"]; dx=e["x"]-s["x"]; dy=e["y"]-s["y"]; da=wrap(e["yaw"]-s["yaw"]); name=self.active["name"]
        passed=(dx>.04 and abs(dy)<=max(.025,dx*.65) and abs(math.degrees(da))<=20) if name=="straight" else ((dy>.04 and abs(dx)<=max(.025,dy*.65) and abs(math.degrees(da))<=20) if name=="lateral" else (da>math.radians(8) and math.hypot(dx,dy)<=.18))
        self.tests.append({**self.active,"end":e,"joint_end":dict(zip(self.latest_joint.name,self.latest_joint.position)) if self.latest_joint else {},"dx":dx,"dy":dy,"dYaw":math.degrees(da),"pass":bool(passed)}); self.active=None; self.pending_since=None
    def tick(self):
        if self.stationary is None and self.initial and self.latest_odom and self.counts["odom"]>25:
            p=self.pose(self.latest_odom); self.stationary={"pose":p,"pass":abs(p["x"])<.02 and abs(p["y"])<.02 and abs(math.degrees(p["yaw"]))<3}
        if self.pending_since and time.monotonic()-self.pending_since>1 and self.latest_odom: self.finish_case()
        self.write()
    def write(self):
        graph=dict(self.get_topic_names_and_types()); type_ok={"odom":graph.get("/sentry/odom")==["nav_msgs/msg/Odometry"],"joint_states":graph.get("/joint_states")==["sensor_msgs/msg/JointState"],"tf":graph.get("/tf")==["tf2_msgs/msg/TFMessage"]}
        terr=yerr=float("inf")
        if self.latest_odom and self.latest_tf:
            o=self.latest_odom.pose.pose; t=self.latest_tf.transform; terr=math.sqrt((o.position.x-t.translation.x)**2+(o.position.y-t.translation.y)**2+(o.position.z-t.translation.z)**2); yerr=abs(wrap(yaw(o.orientation)-yaw(t.rotation)))
        joint_ok=bool(self.latest_joint and set(self.latest_joint.name)==EXPECTED)
        complete=len(self.tests)==3
        passed=bool(complete and all(x["pass"] for x in self.tests) and self.stationary and self.stationary["pass"] and all(v>0 for v in self.counts.values()) and all(type_ok.values()) and joint_ok and self.finite and self.timestamps_valid and self.drive_nonzero and self.steer_changed and terr<.01 and yerr<math.radians(1))
        data={"counts":self.counts,"types":type_ok,"frames":{"odom":"odom","base":"base_link"},"joint_names":list(self.latest_joint.name) if self.latest_joint else [],"joint_count":len(self.latest_joint.name) if self.latest_joint else 0,"timestamps_valid":self.timestamps_valid,"all_values_finite":self.finite,"drive_velocity_nonzero":self.drive_nonzero,"steer_position_changed":self.steer_changed,"stationary":self.stationary,"tests":self.tests,"command_event_count":len(self.command_events),"command_events":self.command_events,"tf_edges":[{"parent":a,"child":b,"max_rotation_rad":self.tf_max_rotation.get((a,b),0)} for a,b in self.tf_edges],"tf_odom_consistency":{"translation_error_m":terr,"yaw_error_rad":yerr,"pass":terr<.01 and yerr<math.radians(1)},"runtime_validation_all_pass":passed}
        if self.urdf_root is not None:
            links=[x.attrib["name"] for x in self.urdf_root.findall("link")]; joints=[x.attrib["name"] for x in self.urdf_root.findall("joint") if x.attrib.get("type")!="fixed"]
            parents={}; duplicate=False
            for edge in data["tf_edges"]:
                if edge["child"] in parents and parents[edge["child"]]!=edge["parent"]:duplicate=True
                parents[edge["child"]]=edge["parent"]
            reachable={"odom"}; changed=True
            while changed:
                changed=False
                for child,parent in parents.items():
                    if parent in reachable and child not in reachable:reachable.add(child);changed=True
            cycle=False
            for start in parents:
                seen=set(); n=start
                while n in parents:
                    if n in seen:cycle=True;break
                    seen.add(n);n=parents[n]
            physical=["steer_FL","drive_FL","steer_FR","drive_FR","steer_RL","drive_RL","steer_RR","drive_RR","yaw_big","yaw_small","pitch"]
            motion=all(self.tf_max_rotation.get((parents.get(n,""),n),0)>.05 for n in ["steer_FL","steer_FR","steer_RL","steer_RR"])
            hpass=passed and len(joints)==11 and set(joints)==set(data["joint_names"]) and not duplicate and not cycle and all(n in reachable for n in ["base_link"]+physical) and parents.get("base_link")=="odom" and motion
            data.update(robot_description_valid=True,root_link="base_link",urdf_links=links,urdf_joints=joints,movable_joint_count=len(joints),joint_match_count=len(set(joints)&set(data["joint_names"])),tf_root="odom",tf_cycle_detected=cycle,duplicate_parent_detected=duplicate,reachable_links=sorted(reachable),missing_links=[n for n in physical if n not in reachable],base_footprint_conflict="base_footprint" in parents,joint_tf_motion_pass=motion,runtime_validation_all_pass=bool(hpass))
        for path in (self.evidence_path,self.report_path):
            path.parent.mkdir(parents=True,exist_ok=True); tmp=path.with_suffix(path.suffix+".tmp"); tmp.write_text(json.dumps(data,indent=2)+"\n"); os.replace(tmp,path)

def main():
    p=argparse.ArgumentParser(); p.add_argument("--evidence",type=Path,required=True); p.add_argument("--report",type=Path,required=True); p.add_argument("--urdf",type=Path); a=p.parse_args(); rclpy.init(); n=Observer(a.evidence.resolve(),a.report.resolve(),a.urdf.resolve() if a.urdf else None)
    try:rclpy.spin(n)
    except rclpy.executors.ExternalShutdownException: pass
    finally:
        if rclpy.ok(): n.write()
        n.destroy_node()
        if rclpy.ok(): rclpy.shutdown()
if __name__=="__main__":main()
