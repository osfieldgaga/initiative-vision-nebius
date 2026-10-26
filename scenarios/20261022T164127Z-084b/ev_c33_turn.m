function [scenario, egoVehicle] = ev_c33_turn()
%EV_C33_TURN turn right no_blinker at 419.4-424.7 s, from a real drive.
%   scenario = ev_c33_turn(); plot(scenario); while advance(scenario), pause(0.05), end
%   drivingScenarioDesigner(ev_c33_turn())
%
%   Drive 20261022T164127Z-084b, drive time 416.4-427.7 s (the event +/- 3 s).
%   Event (agent verdict: corrected, validator: passed): type turn, side right,
%   detail no_blinker, 419.35-424.71 s. Agent's reason (not validated): The steering shows a sustained right turn that starts before the start time and ends near straight, with no blinker activation throughout.
%   Validated claims:
%   seq 6363 steer = -132.8  (frame 00006363_4968614071000.jpg, CAN row 4968586085988)
%   seq 6446 steer = 0.6  (frame 00006446_4973977976000.jpg, CAN row 4973975368584)
%   seq 6363 blinker = null  (frame 00006363_4968614071000.jpg, CAN row 4968586085988)
%   seq 6446 blinker = null  (frame 00006446_4973977976000.jpg, CAN row 4973975368584)
%
%   Ego: the car's speed profile (CAN front wheel speed) along its path (CAN yaw rate, calibrated
%   (raw - 2.5) * 0.112 deg/s), starting at the origin facing +x. Road: two 3.5 m
%   lanes along the path, ego in the right lane. Made by src/scripts/export_matlab.py.

scenario = drivingScenario('SampleTime', 0.1);  % runs until the ego's trajectory ends (11.4 s of drive)

roadCenters = [0.000 1.750 0.000; 16.656 12.821 0.000];
road(scenario, roadCenters, 'Lanes', lanespec([1 1], 'Width', 3.5), 'Name', 'Road');

egoVehicle = vehicle(scenario, 'ClassID', 1, 'Position', [0.000 0.000 0], 'Name', 'Ego');
waypoints = [0.000 0.000 0.000; 0.536 -0.031 0.000; 1.144 -0.121 0.000; 1.742 -0.246 0.000; 2.386 -0.403 0.000; 2.960 -0.548 0.000; 3.630 -0.702 0.000; 4.126 -0.798 0.000; 4.666 -0.880 0.000; 5.241 -0.937 0.000; 5.854 -0.963 0.000; 6.503 -0.950 0.000; 7.176 -0.891 0.000; 7.882 -0.778 0.000; 8.605 -0.607 0.000; 9.342 -0.373 0.000; 10.097 -0.066 0.000; 10.848 0.311 0.000; 11.578 0.757 0.000];
speed = [0.000; 1.045; 1.430; 1.582; 1.810; 2.142; 2.462; 2.618; 2.808; 2.967; 3.145; 3.348; 3.482; 3.633; 3.823; 3.957; 4.160; 4.250; 4.367];
waittime = [6.200; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000];
trajectory(egoVehicle, waypoints, speed, waittime);
end
