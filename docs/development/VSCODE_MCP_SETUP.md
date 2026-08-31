# VS Code and ROS MCP setup

The repository includes `.vscode/mcp.json`, pinned to `ros-mcp==3.1.0` over stdio.

## Topology

```text
VS Code Agent
  -> local stdio ROS-MCP process
  -> rosbridge WebSocket
  -> ROS 2 graph
  -> diagnostic topics and gated /cmd_vel path
```

ROS-MCP does not replace ROS nodes. It exposes ROS topics, services, actions, and parameters to the agent through rosbridge.

## 1. Prepare the ROS machine

Install and launch rosbridge using the actual ROS distribution:

```bash
sudo apt update
sudo apt install "ros-${ROS_DISTRO}-rosbridge-server"
source /path/to/ros2_ws/install/setup.bash
ros2 launch rosbridge_server rosbridge_websocket_launch.xml
```

Keep port 9090 on loopback, a trusted robot LAN, VPN, or SSH tunnel. Do not expose an unauthenticated rosbridge endpoint to the public internet.

For an SSH tunnel from the development machine:

```bash
ssh -L 9090:127.0.0.1:9090 user@robot-host
```

The MCP connection target is then `ws://127.0.0.1:9090`.

## 2. Prepare VS Code

1. Install a current VS Code and GitHub Copilot Chat with Agent mode enabled.
2. Install `uv`/`uvx` from the official Astral instructions if it is not already available.
3. Open `Sentinel.code-workspace`.
4. Review `.vscode/mcp.json` before trusting it.
5. Run `MCP: List Servers` from the Command Palette and start `rosMcp`.
6. Choose **Show Output** if startup fails.

The checked-in configuration is:

```json
{
  "servers": {
    "rosMcp": {
      "type": "stdio",
      "command": "uvx",
      "args": ["--from", "ros-mcp==3.1.0", "ros-mcp", "--transport=stdio"],
      "cwd": "${workspaceFolder}"
    }
  }
}
```

VS Code supports workspace `.vscode/mcp.json` and user-profile configuration. When working through VS Code Remote SSH, define the server in the workspace or remote user configuration if it must run on the remote host.

## 3. First connection

Start with discovery and read-only checks:

```text
Connect to ws://127.0.0.1:9090. List ROS 2 topics, services and actions.
Read /sentry/odom, /joint_states and /sentry/estop. Do not publish anything.
```

Confirm the following manually:

```bash
ros2 topic list
ros2 topic info --verbose /cmd_vel
ros2 topic info --verbose /sentry/cmd_vel_safe
ros2 topic echo --once /sentry/estop
```

## 4. Motion authorization

MCP motion is disabled by policy until all of these are true:

- the robot is in a controlled test area or simulation;
- a human has explicitly authorized motion for the current test;
- estop behavior has been tested;
- `safety_supervisor` is active;
- MCP publishes only to `/cmd_vel`;
- a short command timeout is active;
- a human can remove power or assert estop.

Never ask MCP to publish directly to `/sentry/cmd_vel_safe`, joint commands, motor currents, PWM, or raw CAN.

## 5. Troubleshooting

| Symptom | Check |
|---|---|
| server missing | `MCP: List Servers`, workspace trust, `.vscode/mcp.json`, and a full VS Code restart |
| `uvx` not found | terminal PATH and VS Code extension-host environment |
| cannot connect | rosbridge process, port/tunnel, firewall, and exact WebSocket URL |
| topics visible but no data | ROS domain, topic QoS, namespace, and publisher state |
| tools stale after upgrade | `MCP: Reset Cached Tools` and restart the server |
| remote workspace starts server locally | use remote workspace/user MCP configuration |

References:

- https://code.visualstudio.com/docs/agent-customization/mcp-servers
- https://code.visualstudio.com/docs/agents/reference/mcp-configuration
- https://github.com/robotmcp/ros-mcp-server
