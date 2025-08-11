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

# Set the source file
set(SRC src_cpp/ap.cpp)

# Create the Python module
pybind11_add_module(ap MODULE ${SRC})

# Set compile options
set_target_properties(ap PROPERTIES
    CXX_STANDARD 11
    CXX_STANDARD_REQUIRED YES
    CXX_EXTENSIONS NO
)

# Link Python libraries if needed
if(Python3_LIBRARIES)
    target_link_libraries(ap PRIVATE Python3::Python)
endif()

# Install the Python module
# Optionally, you can specify the install directory for Python modules
message(STATUS "Python3_SITEARCH: ${Python3_SITEARCH}")
install(TARGETS ap
        LIBRARY DESTINATION ${Python3_SITEARCH}
)
