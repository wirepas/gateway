cmake_minimum_required(VERSION 3.18)

project(sinkService LANGUAGES C)

set(CMAKE_C_STANDARD 99)
if(NOT CMAKE_BUILD_TYPE)
    set(CMAKE_BUILD_TYPE RelWithDebInfo)
endif()
set(CMAKE_C_FLAGS_RELEASE "-O2")

add_compile_options(-Wall -Werror -Wextra -Wno-unused-parameter)

include(FetchContent)
FetchContent_Declare(
    c-mesh-api
    GIT_REPOSITORY https://github.com/wirepas/c-mesh-api/
    GIT_TAG 1b8767b9f26717d1819a8043889d58f29f89da13
    SOURCE_SUBDIR lib
)
FetchContent_MakeAvailable(c-mesh-api)

find_package(PkgConfig REQUIRED)
pkg_check_modules(systemd REQUIRED IMPORTED_TARGET libsystemd)

add_executable(${CMAKE_PROJECT_NAME}
    source/main.c
    source/config.c
    source/data.c
    source/otap.c
)

target_link_libraries(${CMAKE_PROJECT_NAME} wpc PkgConfig::systemd)

