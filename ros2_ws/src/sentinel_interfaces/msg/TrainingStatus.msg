uint8 STATE_IDLE=0
uint8 STATE_STARTING=1
uint8 STATE_RUNNING=2
uint8 STATE_STOPPING=3
uint8 STATE_SUCCEEDED=4
uint8 STATE_FAILED=5

std_msgs/Header header
uint8 state
int32 pid
int32 exit_code
string run_name
string config_path
string detail
