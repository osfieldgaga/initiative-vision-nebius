function [scenario, egoVehicle] = ev_c07_other_stop()
%EV_C07_OTHER_STOP other_stop   at 83.3-91.0 s, from a real drive.
%   scenario = ev_c07_other_stop(); plot(scenario); while advance(scenario), pause(0.05), end
%   drivingScenarioDesigner(ev_c07_other_stop())
%
%   Drive 20261022T164127Z-084b, drive time 80.3-94.0 s (the event +/- 3 s).
%   Event (agent verdict: confirmed, validator: passed): type other_stop, side -,
%   detail -, 83.35-91.02 s. Agent's reason (not validated): The vehicle decelerated to a stop with brake applied and standstill true, and no stop sign was visible, matching an other_stop event.
%   Validated claims:
%   seq 1405 mph = 0.0  (frame 00001405_4639618520000.jpg, CAN row 4639618125361)
%   seq 1405 standstill = true  (frame 00001405_4639618520000.jpg, CAN row 4639618125361)
%   seq 1405 brake = true  (frame 00001405_4639618520000.jpg, CAN row 4639618125361)
%   seq 1396 frame_check = No  (frame 00001396_4638952210000.jpg, CAN row 4638945411272)
%
%   Ego: the car's speed profile (CAN front wheel speed) along its path (CAN yaw rate, calibrated
%   (raw - 2.5) * 0.112 deg/s), starting at the origin facing +x. Road: two 3.5 m
%   lanes along the path, ego in the right lane. Made by src/scripts/export_matlab.py.

scenario = drivingScenario('SampleTime', 0.1);  % runs until the ego's trajectory ends (13.7 s of drive)

roadCenters = [0.000 1.750 0.000; 4.367 1.751 0.000; 8.380 1.762 0.000; 12.624 1.791 0.000; 16.948 1.824 0.000; 21.164 1.849 0.000; 25.190 1.858 0.000; 29.312 1.842 0.000; 33.393 1.803 0.000; 38.393 1.755 0.000];
road(scenario, roadCenters, 'Lanes', lanespec([1 1], 'Width', 3.5), 'Name', 'Road');

egoVehicle = vehicle(scenario, 'ClassID', 1, 'Position', [0.000 0.000 0], 'Name', 'Ego');
waypoints = [0.000 0.000 0.000; 0.868 0.000 0.000; 1.736 0.000 0.000; 2.605 0.000 0.000; 3.478 0.000 0.000; 4.370 0.001 0.000; 5.263 0.002 0.000; 6.155 0.004 0.000; 7.051 0.007 0.000; 7.946 0.010 0.000; 8.830 0.014 0.000; 9.702 0.019 0.000; 10.558 0.025 0.000; 11.401 0.031 0.000; 12.228 0.038 0.000; 13.046 0.044 0.000; 13.836 0.051 0.000; 14.622 0.057 0.000; 15.402 0.063 0.000; 16.182 0.069 0.000; 16.959 0.074 0.000; 17.730 0.079 0.000; 18.502 0.084 0.000; 19.271 0.089 0.000; 20.035 0.093 0.000; 20.795 0.097 0.000; 21.550 0.100 0.000; 22.298 0.104 0.000; 23.039 0.106 0.000; 23.764 0.108 0.000; 24.481 0.108 0.000; 25.188 0.108 0.000; 25.872 0.107 0.000; 26.536 0.105 0.000; 27.167 0.103 0.000; 27.760 0.101 0.000; 28.312 0.098 0.000; 28.823 0.095 0.000; 29.511 0.091 0.000; 30.057 0.086 0.000; 30.673 0.081 0.000; 31.251 0.075 0.000; 31.710 0.070 0.000; 32.302 0.063 0.000; 32.846 0.057 0.000; 33.387 0.053 0.000; 34.026 0.056 0.000; 34.723 0.077 0.000; 35.445 0.124 0.000; 35.951 0.174 0.000; 36.210 0.206 0.000];
speed = [4.341; 4.341; 4.341; 4.341; 4.445; 4.488; 4.458; 4.475; 4.492; 4.436; 4.406; 4.324; 4.250; 4.181; 4.112; 4.052; 3.935; 3.913; 3.888; 3.904; 3.866; 3.857; 3.857; 3.827; 3.814; 3.771; 3.749; 3.715; 3.659; 3.607; 3.563; 3.499; 3.369; 3.279; 3.062; 2.860; 2.704; 2.479; 2.017; 1.672; 1.378; 0.959; 0.000; 1.015; 1.615; 1.883; 2.246; 2.397; 2.497; 2.570; 2.635];
waittime = [0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 1.200; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000];
trajectory(egoVehicle, waypoints, speed, waittime);
end
