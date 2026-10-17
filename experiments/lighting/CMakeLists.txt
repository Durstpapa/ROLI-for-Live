cmake_minimum_required(VERSION 3.22)
project(ROLI_Lighting_Probe VERSION 0.1.0 LANGUAGES C CXX)

include(FetchContent)
set(JUCE_MODULES_ONLY ON CACHE BOOL "" FORCE)
FetchContent_Declare(JUCE
    URL https://github.com/juce-framework/JUCE/archive/4f43011b96eb0636104cb3e433894cda98243626.tar.gz
    DOWNLOAD_EXTRACT_TIMESTAMP TRUE)
FetchContent_Declare(roli_blocks_basics
    URL https://github.com/WeAreROLI/roli_blocks_basics/archive/212ba4e237638b9ae8c2a4f76dd2070110392031.tar.gz
    DOWNLOAD_EXTRACT_TIMESTAMP TRUE
    SOURCE_DIR "${CMAKE_BINARY_DIR}/deps/roli_blocks_basics")
FetchContent_MakeAvailable(JUCE roli_blocks_basics)
juce_add_module("${roli_blocks_basics_SOURCE_DIR}")
add_executable(roli_lighting_probe)
target_sources(roli_lighting_probe PRIVATE main.cpp)
target_compile_features(roli_lighting_probe PRIVATE cxx_std_17)
target_compile_definitions(roli_lighting_probe PRIVATE
    JUCE_WEB_BROWSER=0 JUCE_USE_CURL=0 JUCE_MODAL_LOOPS_PERMITTED=1
    JUCE_GLOBAL_MODULE_SETTINGS_INCLUDED=1 JUCE_STANDALONE_APPLICATION=1
    ROLI_PROBE_SOURCE_DIR="${CMAKE_CURRENT_SOURCE_DIR}")
target_link_libraries(roli_lighting_probe PRIVATE roli_blocks_basics)
enable_testing()
add_test(NAME lighting_probe_offline COMMAND roli_lighting_probe --self-test)
