# This CMakeLists.txt is now a stub. The real build configuration is in accel/CMakeLists.txt
cmake_minimum_required(VERSION 3.15)
project(accel_stub)

# Enforce clang-tidy for all subdirectories
set(CMAKE_CXX_CLANG_TIDY "clang-tidy;-extra-arg=-std=c++23;-config-file=${CMAKE_SOURCE_DIR}/.clang-tidy")

add_subdirectory(accel)
