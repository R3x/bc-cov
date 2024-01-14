project(CovInstrument)
cmake_minimum_required(VERSION 3.4.3)
if(POLICY CMP0074)
    cmake_policy(SET CMP0074 OLD)
endif()

set(ENV{LLVM_DIR} /home/r3x/llvm10/llvm-10.0.0.obj/)
set(ENV{LLVM_SRC} /home/r3x/llvm10/llvm-10.0.0.src/)
set(ENV{LLVM_OBJ} /home/r3x/llvm10/llvm-10.0.0.obj/)
# To support both in- and out-of-source builds,
# we check for the presence of the add_llvm_loadable_module command.
# - if this command is not present, we are building out-of-source
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)
if(NOT COMMAND add_llvm_loadable_module)
    if (DEFINED ENV{LLVM_DIR})
        # We need to match the build environment for LLVM:
        # In particular, we need C++11 and the -fno-rtti flag
        set(CMAKE_CXX_STANDARD 14)
	if(CMAKE_BUILD_TYPE MATCHES "Debug")
		set(CMAKE_CXX_FLAGS "-std=c++14 -D__GLIBCXX_USE_CXX11_ABI=0 -O0 -fno-rtti")
	else()
		set(CMAKE_CXX_FLAGS "-std=c++14 -D__GLIBCXX_USE_CXX11_ABI=0 -O3 -fno-rtti")
	endif()

	find_package(LLVM REQUIRED CONFIG)
        
        list(APPEND CMAKE_MODULE_PATH "${LLVM_CMAKE_DIR}")
        include(AddLLVM)

        add_definitions(${LLVM_DEFINITIONS})
        include_directories(${LLVM_INCLUDE_DIRS})

    else()
        message(FATAL_ERROR "\
WARNING: The LLVM_DIR var was not set (required for an out-of-source build)!\n\
Please set this to environment variable to point to the LLVM build directory\
(e.g. on linux: export LLVM_DIR=/path/to/llvm/build/dir)")
    endif()
else()
        set(IN_SOURCE_BUILD 1)
endif()

include_directories(include/)

add_library(CovInstrument MODULE src/CovInstrument.cpp)

# add statically linked library
add_library(CovInstrumentStatic STATIC src/CovInstrument.cpp)

set_target_properties(CovInstrument PROPERTIES
        COMPILE_FLAGS "-g"
        )

set_target_properties(CovInstrumentStatic PROPERTIES
        COMPILE_FLAGS "-g"
        )

target_compile_features(CovInstrument PRIVATE cxx_range_for cxx_auto_type)

target_compile_features(CovInstrumentStatic PRIVATE cxx_range_for cxx_auto_type)