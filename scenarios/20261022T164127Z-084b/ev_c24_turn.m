function [scenario, egoVehicle] = ev_c24_turn(speedup)
%EV_C24_TURN turn left blinker at 306.0-310.0 s, from a real drive.
%   ev_c24_turn                      plays it in a figure (no output requested)
%   ev_c24_turn(4)                   plays it 4x faster
%   scenario = ev_c24_turn();        returns it without playing
%   drivingScenarioDesigner(ev_c24_turn())
%
%   Drive 20261022T164127Z-084b, drive time 303.0-313.0 s (the event +/- 3 s).
%   Event (agent verdict: confirmed, validator: passed, hand label: row 23 agrees): type turn, side left,
%   detail blinker, 306.04-310.04 s. Agent's reason (not validated): The candidate shows a left turn with steering exceeding 90° and left blinker activated before steering began, matching a turn event.
%   Validated claims:
%   seq 4654 steer = 147.8  (frame 00004654_4855638711000.jpg, CAN row 4855638861885)
%   seq 4654 blinker = left  (frame 00004654_4855638711000.jpg, CAN row 4855638861885)
%   seq 4695 blinker = null  (frame 00004695_4858470584000.jpg, CAN row 4858470973101)
%   seq 4695 steer = 162.0  (frame 00004695_4858470584000.jpg, CAN row 4858470973101)
%
%   Ego: the car's speed profile (CAN front wheel speed) along its path (CAN yaw rate, calibrated
%   (raw - 2.5) * 0.112 deg/s), starting at the origin facing +x. Road: two 3.5 m
%   lanes along the path, ego in the right lane. Made by src/scripts/export_matlab.py.

if nargin < 1, speedup = 1; end
scenario = drivingScenario('SampleTime', 0.1);  % runs until the ego's trajectory ends (10.0 s of drive)

roadCenters = [0.000 1.750 0.000; 3.713 2.171 0.000; 6.862 3.923 0.000; 9.021 6.878 0.000; 10.245 10.794 0.000; 10.621 14.554 0.000; 10.527 18.787 0.000; 9.968 23.400 0.000; 9.203 27.482 0.000; 8.308 31.714 0.000; 7.274 36.606 0.000];
road(scenario, roadCenters, 'Lanes', lanespec([1 1], 'Width', 3.5), 'Name', 'Road');

egoVehicle = vehicle(scenario, 'ClassID', 1, 'Position', [0.000 0.000 0], 'Name', 'Ego');
waypoints = [0.000 0.000 0.000; 0.585 0.003 0.000; 1.249 0.021 0.000; 1.912 0.067 0.000; 2.676 0.158 0.000; 3.255 0.259 0.000; 3.873 0.400 0.000; 4.545 0.598 0.000; 5.238 0.857 0.000; 5.945 1.187 0.000; 6.660 1.594 0.000; 7.354 2.069 0.000; 8.027 2.618 0.000; 8.678 3.253 0.000; 9.291 3.975 0.000; 9.857 4.780 0.000; 10.363 5.652 0.000; 10.600 6.123 0.000; 10.822 6.609 0.000; 11.028 7.108 0.000; 11.222 7.627 0.000; 11.402 8.168 0.000; 11.568 8.727 0.000; 11.717 9.298 0.000; 11.850 9.882 0.000; 11.967 10.487 0.000; 12.070 11.115 0.000; 12.160 11.770 0.000; 12.236 12.442 0.000; 12.296 13.118 0.000; 12.341 13.802 0.000; 12.370 14.500 0.000; 12.386 15.207 0.000; 12.389 15.926 0.000; 12.379 16.659 0.000; 12.357 17.398 0.000; 12.321 18.147 0.000; 12.272 18.913 0.000; 12.209 19.691 0.000; 12.132 20.483 0.000; 12.042 21.279 0.000; 11.938 22.074 0.000; 11.823 22.873 0.000; 11.695 23.684 0.000; 11.556 24.503 0.000; 11.408 25.326 0.000; 11.251 26.155 0.000; 11.088 26.990 0.000; 10.918 27.831 0.000; 10.744 28.677 0.000; 10.566 29.527 0.000; 10.385 30.377 0.000; 10.202 31.229 0.000; 10.019 32.081 0.000; 9.836 32.936 0.000];
speed = [0.000; 1.443; 2.004; 2.341; 2.760; 3.045; 3.386; 3.633; 3.784; 4.052; 4.173; 4.250; 4.415; 4.626; 4.881; 4.963; 5.218; 5.317; 5.373; 5.425; 5.663; 5.749; 5.909; 5.892; 6.077; 6.246; 6.492; 6.730; 6.790; 6.790; 6.924; 7.041; 7.101; 7.278; 7.391; 7.391; 7.615; 7.719; 7.900; 8.013; 8.017; 8.017; 8.129; 8.276; 8.341; 8.388; 8.479; 8.548; 8.613; 8.665; 8.691; 8.704; 8.708; 8.734; 8.760];
waittime = [1.989; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000];
trajectory(egoVehicle, waypoints, speed, waittime);

if nargout == 0  % called on its own (or with Run): show it
    driveStart = 303.04;  % drive time (s) at the scenario's start
    eventTimes = [306.04 310.04];
    eventNames = {'c24 turn left blinker'};
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
