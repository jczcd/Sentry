#!/usr/bin/env bash
set -euo pipefail

if [[ ! -r /etc/os-release ]]; then
  echo "Cannot identify this operating system." >&2
  exit 1
fi

source /etc/os-release
if [[ "${ID:-}" != "ubuntu" || "${VERSION_ID:-}" != "24.04" ]]; then
  echo "This bootstrap targets Ubuntu 24.04; found ${PRETTY_NAME:-unknown}." >&2
  exit 2
fi

sudo apt-get update
sudo apt-get install -y curl software-properties-common
sudo add-apt-repository -y universe

ros_source_version="$(
  curl -fsSL https://api.github.com/repos/ros-infrastructure/ros-apt-source/releases/latest \
    | python3 -c 'import json,sys; print(json.load(sys.stdin)["tag_name"])'
)"
ros_source_deb="/tmp/ros2-apt-source.deb"
curl -fsSL -o "${ros_source_deb}" \
  "https://github.com/ros-infrastructure/ros-apt-source/releases/download/${ros_source_version}/ros2-apt-source_${ros_source_version}.$(. /etc/os-release && echo "${UBUNTU_CODENAME}")_all.deb"
sudo dpkg -i "${ros_source_deb}"

sudo apt-get update
sudo apt-get install -y \
  build-essential \
  cmake \
  python3-colcon-common-extensions \
  python3-numpy \
  python3-pytest \
  python3-rosdep \
  python3-serial \
  python3-setuptools \
  python3-yaml \
  ros-dev-tools \
  ros-jazzy-desktop \
  ros-jazzy-navigation2 \
  ros-jazzy-nav2-bringup \
  ros-jazzy-nav2-mppi-controller \
  ros-jazzy-rmw-fastrtps-cpp \
  ros-jazzy-robot-state-publisher \
  ros-jazzy-xacro \
  unzip

if [[ ! -f /etc/ros/rosdep/sources.list.d/20-default.list ]]; then
  sudo rosdep init
fi
rosdep update
sudo usermod -aG dialout "${USER}"

echo "ROS 2 Jazzy dependencies installed."
echo "Log out and back in once for the dialout group change to take effect."
