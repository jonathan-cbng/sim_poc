# CMake configuration for building the pybind11-based Python module from ap.cpp
cmake_minimum_required(VERSION 3.12)
project(ap_module)

set(CMAKE_EXPORT_COMPILE_COMMANDS ON)
# Use Python_EXECUTABLE if specified
if(DEFINED Python_EXECUTABLE)
    set(Python3_EXECUTABLE ${Python_EXECUTABLE})
endif()

# Find Python and pybind11
find_package(Python3 COMPONENTS Interpreter Development REQUIRED)
find_package(pybind11 CONFIG REQUIRED)

# Set the source files
set(SRC src_cpp/node.cpp src_cpp/rt.cpp src_cpp/ap.cpp src_cpp/node_sim_bindings.cpp)

# Create the Python module
pybind11_add_module(node_sim MODULE ${SRC})

# Set compile options
set_target_properties(node_sim PROPERTIES
    CXX_STANDARD 23
    CXX_STANDARD_REQUIRED YES
    CXX_EXTENSIONS NO
)

# Link Python libraries if needed
if(Python3_LIBRARIES)
    target_link_libraries(node_sim PRIVATE Python3::Python)
endif()

# Install the Python module
# Optionally, you can specify the install directory for Python modules
message(STATUS "Python3_SITEARCH: ${Python3_SITEARCH}")
install(TARGETS node_sim
        LIBRARY DESTINATION ${Python3_SITEARCH}
)
# Add a custom target for running cppcheck on the C++ source files
# This will help in static code analysis
find_program(CPPCHECK cppcheck)
if(NOT CPPCHECK)
    message(FATAL_ERROR "cppcheck not found. Please install cppcheck to run static analysis.")
endif()
add_custom_target(
        cppcheck
        COMMAND cppcheck --inconclusive --force --std=c++23 --quiet src_cpp/
        WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
)
