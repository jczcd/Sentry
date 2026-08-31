uint8 TYPE_HERO=1
uint8 TYPE_ENGINEER=2
uint8 TYPE_INFANTRY3=3
uint8 TYPE_INFANTRY4=4
uint8 TYPE_AERIAL=5
uint8 TYPE_SENTRY=6
uint8 TYPE_BASE=7
uint8 TYPE_OUTPOST=8

uint8 TEAM_RED=0
uint8 TEAM_BLUE=1

uint8 robot_type
uint8 team
bool present
bool alive
bool visible
bool vulnerable
geometry_msgs/Point position
float32 turret_yaw_rad
float32 hp
float32 max_hp
float32 chassis_power_w
float32 heat_17
float32 heat_17_limit
float32 heat_42_limit
float32 ammo_17_fired
