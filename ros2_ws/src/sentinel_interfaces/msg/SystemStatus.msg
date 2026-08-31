uint8 MODE_SIM=0
uint8 MODE_HIL=1
uint8 MODE_REAL=2

std_msgs/Header header
uint8 mode
bool estop
bool hardware_online
bool policy_online
bool command_fresh
string active_motion_source
string detail
