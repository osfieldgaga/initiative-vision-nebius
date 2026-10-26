function [scenario, egoVehicle] = ev_c22_turn()
%EV_C22_TURN turn left no_blinker at 276.1-279.7 s, from a real drive.
%   scenario = ev_c22_turn(); plot(scenario); while advance(scenario), pause(0.05), end
%   drivingScenarioDesigner(ev_c22_turn())
%
%   Drive 20261022T164127Z-084b, drive time 273.1-282.7 s (the event +/- 3 s).
%   Event (agent verdict: confirmed, validator: passed): type turn, side left,
%   detail no_blinker, 276.05-279.72 s. Agent's reason (not validated): The steering wheel turned left beyond 150 degrees and gradually returned toward center, indicating a left turn maneuver with no blinker activation.
%   Validated claims:
%   seq 4239 steer = 505.7  (frame 00004239_4826620394000.jpg, CAN row 4826619759185)
%   seq 4239 blinker = null  (frame 00004239_4826620394000.jpg, CAN row 4826619759185)
%   seq 4239 gear = D  (frame 00004239_4826620394000.jpg, CAN row 4826619759185)
%   seq 4239 mph = 4.5  (frame 00004239_4826620394000.jpg, CAN row 4826619759185)
%   seq 4219 steer = 158.2  (frame 00004219_4825321068000.jpg, CAN row 4825311605862)
%   seq 4273 steer = 163.1  (frame 00004273_4828985838000.jpg, CAN row 4828982625363)
%
%   Ego: the car's speed profile (CAN front wheel speed) along its path (CAN yaw rate, calibrated
%   (raw - 2.5) * 0.112 deg/s), starting at the origin facing +x. Road: two 3.5 m
%   lanes along the path, ego in the right lane. Made by src/scripts/export_matlab.py.

scenario = drivingScenario('SampleTime', 0.1);  % runs until the ego's trajectory ends (9.7 s of drive)

roadCenters = [0.000 1.750 0.000; 2.182 2.802 0.000; 2.628 5.078 0.000; 0.817 7.792 0.000; -2.088 10.512 0.000; -5.039 13.409 0.000; -8.056 16.868 0.000; -10.734 20.070 0.000; -13.943 23.904 0.000];
road(scenario, roadCenters, 'Lanes', lanespec([1 1], 'Width', 3.5), 'Name', 'Road');

egoVehicle = vehicle(scenario, 'ClassID', 1, 'Position', [0.000 0.000 0], 'Name', 'Ego');
waypoints = [0.000 0.000 0.000; 0.552 0.034 0.000; 1.064 0.132 0.000; 1.634 0.321 0.000; 2.085 0.534 0.000; 2.583 0.829 0.000; 3.104 1.235 0.000; 3.545 1.704 0.000; 3.837 2.114 0.000; 4.100 2.605 0.000; 4.315 3.194 0.000; 4.447 3.841 0.000; 4.476 4.520 0.000; 4.396 5.208 0.000; 4.202 5.896 0.000; 3.898 6.589 0.000; 3.488 7.290 0.000; 2.981 7.986 0.000; 2.394 8.671 0.000; 1.740 9.347 0.000; 1.035 10.024 0.000; 0.665 10.366 0.000; 0.287 10.712 0.000; -0.100 11.063 0.000; -0.496 11.424 0.000; -0.899 11.795 0.000; -1.304 12.173 0.000; -1.706 12.554 0.000; -2.105 12.938 0.000; -2.502 13.324 0.000; -2.915 13.735 0.000; -3.344 14.170 0.000; -3.769 14.613 0.000; -4.193 15.067 0.000; -4.617 15.530 0.000; -5.035 16.000 0.000; -5.451 16.480 0.000; -5.864 16.967 0.000; -6.282 17.468 0.000; -6.705 17.981 0.000; -7.138 18.505 0.000; -7.583 19.041 0.000; -8.030 19.577 0.000; -8.482 20.117 0.000; -8.940 20.660 0.000; -9.402 21.204 0.000];
speed = [1.421; 1.322; 1.292; 1.067; 0.000; 1.287; 1.965; 2.384; 2.596; 3.032; 3.244; 3.369; 3.451; 3.520; 3.624; 3.922; 4.177; 4.402; 4.613; 4.777; 5.011; 5.067; 5.166; 5.296; 5.421; 5.537; 5.537; 5.537; 5.537; 5.537; 6.112; 6.116; 6.155; 6.276; 6.276; 6.311; 6.384; 6.384; 6.656; 6.656; 6.941; 6.980; 6.993; 7.093; 7.097; 7.192];
waittime = [0.000; 0.000; 0.000; 0.000; 1.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000];
trajectory(egoVehicle, waypoints, speed, waittime);
end
