add_library(sentinel_common STATIC
  src/swerve_kinematics.cpp
)

target_include_directories(sentinel_common
  PUBLIC
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
)

target_compile_features(sentinel_common PUBLIC cxx_std_17)

if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
  target_compile_options(sentinel_common PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()

if(SENTRY_BUILD_TESTS AND BUILD_TESTING)
  add_executable(test_swerve_kinematics tests/test_swerve_kinematics.cpp)
  target_link_libraries(test_swerve_kinematics PRIVATE sentinel_common)
  target_compile_features(test_swerve_kinematics PRIVATE cxx_std_17)
  if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
    target_compile_options(test_swerve_kinematics PRIVATE -Wall -Wextra -Wpedantic -Werror)
  endif()
  add_test(NAME swerve_kinematics COMMAND test_swerve_kinematics)
endif()
