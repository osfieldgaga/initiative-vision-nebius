function [scenario, egoVehicle] = ev_c06_turn()
%EV_C06_TURN turn right no_blinker at 64.4-70.4 s, from a real drive.
%   scenario = ev_c06_turn(); plot(scenario); while advance(scenario), pause(0.05), end
%   drivingScenarioDesigner(ev_c06_turn())
%
%   Drive 20261022T164127Z-084b, drive time 61.4-73.4 s (the event +/- 3 s).
%   Event (agent verdict: confirmed, validator: passed): type turn, side right,
%   detail no_blinker, 64.36-70.36 s. Agent's reason (not validated): The steering wheel turned strongly negative (right) from ~‑98° to ‑427° while speed remained low and blinker stayed off, indicating a right turn without signal.
%   Validated claims:
%   seq 993 steer = -98.2  (frame 00000993_4613632394000.jpg, CAN row 4613631648893)
%   seq 1046 steer = -427.4  (frame 00001046_4617030573000.jpg, CAN row 4617023807936)
%   seq 993 blinker = null  (frame 00000993_4613632394000.jpg, CAN row 4613631648893)
%   seq 1046 blinker = null  (frame 00001046_4617030573000.jpg, CAN row 4617023807936)
%   seq 993 gear = D  (frame 00000993_4613632394000.jpg, CAN row 4613631648893)
%   seq 1046 gear = D  (frame 00001046_4617030573000.jpg, CAN row 4617023807936)
%
%   Ego: the car's speed profile (CAN front wheel speed) along its path (CAN yaw rate, calibrated
%   (raw - 2.5) * 0.112 deg/s), starting at the origin facing +x. Road: two 3.5 m
%   lanes along the path, ego in the right lane. Made by src/scripts/export_matlab.py.

scenario = drivingScenario('SampleTime', 0.1);  % runs until the ego's trajectory ends (12.0 s of drive)

roadCenters = [0.000 1.750 0.000; 4.288 1.455 0.000; 9.008 -0.618 0.000; 11.394 -5.447 0.000; 11.133 -10.232 0.000; 10.251 -14.528 0.000; 9.336 -18.642 0.000; 8.251 -23.523 0.000];
road(scenario, roadCenters, 'Lanes', lanespec([1 1], 'Width', 3.5), 'Name', 'Road');

egoVehicle = vehicle(scenario, 'ClassID', 1, 'Position', [0.000 0.000 0], 'Name', 'Ego');
waypoints = [0.000 0.000 0.000; 0.513 -0.004 0.000; 1.069 -0.018 0.000; 1.571 -0.039 0.000; 2.145 -0.073 0.000; 2.707 -0.117 0.000; 3.216 -0.167 0.000; 3.777 -0.238 0.000; 4.402 -0.343 0.000; 4.988 -0.476 0.000; 5.485 -0.618 0.000; 6.004 -0.803 0.000; 6.512 -1.025 0.000; 7.009 -1.296 0.000; 7.498 -1.632 0.000; 7.980 -2.057 0.000; 8.429 -2.570 0.000; 8.831 -3.170 0.000; 9.065 -3.613 0.000; 9.266 -4.088 0.000; 9.433 -4.590 0.000; 9.564 -5.121 0.000; 9.660 -5.680 0.000; 9.717 -6.258 0.000; 9.737 -6.851 0.000; 9.721 -7.457 0.000; 9.676 -8.067 0.000; 9.606 -8.680 0.000; 9.516 -9.302 0.000; 9.411 -9.923 0.000; 9.293 -10.555 0.000; 9.167 -11.199 0.000; 9.036 -11.847 0.000; 8.900 -12.500 0.000; 8.759 -13.158 0.000; 8.615 -13.818 0.000; 8.468 -14.488 0.000; 8.318 -15.165 0.000; 8.167 -15.843 0.000; 8.016 -16.526 0.000; 7.861 -17.219 0.000; 7.706 -17.912 0.000; 7.628 -18.261 0.000];
speed = [1.382; 1.097; 0.834; 0.894; 0.946; 0.959; 1.101; 1.149; 1.404; 1.641; 1.819; 1.819; 1.853; 1.935; 2.069; 2.168; 2.380; 2.441; 2.549; 2.605; 2.700; 2.790; 2.864; 2.937; 2.980; 3.062; 3.062; 3.110; 3.149; 3.149; 3.252; 3.304; 3.317; 3.339; 3.378; 3.408; 3.460; 3.477; 3.469; 3.546; 3.559; 3.559; 3.594];
waittime = [0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000];
trajectory(egoVehicle, waypoints, speed, waittime);
end
