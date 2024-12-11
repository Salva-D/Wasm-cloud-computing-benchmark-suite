# Copyright (C) 2019 Intel Corporation.  All rights reserved.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

cmake_minimum_required(VERSION 2.8...3.18)
project(socket_api_sample_wasm_app)

message(CHECK_START "Detecting WASM-MICRO-RUNTIME at /opt/wasm-micro-runtime")
if(NOT (DEFINED WASM_MICRO_RUNTIME_DIR OR DEFINED CACHE{WASM_MICRO_RUNTIME_DIR}))
  find_path(WASM_MICRO_RUNTIME_PARENT
    wasm-micro-runtime
    PATHS /opt
    NO_DEFAULT_PATH
    NO_CMAKE_FIND_ROOT_PATH
  )
  if(WASM_MICRO_RUNTIME_PARENT)
    set(WASM_MICRO_RUNTIME_DIR ${WASM_MICRO_RUNTIME_PARENT}/wasm-micro-runtime)
  endif()
endif()
if(WASM_MICRO_RUNTIME_DIR)
  message(CHECK_PASS "found")
else()
  message(CHECK_FAIL "not found")
endif()

if(NOT EXISTS ${WASM_MICRO_RUNTIME_DIR})
  message(FATAL_ERROR "Please install WASM-MICRO-RUNTIME under /opt/wasm-micro-runtime")
endif()

message(CHECK_START "Detecting WABT")
if(NOT (DEFINED WABT_DIR OR DEFINED CACHE{WABT_DIR}))
  find_path(WABT_DIR
    wabt
    PATHS /opt
    NO_DEFAULT_PATH
    NO_CMAKE_FIND_ROOT_PATH
  )
  if(DEFINED WABT_DIR)
    set(WABT_DIR ${WABT_DIR}/wabt)
  endif()
endif()
if(WABT_DIR)
  message(CHECK_PASS "found")
else()
  message(CHECK_FAIL "not found")
endif()

message(CHECK_START "Detecting WASM_OBJDUMP at ${WABT_DIR}")
find_program(WASM_OBJDUMP
  wasm-objdump
  PATHS "${WABT_DIR}/bin"
  NO_DEFAULT_PATH
  NO_CMAKE_FIND_ROOT_PATH
)
if(WASM_OBJDUMP)
  message(CHECK_PASS "found")
else()
  message(CHECK_FAIL "not found")
endif()

set(SRC ${CMAKE_CURRENT_SOURCE_DIR})

include(${WASM_MICRO_RUNTIME_DIR}/core/iwasm/libraries/lib-socket/lib_socket_wasi.cmake)

set(MY_SOURCE_FILES 
${CMAKE_CURRENT_SOURCE_DIR}/no_sql_db.c
${CMAKE_CURRENT_SOURCE_DIR}/dballoc.c
${CMAKE_CURRENT_SOURCE_DIR}/dbcompare.c
${CMAKE_CURRENT_SOURCE_DIR}/dbdata.c
${CMAKE_CURRENT_SOURCE_DIR}/dbdump.c
${CMAKE_CURRENT_SOURCE_DIR}/dbhash.c
${CMAKE_CURRENT_SOURCE_DIR}/dbindex.c
${CMAKE_CURRENT_SOURCE_DIR}/dbjson.c
${CMAKE_CURRENT_SOURCE_DIR}/dblock.c
${CMAKE_CURRENT_SOURCE_DIR}/dblog.c
${CMAKE_CURRENT_SOURCE_DIR}/dbmem.c
${CMAKE_CURRENT_SOURCE_DIR}/dbmpool.c
${CMAKE_CURRENT_SOURCE_DIR}/dbquery.c
${CMAKE_CURRENT_SOURCE_DIR}/dbschema.c
${CMAKE_CURRENT_SOURCE_DIR}/dbutil.c
${CMAKE_CURRENT_SOURCE_DIR}/yajl_all.c)

function(COMPILE_WITH_CLANG FILE_NAME)
  set(WASM_MODULE ${FILE_NAME}.wasm)

  set(MAIN_TARGET_NAME MODULE_${FILE_NAME})

  add_executable(${MAIN_TARGET_NAME} ${MY_SOURCE_FILES})
  set_target_properties(${MAIN_TARGET_NAME} PROPERTIES OUTPUT_NAME ${WASM_MODULE})
  target_include_directories(${MAIN_TARGET_NAME} PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/inc)
  target_compile_options(${MAIN_TARGET_NAME} INTERFACE -pthread)
  target_link_libraries(${MAIN_TARGET_NAME} socket_wasi_ext)
  target_link_options(${MAIN_TARGET_NAME} PRIVATE
    LINKER:--export=__heap_base
    LINKER:--export=__data_end
    LINKER:--export=malloc
    LINKER:--export=free
    # LINKER:--shared-memory,--max-memory=16777216
    # LINKER:--shared-memory,--max-memory=1073741824
    # LINKER:-z,stack-size=8388608
    LINKER:-z,stack-size=33554432
    LINKER:--shared-memory,--max-memory=2147483648
    LINKER:--no-check-features
    LINKER:--allow-undefined
  )

  if(EXISTS ${WASM_OBJDUMP})
    message(STATUS "Dumping ${WASM_MODULE}...")
    set(WASM_DUMP ${WASM_MODULE}.dump)
    set(DUMP_TARGET_NAME DUMP_${FILE_NAME})

    add_custom_command(OUTPUT ${WASM_DUMP}
      COMMAND ${WASM_OBJDUMP} -dx ${WASM_MODULE} > ${WASM_DUMP}
      COMMENT "Dumping ${WASM_MODULE}..."
      DEPENDS ${MAIN_TARGET_NAME}
    )

    add_custom_target(${DUMP_TARGET_NAME} ALL
      DEPENDS ${WASM_DUMP}
    )
  endif()
endfunction()

compile_with_clang(no_sql_db)
