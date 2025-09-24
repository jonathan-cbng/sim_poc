# This CMakeLists.txt is now a stub. The real build configuration is in accel/CMakeLists.txt
cmake_minimum_required(VERSION 3.15)
project(accel_stub)

# Enforce clang-tidy for all subdirectories
set(CMAKE_CXX_CLANG_TIDY "clang-tidy;-extra-arg=-std=c++23;-config-file=${CMAKE_SOURCE_DIR}/.clang-tidy")

add_subdirectory(accel)

# --- PlantUML SVG generation for docs/ ---
set(PLANTUML_JAR "${CMAKE_SOURCE_DIR}/utils/plantuml.jar")
find_program(JAVA_EXEC java)
if(NOT JAVA_EXEC)
    message(FATAL_ERROR "Java not found. Please install Java and ensure it is in your PATH.")
endif()

file(GLOB PUML_FILES "${CMAKE_SOURCE_DIR}/docs/*.puml")
set(SVG_FILES)
foreach(PUML_FILE ${PUML_FILES})
    get_filename_component(PUML_NAME ${PUML_FILE} NAME_WE)
    set(SVG_FILE "${CMAKE_SOURCE_DIR}/docs/${PUML_NAME}.svg")
    add_custom_command(
        OUTPUT ${SVG_FILE}
        COMMAND ${JAVA_EXEC} -jar ${PLANTUML_JAR} -tsvg ${PUML_FILE}
        DEPENDS ${PUML_FILE} ${PLANTUML_JAR}
        COMMENT "Generating ${SVG_FILE} from ${PUML_FILE} using plantuml.jar"
        VERBATIM
    )
    list(APPEND SVG_FILES ${SVG_FILE})
endforeach()

add_custom_target(puml_svgs ALL DEPENDS ${SVG_FILES})
