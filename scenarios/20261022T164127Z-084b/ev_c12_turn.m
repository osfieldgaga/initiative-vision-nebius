function [scenario, egoVehicle] = ev_c12_turn()
%EV_C12_TURN turn right blinker at 179.0-182.3 s, from a real drive.
%   scenario = ev_c12_turn(); plot(scenario); while advance(scenario), pause(0.05), end
%   drivingScenarioDesigner(ev_c12_turn())
%
%   Drive 20261022T164127Z-084b, drive time 176.0-185.3 s (the event +/- 3 s).
%   Event (agent verdict: confirmed, validator: passed): type turn, side right,
%   detail blinker, 179.04-182.34 s. Agent's reason (not validated): The steering wheel turned right (negative values) from ~179 s to ~182 s while the right blinker was on before steering began and stayed on until shortly after the wheel returned toward centre, matching a right turn with proper blinker use.
%   Validated claims:
%   seq 2771 steer = -124.4  (frame 00002771_4728304994000.jpg, CAN row 4728291746222)
%   seq 2771 blinker = right  (frame 00002771_4728304994000.jpg, CAN row 4728291746222)
%   seq 2794 steer = -428.8  (frame 00002794_4729970787000.jpg, CAN row 4729967740655)
%   seq 2794 blinker = right  (frame 00002794_4729970787000.jpg, CAN row 4729967740655)
%   seq 2820 steer = -163.1  (frame 00002820_4731603269000.jpg, CAN row 4731601726528)
%   seq 2820 blinker = null  (frame 00002820_4731603269000.jpg, CAN row 4731601726528)
%
%   Ego: the car's speed profile (CAN front wheel speed) along its path (CAN yaw rate, calibrated
%   (raw - 2.5) * 0.112 deg/s), starting at the origin facing +x. Road: two 3.5 m
%   lanes along the path, ego in the right lane. Made by src/scripts/export_matlab.py.

scenario = drivingScenario('SampleTime', 0.1);  % runs until the ego's trajectory ends (9.3 s of drive)

roadCenters = [0.000 1.750 0.000; 4.254 1.752 0.000; 9.264 0.077 0.000; 11.843 -4.421 0.000; 12.160 -9.156 0.000; 11.986 -13.753 0.000; 11.729 -18.297 0.000; 11.446 -23.289 0.000];
road(scenario, roadCenters, 'Lanes', lanespec([1 1], 'Width', 3.5), 'Name', 'Road');

egoVehicle = vehicle(scenario, 'ClassID', 1, 'Position', [0.000 0.000 0], 'Name', 'Ego');
waypoints = [0.000 0.000 0.000; 0.549 0.000 0.000; 1.068 0.002 0.000; 1.615 0.003 0.000; 2.235 0.006 0.000; 2.860 0.010 0.000; 3.560 0.015 0.000; 4.191 0.003 0.000; 4.867 -0.039 0.000; 5.567 -0.130 0.000; 6.272 -0.294 0.000; 6.745 -0.456 0.000; 7.221 -0.668 0.000; 7.693 -0.939 0.000; 8.152 -1.274 0.000; 8.586 -1.677 0.000; 8.988 -2.149 0.000; 9.360 -2.710 0.000; 9.678 -3.336 0.000; 9.934 -4.024 0.000; 10.131 -4.782 0.000; 10.266 -5.580 0.000; 10.350 -6.415 0.000; 10.395 -7.288 0.000; 10.412 -8.195 0.000; 10.410 -9.139 0.000; 10.394 -10.105 0.000; 10.363 -11.087 0.000; 10.343 -11.588 0.000; 10.319 -12.097 0.000; 10.294 -12.614 0.000; 10.266 -13.132 0.000; 10.238 -13.658 0.000; 10.209 -14.197 0.000; 10.179 -14.743 0.000; 10.148 -15.301 0.000; 10.117 -15.864 0.000; 10.085 -16.433 0.000; 10.052 -17.012 0.000; 10.018 -17.598 0.000; 9.982 -18.188 0.000; 9.944 -18.784 0.000; 9.903 -19.390 0.000; 9.858 -20.005 0.000; 9.808 -20.627 0.000; 9.755 -21.255 0.000];
speed = [0.540; 0.851; 1.231; 1.490; 1.564; 1.564; 2.086; 2.104; 2.311; 2.406; 2.436; 2.574; 2.669; 2.769; 2.911; 3.019; 3.201; 3.469; 3.555; 3.849; 3.970; 4.116; 4.289; 4.449; 4.630; 4.786; 4.868; 4.976; 5.054; 5.153; 5.188; 5.188; 5.356; 5.429; 5.516; 5.654; 5.633; 5.758; 5.844; 5.896; 5.931; 6.013; 6.125; 6.220; 6.250; 6.358];
waittime = [0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000];
trajectory(egoVehicle, waypoints, speed, waittime);
end
