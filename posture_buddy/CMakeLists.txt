cmake_minimum_required(VERSION 3.0.2)
project(posture_buddy)

find_package(catkin REQUIRED COMPONENTS
  rospy
  std_msgs
  sensor_msgs
  geometry_msgs
  message_generation
)

## All 4 shared message types live here.
## Modules 2-5 import these — they must have this package in their workspace.
add_message_files(
  FILES
  Kinematics.msg
  PostureStatus.msg
  FatigueMetrics.msg
  HriStatus.msg
)

generate_messages(
  DEPENDENCIES
  std_msgs
)

catkin_package(
  CATKIN_DEPENDS
    rospy
    std_msgs
    sensor_msgs
    geometry_msgs
    message_runtime
)

catkin_install_python(PROGRAMS
  src/pose_estimation_node.py
  src/posture_eval_node.py
  src/fatigue_state_node.py
  src/feedback_controller_node.py
  DESTINATION ${CATKIN_PACKAGE_BIN_DESTINATION}
)

install(DIRECTORY launch/
  DESTINATION ${CATKIN_PACKAGE_SHARE_DESTINATION}/launch
)
