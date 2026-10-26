function [scenario, egoVehicle] = ev_c32_turn()
%EV_C32_TURN turn right blinker at 395.4-400.7 s, from a real drive.
%   scenario = ev_c32_turn(); plot(scenario); while advance(scenario), pause(0.05), end
%   drivingScenarioDesigner(ev_c32_turn())
%
%   Drive 20261022T164127Z-084b, drive time 392.4-403.7 s (the event +/- 3 s).
%   Event (agent verdict: confirmed, validator: passed): type turn, side right,
%   detail blinker, 395.36-400.69 s. Agent's reason (not validated): The vehicle steered right with a right blinker engaged before and during the maneuver, reducing speed from ~10 mph to a stop, consistent with a right turn.
%   Validated claims:
%   seq 6039 steer = -347.1  (frame 00006039_4947291597000.jpg, CAN row 4947291578393)
%   seq 6039 blinker = right  (frame 00006039_4947291597000.jpg, CAN row 4947291578393)
%   seq 5993 blinker = right  (frame 00005993_4944326456000.jpg, CAN row 4944324718310)
%   seq 6076 mph = 2.5  (frame 00006076_4949956898000.jpg, CAN row 4949955590163)
%
%   Ego: the car's speed profile (CAN front wheel speed) along its path (CAN yaw rate, calibrated
%   (raw - 2.5) * 0.112 deg/s), starting at the origin facing +x. Road: two 3.5 m
%   lanes along the path, ego in the right lane. Made by src/scripts/export_matlab.py.

scenario = drivingScenario('SampleTime', 0.1);  % runs until the ego's trajectory ends (11.3 s of drive)

roadCenters = [0.000 1.750 0.000; 4.227 1.869 0.000; 8.208 2.197 0.000; 12.442 2.787 0.000; 16.710 3.486 0.000; 21.512 3.551 0.000; 26.135 1.557 0.000; 28.805 -2.857 0.000; 28.872 -7.419 0.000; 28.946 -12.418 0.000];
road(scenario, roadCenters, 'Lanes', lanespec([1 1], 'Width', 3.5), 'Name', 'Road');

egoVehicle = vehicle(scenario, 'ClassID', 1, 'Position', [0.000 0.000 0], 'Name', 'Ego');
waypoints = [0.000 0.000 0.000; 0.734 0.003 0.000; 1.462 0.014 0.000; 2.187 0.031 0.000; 2.907 0.054 0.000; 3.621 0.085 0.000; 4.326 0.122 0.000; 5.025 0.165 0.000; 5.717 0.212 0.000; 6.400 0.266 0.000; 7.074 0.325 0.000; 7.741 0.389 0.000; 8.399 0.458 0.000; 9.047 0.532 0.000; 9.683 0.610 0.000; 10.313 0.693 0.000; 10.934 0.780 0.000; 11.547 0.871 0.000; 12.146 0.965 0.000; 12.731 1.061 0.000; 13.302 1.158 0.000; 13.858 1.255 0.000; 14.405 1.350 0.000; 14.936 1.441 0.000; 15.456 1.528 0.000; 15.963 1.610 0.000; 16.936 1.751 0.000; 17.878 1.856 0.000; 18.783 1.920 0.000; 19.647 1.937 0.000; 20.472 1.904 0.000; 21.261 1.819 0.000; 22.006 1.681 0.000; 22.695 1.492 0.000; 23.339 1.250 0.000; 23.942 0.954 0.000; 24.504 0.604 0.000; 25.006 0.220 0.000; 25.438 -0.180 0.000; 25.819 -0.605 0.000; 26.150 -1.047 0.000; 26.432 -1.502 0.000; 26.665 -1.958 0.000; 26.929 -2.633 0.000; 27.097 -3.240 0.000; 27.191 -3.754 0.000; 27.257 -4.384 0.000; 27.279 -5.015 0.000; 27.270 -5.552 0.000; 27.238 -6.106 0.000; 27.188 -6.672 0.000; 27.135 -7.200 0.000];
speed = [7.369; 7.313; 7.248; 7.257; 7.157; 7.118; 7.019; 6.984; 6.885; 6.807; 6.738; 6.648; 6.583; 6.462; 6.371; 6.328; 6.224; 6.160; 5.974; 5.883; 5.689; 5.611; 5.490; 5.291; 5.239; 5.028; 4.795; 4.626; 4.453; 4.220; 4.073; 3.879; 3.633; 3.503; 3.391; 3.317; 3.313; 3.011; 2.894; 2.812; 2.708; 2.648; 2.479; 2.255; 1.905; 1.607; 1.607; 1.520; 1.179; 1.067; 0.842; 0.000];
waittime = [0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 1.200];
trajectory(egoVehicle, waypoints, speed, waittime);
end
