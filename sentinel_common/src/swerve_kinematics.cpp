#include "sentinel/swerve_kinematics.hpp"

#include <cmath>

namespace sentinel {
namespace {

constexpr float kPi = 3.14159265358979323846F;
constexpr float kTwoPi = 2.0F * kPi;
constexpr float kHalfPi = 0.5F * kPi;
constexpr float kEpsilon = 1.0e-6F;

bool solve_3x3(float matrix[3][4], float solution[3]) noexcept {
  for (std::size_t column = 0U; column < 3U; ++column) {
    std::size_t pivot = column;
    for (std::size_t row = column + 1U; row < 3U; ++row) {
      if (::fabsf(matrix[row][column]) > ::fabsf(matrix[pivot][column])) {
        pivot = row;
      }
    }

    if (::fabsf(matrix[pivot][column]) <= kEpsilon) {
      return false;
    }

    if (pivot != column) {
      for (std::size_t value = column; value < 4U; ++value) {
        const float temporary = matrix[column][value];
        matrix[column][value] = matrix[pivot][value];
        matrix[pivot][value] = temporary;
      }
    }

    const float divisor = matrix[column][column];
    for (std::size_t value = column; value < 4U; ++value) {
      matrix[column][value] /= divisor;
    }

    for (std::size_t row = 0U; row < 3U; ++row) {
      if (row == column) {
        continue;
      }
      const float factor = matrix[row][column];
      for (std::size_t value = column; value < 4U; ++value) {
        matrix[row][value] -= factor * matrix[column][value];
      }
    }
  }

  solution[0] = matrix[0][3];
  solution[1] = matrix[1][3];
  solution[2] = matrix[2][3];
  return true;
}

}  // namespace

float wrap_angle_rad(const float angle_rad) noexcept {
  float wrapped = ::fmodf(angle_rad + kPi, kTwoPi);
  if (wrapped < 0.0F) {
    wrapped += kTwoPi;
  }
  return wrapped - kPi;
}

std::array<ModuleTarget, kSwerveModuleCount> SwerveKinematics::inverse(
    const ChassisCommand& command,
    const std::array<float, kSwerveModuleCount>& current_steer_rad) const noexcept {
  std::array<ModuleTarget, kSwerveModuleCount> targets{};

  if (geometry_.wheel_radius_m <= kEpsilon) {
    return targets;
  }

  float largest_wheel_radps = 0.0F;
  for (std::size_t index = 0U; index < kSwerveModuleCount; ++index) {
    const ModulePosition& position = geometry_.modules[index];
    const float module_vx_mps = command.vx_mps - command.wz_radps * position.y_m;
    const float module_vy_mps = command.vy_mps + command.wz_radps * position.x_m;
    float linear_speed_mps = ::hypotf(module_vx_mps, module_vy_mps);

    if (linear_speed_mps <= geometry_.stationary_speed_mps) {
      targets[index].steer_rad = wrap_angle_rad(current_steer_rad[index]);
      targets[index].wheel_radps = 0.0F;
      continue;
    }

    float target_angle_rad = ::atan2f(module_vy_mps, module_vx_mps);
    const float steering_error_rad =
        wrap_angle_rad(target_angle_rad - current_steer_rad[index]);
    if (::fabsf(steering_error_rad) > kHalfPi) {
      target_angle_rad = wrap_angle_rad(target_angle_rad + kPi);
      linear_speed_mps = -linear_speed_mps;
    }

    targets[index].steer_rad = target_angle_rad;
    targets[index].wheel_radps = linear_speed_mps / geometry_.wheel_radius_m;
    const float magnitude = ::fabsf(targets[index].wheel_radps);
    if (magnitude > largest_wheel_radps) {
      largest_wheel_radps = magnitude;
    }
  }

  if (geometry_.max_wheel_radps > kEpsilon &&
      largest_wheel_radps > geometry_.max_wheel_radps) {
    const float scale = geometry_.max_wheel_radps / largest_wheel_radps;
    for (ModuleTarget& target : targets) {
      target.wheel_radps *= scale;
    }
  }

  return targets;
}

ChassisCommand SwerveKinematics::forward(
    const std::array<ModuleMeasurement, kSwerveModuleCount>& modules) const noexcept {
  ChassisCommand result{};
  if (geometry_.wheel_radius_m <= kEpsilon) {
    return result;
  }

  float sum_x = 0.0F;
  float sum_y = 0.0F;
  float sum_radius_squared = 0.0F;
  float rhs_vx = 0.0F;
  float rhs_vy = 0.0F;
  float rhs_wz = 0.0F;

  for (std::size_t index = 0U; index < kSwerveModuleCount; ++index) {
    const ModulePosition& position = geometry_.modules[index];
    const float linear_speed_mps =
        modules[index].wheel_radps * geometry_.wheel_radius_m;
    const float module_vx_mps = linear_speed_mps * ::cosf(modules[index].steer_rad);
    const float module_vy_mps = linear_speed_mps * ::sinf(modules[index].steer_rad);

    sum_x += position.x_m;
    sum_y += position.y_m;
    sum_radius_squared +=
        position.x_m * position.x_m + position.y_m * position.y_m;
    rhs_vx += module_vx_mps;
    rhs_vy += module_vy_mps;
    rhs_wz += -position.y_m * module_vx_mps + position.x_m * module_vy_mps;
  }

  constexpr float module_count = static_cast<float>(kSwerveModuleCount);
  float normal_equations[3][4] = {
      {module_count, 0.0F, -sum_y, rhs_vx},
      {0.0F, module_count, sum_x, rhs_vy},
      {-sum_y, sum_x, sum_radius_squared, rhs_wz},
  };
  float solution[3] = {0.0F, 0.0F, 0.0F};
  if (!solve_3x3(normal_equations, solution)) {
    return result;
  }

  result.vx_mps = solution[0];
  result.vy_mps = solution[1];
  result.wz_radps = solution[2];
  return result;
}

}  // namespace sentinel
