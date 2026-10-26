function [scenario, egoVehicle] = ev_c04_other_stop()
%EV_C04_OTHER_STOP other_stop   at 52.7-56.3 s, from a real drive.
%   scenario = ev_c04_other_stop(); plot(scenario); while advance(scenario), pause(0.05), end
%   drivingScenarioDesigner(ev_c04_other_stop())
%
%   Drive 20261022T164127Z-084b, drive time 49.7-59.3 s (the event +/- 3 s).
%   Event (agent verdict: corrected, validator: passed): type other_stop, side -,
%   detail -, 52.70-56.34 s. Agent's reason (not validated): The car was stopped with zero speed and standstill true, then resumed motion at 0.3 mph with standstill false.
%   Validated claims:
%   seq 818 mph = 0.0  (frame 00000818_4601971957000.jpg, CAN row 4601971941261)
%   seq 818 standstill = true  (frame 00000818_4601971957000.jpg, CAN row 4601971941261)
%   seq 874 mph = 0.3  (frame 00000874_4605603353000.jpg, CAN row 4605599954140)
%   seq 874 standstill = false  (frame 00000874_4605603353000.jpg, CAN row 4605599954140)
%
%   Ego: the car's speed profile (CAN front wheel speed) along its path (CAN yaw rate, calibrated
%   (raw - 2.5) * 0.112 deg/s), starting at the origin facing +x. Road: two 3.5 m
%   lanes along the path, ego in the right lane. Made by src/scripts/export_matlab.py.

scenario = drivingScenario('SampleTime', 0.1);  % runs until the ego's trajectory ends (9.6 s of drive)

roadCenters = [0.000 1.750 0.000; 19.898 3.764 0.000];
road(scenario, roadCenters, 'Lanes', lanespec([1 1], 'Width', 3.5), 'Name', 'Road');

egoVehicle = vehicle(scenario, 'ClassID', 1, 'Position', [0.000 0.000 0], 'Name', 'Ego');
waypoints = [0.000 0.000 0.000; 0.506 0.008 0.000; 1.075 0.035 0.000; 1.670 0.081 0.000; 2.222 0.136 0.000; 2.662 0.181 0.000];
speed = [0.000; 0.808; 1.054; 1.300; 1.456; 1.551];
waittime = [6.800; 0.000; 0.000; 0.000; 0.000; 0.000];
trajectory(egoVehicle, waypoints, speed, waittime);
end
