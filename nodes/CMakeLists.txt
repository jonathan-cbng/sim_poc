# CMake configuration for building the pybind11-based Python module from ap.cpp
cmake_minimum_required(VERSION 3.15)
project(_node_sim)

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
file(GLOB SRC cpp_src/*.cpp)

# Create the Python module
pybind11_add_module(_node_sim MODULE ${SRC})

# Set compile options
set_target_properties(_node_sim PROPERTIES
    CXX_STANDARD 23
    CXX_STANDARD_REQUIRED YES
    CXX_EXTENSIONS NO
)

# Enable parallel LTO jobs (auto-detects number of cores)
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -flto=auto")

# Link Python libraries if needed
if(Python3_LIBRARIES)
    target_link_libraries(_node_sim PRIVATE Python3::Python)
endif()

# Set install prefix to the top-level directory
set(CMAKE_INSTALL_PREFIX "${CMAKE_SOURCE_DIR}")

# Install the extension module into the nodes/ package directory
install(TARGETS _node_sim LIBRARY DESTINATION nodes)

# Add a custom target for running cppcheck on the C++ source files
# This will help in static code analysis
find_program(CPPCHECK cppcheck)
if(NOT CPPCHECK)
    message(FATAL_ERROR "cppcheck not found. Please install cppcheck to run static analysis.")
endif()
add_custom_target(
        cppcheck
        COMMAND cppcheck --inconclusive --force --std=c++23 --quiet cpp_src/
        WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
)
