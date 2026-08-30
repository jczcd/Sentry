#pragma once

#include <array>
#include <cstddef>

namespace sentinel {

inline constexpr std::size_t kSwerveModuleCount = 4U;

struct ChassisCommand final {
  float vx_mps{0.0F};
  float vy_mps{0.0F};
  float wz_radps{0.0F};
};

struct ModulePosition final {
  float x_m{0.0F};
  float y_m{0.0F};
};

struct SwerveGeometry final {
  std::array<ModulePosition, kSwerveModuleCount> modules{};
  float wheel_radius_m{0.0F};
  float max_wheel_radps{0.0F};
  float stationary_speed_mps{1.0e-4F};
};

struct ModuleTarget final {
  float steer_rad{0.0F};
  float wheel_radps{0.0F};
};

struct ModuleMeasurement final {
  float steer_rad{0.0F};
  float wheel_radps{0.0F};
};

[[nodiscard]] float wrap_angle_rad(float angle_rad) noexcept;

class SwerveKinematics final {
 public:
  explicit constexpr SwerveKinematics(const SwerveGeometry& geometry) noexcept
      : geometry_(geometry) {}

  [[nodiscard]] std::array<ModuleTarget, kSwerveModuleCount> inverse(
      const ChassisCommand& command,
      const std::array<float, kSwerveModuleCount>& current_steer_rad) const noexcept;

  [[nodiscard]] ChassisCommand forward(
      const std::array<ModuleMeasurement, kSwerveModuleCount>& modules) const noexcept;

  [[nodiscard]] constexpr const SwerveGeometry& geometry() const noexcept {
    return geometry_;
  }

 private:
  SwerveGeometry geometry_;
};

}  // namespace sentinel
