# CMake configuration for building the pybind11-based Python module from ap.cpp
cmake_minimum_required(VERSION 3.15)
project(accel)

# Force clang-tidy checking on the project
set(CMAKE_CXX_CLANG_TIDY "clang-tidy;-extra-arg=-std=c++23;-config-file=${CMAKE_SOURCE_DIR}/.clang-tidy")

set(CMAKE_EXPORT_COMPILE_COMMANDS ON)
# Use Python_EXECUTABLE if specified
if(DEFINED Python_EXECUTABLE)
    set(Python3_EXECUTABLE ${Python_EXECUTABLE})
endif()

# Find Python and pybind11
find_package(Python3 COMPONENTS Interpreter Development REQUIRED)
find_package(pybind11 CONFIG REQUIRED)

# Set the source files
file(GLOB SRC accel/src/*.cpp)

# Create the Python module
pybind11_add_module(accel MODULE ${SRC})

# Set compile options
set_target_properties(accel PROPERTIES
    CXX_STANDARD 23
    CXX_STANDARD_REQUIRED YES
    CXX_EXTENSIONS NO
)

# Enable parallel LTO jobs (auto-detects number of cores)
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -flto=auto")

# Link Python libraries if needed
if(Python3_LIBRARIES)
    target_link_libraries(accel PRIVATE Python3::Python)
endif()

# Set install prefix to the top-level directory
set(CMAKE_INSTALL_PREFIX "${CMAKE_SOURCE_DIR}")

# Install the extension module into the src/worker/ package directory
install(TARGETS accel LIBRARY DESTINATION src/worker)

# Add a custom target for running cppcheck on the C++ source files
# This will help in static code analysis
find_program(CPPCHECK cppcheck)
if(NOT CPPCHECK)
    message(FATAL_ERROR "cppcheck not found. Please install cppcheck to run static analysis.")
endif()
add_custom_target(
        cppcheck
        COMMAND cppcheck --inconclusive --force --std=c++23 --quiet accel/src/
        WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
)
