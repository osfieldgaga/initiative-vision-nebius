function [scenario, egoVehicle] = ev_c02_turn()
%EV_C02_TURN turn left no_blinker at 33.7-35.4 s, from a real drive.
%   scenario = ev_c02_turn(); plot(scenario); while advance(scenario), pause(0.05), end
%   drivingScenarioDesigner(ev_c02_turn())
%
%   Drive 20261022T164127Z-084b, drive time 30.7-38.4 s (the event +/- 3 s).
%   Event (agent verdict: confirmed, validator: passed): type turn, side left,
%   detail no_blinker, 33.68-35.35 s. Agent's reason (not validated): The steering wheel turned left past 90° and returned to center while the left blinker was off, indicating a left turn without signaling.
%   Validated claims:
%   seq 542 steer = 152.8  (frame 00000542_4583281991000.jpg, CAN row 4583281790324)
%   seq 542 blinker = null  (frame 00000542_4583281991000.jpg, CAN row 4583281790324)
%   seq 542 gear = D  (frame 00000542_4583281991000.jpg, CAN row 4583281790324)
%   seq 542 mph = 3.8  (frame 00000542_4583281991000.jpg, CAN row 4583281790324)
%
%   Ego: the car's speed profile (CAN front wheel speed) along its path (CAN yaw rate, calibrated
%   (raw - 2.5) * 0.112 deg/s), starting at the origin facing +x. Road: two 3.5 m
%   lanes along the path, ego in the right lane. Made by src/scripts/export_matlab.py.

scenario = drivingScenario('SampleTime', 0.1);  % runs until the ego's trajectory ends (7.7 s of drive)

roadCenters = [0.000 1.750 0.000; 19.439 6.453 0.000];
road(scenario, roadCenters, 'Lanes', lanespec([1 1], 'Width', 3.5), 'Name', 'Road');

egoVehicle = vehicle(scenario, 'ClassID', 1, 'Position', [0.000 0.000 0], 'Name', 'Ego');
waypoints = [0.000 0.000 0.000; 0.571 0.003 0.000; 1.169 0.012 0.000; 1.725 0.028 0.000; 2.330 0.055 0.000; 2.981 0.108 0.000; 3.498 0.171 0.000; 4.031 0.256 0.000; 4.584 0.363 0.000; 5.149 0.488 0.000; 5.723 0.632 0.000; 6.313 0.793 0.000; 6.908 0.966 0.000; 7.506 1.147 0.000; 8.102 1.332 0.000; 8.691 1.516 0.000; 9.276 1.699 0.000; 9.869 1.881 0.000; 10.470 2.052 0.000; 11.083 2.208 0.000];
speed = [0.000; 1.119; 1.335; 1.464; 1.572; 1.685; 1.767; 1.849; 1.909; 1.939; 2.022; 2.060; 2.065; 2.091; 2.079; 2.043; 2.039; 2.069; 2.095; 2.130];
waittime = [1.200; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000];
trajectory(egoVehicle, waypoints, speed, waittime);
end
