#!/usr/bin/env bash
set -e

# Automatically detect the directory containing this script (project root in VS Code)
WS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "🚀 [1/6] Adding the official ROS 2 Jazzy repository..."
sudo apt update
sudo apt install -y curl gnupg lsb-release
sudo curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key -o /usr/share/keyrings/ros-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] http://packages.ros.org/ros2/ubuntu $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/ros2.list > /dev/null

echo "📦 [2/6] Installing ros-jazzy-desktop, colcon and Gazebo..."
sudo apt update
sudo apt install -y \
  ros-jazzy-desktop \
  python3-colcon-common-extensions \
  ros-jazzy-ros-gz \
  ros-jazzy-ros-gz-sim \
  ros-jazzy-ros-gz-bridge

echo "⚙️ [3/6] Adding ROS 2 auto-sourcing to ~/.bashrc..."
if ! grep -qF "source /opt/ros/jazzy/setup.bash" ~/.bashrc; then
    echo "source /opt/ros/jazzy/setup.bash" >> ~/.bashrc
fi
# Activate the system ROS 2 environment for the current script
source /opt/ros/jazzy/setup.bash

echo "🖥️ [4/6] Configuring Fluxbox (auto-maximize RViz and Gazebo windows)..."
mkdir -p ~/.fluxbox
cat << 'EOF' > ~/.fluxbox/apps
[app] (name=rviz2)
  [Maximized] {yes}
[end]

[app] (name=.*gz.*)
  [Maximized] {yes}
[end]

[app] (name=ruby)
  [Maximized] {yes}
[end]
EOF
# Оновлюємо конфігурацію запущеного Fluxbox на льоту
fluxbox-remote reconfigure 2>/dev/null || true

echo "🔨 [5/6] Building workspace in ${WS_DIR}..."
cd "${WS_DIR}"
# Build all project packages with symlink support for fast Python development
rm -rf build/ install/ log/
colcon build --symlink-install

echo "🔗 [6/6] Activating the local workspace..."
SETUP_LINE="source ${WS_DIR}/install/setup.bash"
if ! grep -qF "$SETUP_LINE" ~/.bashrc; then
    echo "$SETUP_LINE" >> ~/.bashrc
fi
# Activate both environments in the current shell
# (works only if script is run as: source setup.sh)
source /opt/ros/jazzy/setup.bash
source "${WS_DIR}/install/setup.bash"

echo ""
echo "✅ ALL DONE! ROS 2 Jazzy is configured for workspace: ${WS_DIR}"