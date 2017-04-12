# r4a_mic_commands

*Code by Vladimiros Sterzenchenco and Alexandros Metsai*

This code implements an oral command system taking input from a microphone, by utilizing the [RAPP Cloud Platform](https://github.com/robotics-4-all/r4a_rapp_cloud_api_python) ASR infrastructure.

## Setup

First enter the virtualenv of r4a_rapp_cloud_api_python (unless you have installed it in the system). You should install the following libraries:

```
[sudo] pip install pyaudio rospkg catkin_pkg
```

## Execution

First add the vocabulary of words to be recognized [here](https://github.com/robotics-4-all/r4a_mic_commands/blob/master/config/params.yaml#L4). You can then execute the code by:

```
roslaunch voice_recorder launcher.launch
```

The recognized words are posted in [this](https://github.com/robotics-4-all/r4a_mic_commands/blob/master/config/topics.yaml#L1) ROS topic.
