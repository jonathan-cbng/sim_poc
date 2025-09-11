# CMake configuration for building the pybind11-based Python module from ap.cpp
cmake_minimum_required(VERSION 3.15)
project(accel)

set(CMAKE_EXPORT_COMPILE_COMMANDS ON)
# Use Python_EXECUTABLE if specified
if(DEFINED Python_EXECUTABLE)
    set(Python3_EXECUTABLE ${Python_EXECUTABLE})
endif()

# Find Python and pybind11
find_package(Python3 COMPONENTS Interpreter Development REQUIRED)
find_package(pybind11 CONFIG REQUIRED)

# Set the source files
file(GLOB SRC src/*.cpp)

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

# Compute the project root (parent of accel directory)
get_filename_component(PROJECT_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/.." ABSOLUTE)

# If the install prefix is still the default, set it to the project root
if(CMAKE_INSTALL_PREFIX_INITIALIZED_TO_DEFAULT)
    set(CMAKE_INSTALL_PREFIX "${PROJECT_ROOT}" CACHE PATH "Install path prefix" FORCE)
endif()

# Install the extension module into the src/worker/ package directory (absolute path)
install(TARGETS accel LIBRARY DESTINATION "${PROJECT_ROOT}/src/worker")

# Add a custom target for running cppcheck on the C++ source files
# This will help in static code analysis
find_program(CPPCHECK cppcheck)
if(NOT CPPCHECK)
    message(FATAL_ERROR "cppcheck not found. Please install cppcheck to run static analysis.")
endif()
add_custom_target(
        cppcheck
        COMMAND cppcheck --inconclusive --force --std=c++23 --quiet src/
        WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
)
