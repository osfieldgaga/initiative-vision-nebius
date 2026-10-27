function [scenario, egoVehicle] = ev_c23_stop_sign(speedup)
%EV_C23_STOP_SIGN stop_sign  full_stop at 296.0-304.4 s, from a real drive.
%   ev_c23_stop_sign                      plays it in a figure (no output requested)
%   ev_c23_stop_sign(4)                   plays it 4x faster
%   scenario = ev_c23_stop_sign();        returns it without playing
%   drivingScenarioDesigner(ev_c23_stop_sign())
%
%   Drive 20261022T164127Z-084b, drive time 293.0-307.4 s (the event +/- 3 s).
%   Event (agent verdict: confirmed, validator: passed, hand label: row 22 agrees): type stop_sign, side -,
%   detail full_stop, 296.04-304.41 s. Agent's reason (not validated): The stop sign was detected at 296.04 s, the car decelerated to 0 mph and remained stopped until at least 304.41 s, indicating a full stop.
%   Validated claims:
%   seq 4507 vision_stop_sign = true  (frame 00004507_4845310720000.jpg, CAN row 4845306061240)
%   seq 4592 mph = 0.0  (frame 00004592_4851274309000.jpg, CAN row 4851272192169)
%   seq 4528 standstill = true  (frame 00004528_4846643357000.jpg, CAN row 4846639714357)
%   seq 4627 standstill = true  (frame 00004627_4853673059000.jpg, CAN row 4853671979832)
%
%   Ego: the car's speed profile (CAN front wheel speed) along its path (CAN yaw rate, calibrated
%   (raw - 2.5) * 0.112 deg/s), starting at the origin facing +x. Road: two 3.5 m
%   lanes along the path, ego in the right lane. Made by src/scripts/export_matlab.py.

if nargin < 1, speedup = 1; end
scenario = drivingScenario('SampleTime', 0.1);  % runs until the ego's trajectory ends (14.4 s of drive)

roadCenters = [0.000 1.750 0.000; 4.116 1.780 0.000; 8.276 1.834 0.000; 12.336 1.788 0.000; 16.448 1.654 0.000; 20.309 1.717 0.000; 25.308 1.799 0.000];
road(scenario, roadCenters, 'Lanes', lanespec([1 1], 'Width', 3.5), 'Name', 'Road');

egoVehicle = vehicle(scenario, 'ClassID', 1, 'Position', [0.000 0.000 0], 'Name', 'Ego');
waypoints = [0.000 0.000 0.000; 0.941 0.002 0.000; 1.828 0.006 0.000; 2.672 0.014 0.000; 3.435 0.022 0.000; 4.138 0.031 0.000; 4.771 0.039 0.000; 5.334 0.047 0.000; 5.866 0.055 0.000; 6.369 0.062 0.000; 7.099 0.071 0.000; 7.814 0.080 0.000; 8.524 0.085 0.000; 9.230 0.085 0.000; 9.930 0.077 0.000; 10.621 0.066 0.000; 11.297 0.055 0.000; 11.939 0.044 0.000; 12.483 0.035 0.000; 12.996 0.025 0.000; 13.623 0.010 0.000; 14.191 -0.006 0.000; 14.746 -0.026 0.000; 15.326 -0.049 0.000; 15.892 -0.073 0.000; 16.475 -0.098 0.000; 16.978 -0.120 0.000; 17.300 -0.133 0.000; 17.901 -0.156 0.000; 18.565 -0.165 0.000; 19.229 -0.147 0.000; 19.996 -0.088 0.000; 20.579 -0.012 0.000; 21.202 0.103 0.000; 21.882 0.272 0.000];
speed = [4.842; 4.531; 4.293; 3.995; 3.637; 3.322; 2.967; 2.682; 2.596; 2.466; 2.419; 2.363; 2.350; 2.358; 2.307; 2.294; 2.220; 1.896; 1.741; 1.680; 1.464; 1.382; 1.413; 1.447; 1.304; 0.985; 0.687; 0.000; 1.443; 2.004; 2.341; 2.760; 3.045; 3.386; 3.633];
waittime = [0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 3.084; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000];
trajectory(egoVehicle, waypoints, speed, waittime);

if nargout == 0  % called on its own (or with Run): show it
    driveStart = 293.04;  % drive time (s) at the scenario's start
    eventTimes = [296.04 304.41];
    eventNames = {'c23 stop_sign full_stop'};
    plot(scenario, 'Waypoints', 'on');
    ax = gca;
    chasePlot(egoVehicle);
    frame = tic;
    while advance(scenario)
        t = driveStart + scenario.SimulationTime;
        now = eventNames(eventTimes(:, 1) <= t & t <= eventTimes(:, 2));
        title(ax, sprintf('drive %.1f s   %.0f km/h   %s', t, 3.6 * norm(egoVehicle.Velocity), strjoin(now, ', ')), ...
              'Interpreter', 'none');
        pause(max(scenario.SampleTime / speedup - toc(frame), 0.001));  % drawing takes time too
        frame = tic;
    end
    clear scenario egoVehicle  % don't print the object
end
end
