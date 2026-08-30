cmake_minimum_required(VERSION 3.16)
project(sentry LANGUAGES CXX)

option(SENTRY_BUILD_TESTS "Build host-side tests" ON)

if(SENTRY_BUILD_TESTS)
  include(CTest)
endif()

add_subdirectory(sentinel_common)
