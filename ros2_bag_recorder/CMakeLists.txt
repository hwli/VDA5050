cmake_minimum_required(VERSION 3.8)
project(ros2_bag_recorder)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

# Find dependencies
find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(rosbag2_cpp REQUIRED)
find_package(rosbag2_storage REQUIRED)
find_package(rosbag2_storage_default_plugins REQUIRED)

# Add executable
add_executable(bag_recorder src/bag_recorder.cpp)
ament_target_dependencies(bag_recorder
  rclcpp
  rosbag2_cpp
  rosbag2_storage
  rosbag2_storage_default_plugins
)

# Install executable
install(TARGETS bag_recorder
  DESTINATION lib/${PROJECT_NAME}
)

# Install launch files if any
if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/launch")
  install(DIRECTORY launch
    DESTINATION share/${PROJECT_NAME}/
  )
endif()

if(BUILD_TESTING)
  find_package(ament_lint_auto REQUIRED)
  ament_lint_auto_find_test_dependencies()
endif()

ament_package()
