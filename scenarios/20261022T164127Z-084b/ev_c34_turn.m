function [scenario, egoVehicle] = ev_c34_turn()
%EV_C34_TURN turn left no_blinker at 425.3-428.0 s, from a real drive.
%   scenario = ev_c34_turn(); plot(scenario); while advance(scenario), pause(0.05), end
%   drivingScenarioDesigner(ev_c34_turn())
%
%   Drive 20261022T164127Z-084b, drive time 422.3-431.0 s (the event +/- 3 s).
%   Event (agent verdict: confirmed, validator: passed): type turn, side left,
%   detail no_blinker, 425.34-428.04 s. Agent's reason (not validated): The steering wheel turned left past 90° and returned toward centre without any blinker activation, matching a left turn maneuver.
%   Validated claims:
%   seq 6457 steer = 145.7  (frame 00006457_4974611230000.jpg, CAN row 4974607699156)
%   seq 6476 steer = 218.1  (frame 00006476_4975943636000.jpg, CAN row 4975943976008)
%   seq 6457 blinker = null  (frame 00006457_4974611230000.jpg, CAN row 4974607699156)
%   seq 6476 blinker = null  (frame 00006476_4975943636000.jpg, CAN row 4975943976008)
%   seq 6457 gear = D  (frame 00006457_4974611230000.jpg, CAN row 4974607699156)
%   seq 6476 gear = D  (frame 00006476_4975943636000.jpg, CAN row 4975943976008)
%
%   Ego: the car's speed profile (CAN front wheel speed) along its path (CAN yaw rate, calibrated
%   (raw - 2.5) * 0.112 deg/s), starting at the origin facing +x. Road: two 3.5 m
%   lanes along the path, ego in the right lane. Made by src/scripts/export_matlab.py.

scenario = drivingScenario('SampleTime', 0.1);  % runs until the ego's trajectory ends (8.7 s of drive)

roadCenters = [0.000 1.750 0.000; 4.406 0.932 0.000; 7.808 1.000 0.000; 10.868 2.398 0.000; 13.576 4.967 0.000; 16.346 8.254 0.000; 19.311 11.671 0.000; 22.587 15.447 0.000];
road(scenario, roadCenters, 'Lanes', lanespec([1 1], 'Width', 3.5), 'Name', 'Road');

egoVehicle = vehicle(scenario, 'ClassID', 1, 'Position', [0.000 0.000 0], 'Name', 'Ego');
waypoints = [0.000 0.000 0.000; 0.536 -0.030 0.000; 1.143 -0.120 0.000; 1.735 -0.243 0.000; 2.378 -0.399 0.000; 2.939 -0.541 0.000; 3.608 -0.695 0.000; 4.104 -0.791 0.000; 4.638 -0.873 0.000; 5.211 -0.932 0.000; 5.824 -0.959 0.000; 6.472 -0.947 0.000; 7.146 -0.890 0.000; 7.846 -0.781 0.000; 8.566 -0.613 0.000; 9.297 -0.385 0.000; 10.049 -0.083 0.000; 10.802 0.291 0.000; 11.531 0.731 0.000; 12.240 1.238 0.000; 12.928 1.811 0.000; 13.599 2.443 0.000; 14.250 3.110 0.000; 14.884 3.805 0.000; 15.508 4.520 0.000; 16.125 5.248 0.000; 16.751 5.998 0.000; 17.379 6.758 0.000; 18.010 7.518 0.000; 18.645 8.277 0.000; 19.285 9.026 0.000; 19.929 9.757 0.000; 20.585 10.472 0.000; 21.254 11.165 0.000; 21.935 11.833 0.000; 22.279 12.156 0.000];
speed = [0.000; 1.045; 1.391; 1.568; 1.810; 2.142; 2.462; 2.618; 2.808; 2.967; 3.136; 3.348; 3.482; 3.633; 3.758; 3.874; 4.160; 4.250; 4.272; 4.419; 4.561; 4.630; 4.704; 4.708; 4.747; 4.825; 4.920; 4.928; 4.946; 4.941; 4.924; 4.838; 4.838; 4.799; 4.717; 4.738];
waittime = [0.200; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000];
trajectory(egoVehicle, waypoints, speed, waittime);
end
