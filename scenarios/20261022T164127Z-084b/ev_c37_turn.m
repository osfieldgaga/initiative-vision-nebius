function [scenario, egoVehicle] = ev_c37_turn()
%EV_C37_TURN turn left no_blinker at 444.3-448.0 s, from a real drive.
%   scenario = ev_c37_turn(); plot(scenario); while advance(scenario), pause(0.05), end
%   drivingScenarioDesigner(ev_c37_turn())
%
%   Drive 20261022T164127Z-084b, drive time 441.3-451.0 s (the event +/- 3 s).
%   Event (agent verdict: confirmed, validator: passed): type turn, side left,
%   detail no_blinker, 444.33-448.03 s. Agent's reason (not validated): The steering angle exceeds 90 degrees left from 444.33 s onward, peaking at 504.5°, while the blinker remains off, indicating a left turn without signal.
%   Validated claims:
%   seq 6744 steer = 169.7  (frame 00006744_4993601288000.jpg, CAN row 4993600923566)
%   seq 6782 steer = 504.5  (frame 00006782_4995966759000.jpg, CAN row 4995959808204)
%   seq 6782 blinker = null  (frame 00006782_4995966759000.jpg, CAN row 4995959808204)
%
%   Ego: the car's speed profile (CAN front wheel speed) along its path (CAN yaw rate, calibrated
%   (raw - 2.5) * 0.112 deg/s), starting at the origin facing +x. Road: two 3.5 m
%   lanes along the path, ego in the right lane. Made by src/scripts/export_matlab.py.

scenario = drivingScenario('SampleTime', 0.1);  % runs until the ego's trajectory ends (9.7 s of drive)

roadCenters = [0.000 1.750 0.000; -4.769 21.173 0.000];
road(scenario, roadCenters, 'Lanes', lanespec([1 1], 'Width', 3.5), 'Name', 'Road');

egoVehicle = vehicle(scenario, 'ClassID', 1, 'Position', [0.000 0.000 0], 'Name', 'Ego');
waypoints = [0.000 0.000 0.000; 0.752 0.002 0.000; 1.498 0.005 0.000; 2.230 0.010 0.000; 2.944 0.016 0.000; 3.641 0.024 0.000; 4.327 0.032 0.000; 5.006 0.039 0.000; 5.677 0.045 0.000; 6.334 0.050 0.000; 6.971 0.054 0.000; 7.592 0.059 0.000; 8.200 0.064 0.000; 8.790 0.073 0.000; 9.370 0.090 0.000; 9.929 0.120 0.000; 10.469 0.169 0.000; 11.004 0.247 0.000; 11.529 0.356 0.000; 12.042 0.501 0.000; 12.542 0.685 0.000; 13.036 0.922 0.000; 13.522 1.221 0.000; 13.983 1.584 0.000; 14.392 1.998 0.000; 14.738 2.450 0.000; 15.015 2.929 0.000; 15.218 3.419 0.000; 15.354 3.907 0.000; 15.443 4.627 0.000; 15.423 5.295 0.000; 15.337 5.893 0.000; 15.223 6.408 0.000; 15.088 6.931 0.000; 14.945 7.486 0.000; 14.888 7.719 0.000];
speed = [3.775; 3.758; 3.676; 3.663; 3.490; 3.486; 3.408; 3.365; 3.304; 3.227; 3.140; 3.054; 3.002; 2.933; 2.890; 2.700; 2.717; 2.678; 2.665; 2.648; 2.704; 2.790; 2.924; 2.898; 2.898; 2.795; 2.691; 2.605; 2.492; 2.350; 2.168; 1.905; 1.577; 1.132; 0.760; 0.000];
waittime = [0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 1.400];
trajectory(egoVehicle, waypoints, speed, waittime);
end
