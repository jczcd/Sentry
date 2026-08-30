#include "sentinel/swerve_kinematics.hpp"

#include <array>
#include <cassert>
#include <cmath>

namespace {

constexpr float kTolerance = 1.0e-4F;

bool near(const float lhs, const float rhs, const float tolerance = kTolerance) {
  return std::fabs(lhs - rhs) <= tolerance;
}

sentinel::SwerveGeometry test_geometry(const float max_wheel_radps = 100.0F) {
  return sentinel::SwerveGeometry{
      {{{0.25F, 0.20F}, {0.25F, -0.20F}, {-0.25F, 0.20F}, {-0.25F, -0.20F}}},
      0.075F,
      max_wheel_radps,
      1.0e-5F,
  };
}

void expect_round_trip(const sentinel::ChassisCommand& command) {
  const sentinel::SwerveKinematics kinematics(test_geometry());
  const std::array<float, sentinel::kSwerveModuleCount> current{};
  const auto targets = kinematics.inverse(command, current);

  std::array<sentinel::ModuleMeasurement, sentinel::kSwerveModuleCount> measured{};
  for (std::size_t index = 0U; index < measured.size(); ++index) {
    measured[index] = {targets[index].steer_rad, targets[index].wheel_radps};
  }

  const sentinel::ChassisCommand reconstructed = kinematics.forward(measured);
  assert(near(reconstructed.vx_mps, command.vx_mps));
  assert(near(reconstructed.vy_mps, command.vy_mps));
  assert(near(reconstructed.wz_radps, command.wz_radps));
}

void test_round_trips() {
  expect_round_trip({1.0F, 0.0F, 0.0F});
  expect_round_trip({0.0F, 0.8F, 0.0F});
  expect_round_trip({0.0F, 0.0F, 0.7F});
  expect_round_trip({0.7F, -0.3F, 0.4F});
}

void test_shortest_path_reverses_wheel() {
  const sentinel::SwerveKinematics kinematics(test_geometry());
  const std::array<float, sentinel::kSwerveModuleCount> current{};
  const auto targets = kinematics.inverse({-1.0F, 0.0F, 0.0F}, current);
  for (const sentinel::ModuleTarget& target : targets) {
    assert(near(target.steer_rad, 0.0F));
    assert(target.wheel_radps < 0.0F);
  }
}

void test_stationary_holds_steering() {
  const sentinel::SwerveKinematics kinematics(test_geometry());
  const std::array<float, sentinel::kSwerveModuleCount> current{
      0.1F, -0.2F, 0.3F, -0.4F};
  const auto targets = kinematics.inverse({}, current);
  for (std::size_t index = 0U; index < targets.size(); ++index) {
    assert(near(targets[index].steer_rad, current[index]));
    assert(near(targets[index].wheel_radps, 0.0F));
  }
}

void test_uniform_saturation() {
  constexpr float limit = 20.0F;
  const sentinel::SwerveKinematics kinematics(test_geometry(limit));
  const std::array<float, sentinel::kSwerveModuleCount> current{};
  const auto targets = kinematics.inverse({4.0F, 2.0F, 3.0F}, current);

  float largest = 0.0F;
  for (const sentinel::ModuleTarget& target : targets) {
    largest = std::fmax(largest, std::fabs(target.wheel_radps));
  }
  assert(near(largest, limit));
}

void test_degenerate_geometry_fails_safe() {
  sentinel::SwerveGeometry geometry = test_geometry();
  geometry.wheel_radius_m = 0.0F;
  const sentinel::SwerveKinematics kinematics(geometry);
  const std::array<float, sentinel::kSwerveModuleCount> current{};
  const auto targets = kinematics.inverse({1.0F, 1.0F, 1.0F}, current);
  for (const sentinel::ModuleTarget& target : targets) {
    assert(near(target.wheel_radps, 0.0F));
  }
}

}  // namespace

int main() {
  test_round_trips();
  test_shortest_path_reverses_wheel();
  test_stationary_holds_steering();
  test_uniform_saturation();
  test_degenerate_geometry_fails_safe();
  return 0;
}
