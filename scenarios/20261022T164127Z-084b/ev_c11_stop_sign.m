function [scenario, egoVehicle] = ev_c11_stop_sign()
%EV_C11_STOP_SIGN stop_sign  rolling_stop at 170.7-176.1 s, from a real drive.
%   scenario = ev_c11_stop_sign(); plot(scenario); while advance(scenario), pause(0.05), end
%   drivingScenarioDesigner(ev_c11_stop_sign())
%
%   Drive 20261022T164127Z-084b, drive time 167.7-179.1 s (the event +/- 3 s).
%   Event (agent verdict: confirmed, validator: passed): type stop_sign, side -,
%   detail rolling_stop, 170.71-176.07 s. Agent's reason (not validated): Stop sign visible, speed never reached zero, right blinker on.
%   Validated claims:
%   seq 2637 vision_stop_sign = true  (frame 00002637_4719976080000.jpg, CAN row 4719971735937)
%   seq 2637 mph = 8.5  (frame 00002637_4719976080000.jpg, CAN row 4719971735937)
%   seq 2720 mph = 1.1  (frame 00002720_4725339881000.jpg, CAN row 4725323584316)
%   seq 2637 blinker = right  (frame 00002637_4719976080000.jpg, CAN row 4719971735937)
%   seq 2637 frame_check = Yes  (frame 00002637_4719976080000.jpg, CAN row 4719971735937)
%
%   Ego: the car's speed profile (CAN front wheel speed) along its path (CAN yaw rate, calibrated
%   (raw - 2.5) * 0.112 deg/s), starting at the origin facing +x. Road: two 3.5 m
%   lanes along the path, ego in the right lane. Made by src/scripts/export_matlab.py.

scenario = drivingScenario('SampleTime', 0.1);  % runs until the ego's trajectory ends (11.4 s of drive)

roadCenters = [0.000 1.750 0.000; 4.092 1.753 0.000; 8.180 1.748 0.000; 12.453 1.731 0.000; 16.499 1.682 0.000; 20.614 1.632 0.000; 24.647 1.643 0.000; 29.647 1.657 0.000];
road(scenario, roadCenters, 'Lanes', lanespec([1 1], 'Width', 3.5), 'Name', 'Road');

egoVehicle = vehicle(scenario, 'ClassID', 1, 'Position', [0.000 0.000 0], 'Name', 'Ego');
waypoints = [0.000 0.000 0.000; 0.627 0.000 0.000; 1.253 0.001 0.000; 1.852 0.002 0.000; 2.419 0.002 0.000; 2.981 0.003 0.000; 3.540 0.003 0.000; 4.092 0.003 0.000; 4.640 0.003 0.000; 5.181 0.003 0.000; 5.710 0.003 0.000; 6.227 0.002 0.000; 6.737 0.001 0.000; 7.709 -0.001 0.000; 8.634 -0.003 0.000; 9.532 -0.005 0.000; 10.407 -0.008 0.000; 11.245 -0.011 0.000; 12.049 -0.016 0.000; 12.821 -0.022 0.000; 13.557 -0.029 0.000; 14.267 -0.038 0.000; 14.941 -0.046 0.000; 15.576 -0.055 0.000; 16.179 -0.063 0.000; 16.754 -0.072 0.000; 17.289 -0.081 0.000; 17.801 -0.088 0.000; 18.516 -0.097 0.000; 19.167 -0.106 0.000; 19.790 -0.113 0.000; 20.404 -0.117 0.000; 21.011 -0.119 0.000; 21.605 -0.120 0.000; 22.191 -0.119 0.000; 22.729 -0.118 0.000; 23.341 -0.115 0.000; 23.896 -0.112 0.000; 24.418 -0.108 0.000; 24.955 -0.104 0.000; 25.576 -0.099 0.000; 26.137 -0.094 0.000; 26.759 -0.087 0.000; 27.384 -0.078 0.000; 28.085 -0.069 0.000; 28.294 -0.069 0.000];
speed = [6.268; 6.268; 6.268; 5.697; 5.641; 5.598; 5.581; 5.477; 5.468; 5.360; 5.209; 5.140; 5.058; 4.726; 4.535; 4.415; 4.332; 4.095; 3.944; 3.762; 3.590; 3.434; 3.291; 3.110; 2.985; 2.786; 2.579; 2.488; 2.268; 2.121; 2.052; 2.039; 1.991; 1.970; 1.870; 1.698; 1.365; 0.864; 0.540; 0.829; 1.257; 1.520; 1.564; 1.564; 2.086; 2.104];
waittime = [0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000];
trajectory(egoVehicle, waypoints, speed, waittime);
end
