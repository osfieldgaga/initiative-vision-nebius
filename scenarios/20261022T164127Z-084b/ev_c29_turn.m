function [scenario, egoVehicle] = ev_c29_turn(speedup)
%EV_C29_TURN turn left blinker at 376.4-380.0 s, from a real drive.
%   ev_c29_turn                      plays it in a figure (no output requested)
%   ev_c29_turn(4)                   plays it 4x faster
%   scenario = ev_c29_turn();        returns it without playing
%   drivingScenarioDesigner(ev_c29_turn())
%
%   Drive 20261022T164127Z-084b, drive time 373.4-383.0 s (the event +/- 3 s).
%   Event (agent verdict: confirmed, validator: passed, hand label: row 28 agrees): type turn, side left,
%   detail blinker, 376.37-380.00 s. Agent's reason (not validated): The steering angle exceeds 90° left at the start and the left blinker is on before and during the turn, matching a left turn with blinker.
%   Validated claims:
%   seq 5711 steer = 90.9  (frame 00005711_4925636088000.jpg, CAN row 4925631732900)
%   seq 5711 blinker = left  (frame 00005711_4925636088000.jpg, CAN row 4925631732900)
%   seq 5748 blinker = left  (frame 00005748_4928268009000.jpg, CAN row 4928263709385)
%   seq 5754 blinker = null  (frame 00005754_4928634479000.jpg, CAN row 4928632426514)
%
%   Ego: the car's speed profile (CAN front wheel speed) along its path (CAN yaw rate, calibrated
%   (raw - 2.5) * 0.112 deg/s), starting at the origin facing +x. Road: two 3.5 m
%   lanes along the path, ego in the right lane. Made by src/scripts/export_matlab.py.

if nargin < 1, speedup = 1; end
scenario = drivingScenario('SampleTime', 0.1);  % runs until the ego's trajectory ends (9.6 s of drive)

roadCenters = [0.000 1.750 0.000; 4.768 1.641 0.000; 9.037 1.384 0.000; 13.232 1.022 0.000; 17.531 0.633 0.000; 21.348 0.751 0.000; 24.534 2.086 0.000; 26.849 4.696 0.000; 28.066 8.132 0.000; 28.351 11.835 0.000; 28.049 15.977 0.000; 27.467 20.422 0.000; 26.844 24.386 0.000; 26.069 29.325 0.000];
road(scenario, roadCenters, 'Lanes', lanespec([1 1], 'Width', 3.5), 'Name', 'Road');

egoVehicle = vehicle(scenario, 'ClassID', 1, 'Position', [0.000 0.000 0], 'Name', 'Ego');
waypoints = [0.000 0.000 0.000; 0.802 -0.003 0.000; 1.597 -0.014 0.000; 2.385 -0.029 0.000; 3.167 -0.051 0.000; 3.937 -0.077 0.000; 4.692 -0.108 0.000; 5.440 -0.142 0.000; 6.179 -0.180 0.000; 6.888 -0.221 0.000; 7.572 -0.265 0.000; 8.244 -0.311 0.000; 8.903 -0.361 0.000; 9.550 -0.411 0.000; 10.180 -0.463 0.000; 10.792 -0.514 0.000; 11.385 -0.566 0.000; 11.962 -0.618 0.000; 12.523 -0.669 0.000; 13.067 -0.721 0.000; 13.595 -0.771 0.000; 14.112 -0.820 0.000; 14.619 -0.869 0.000; 15.585 -0.961 0.000; 16.510 -1.043 0.000; 17.411 -1.113 0.000; 18.303 -1.165 0.000; 19.169 -1.188 0.000; 20.023 -1.169 0.000; 20.865 -1.097 0.000; 21.686 -0.966 0.000; 22.489 -0.777 0.000; 23.270 -0.530 0.000; 24.039 -0.214 0.000; 24.803 0.182 0.000; 25.548 0.660 0.000; 26.267 1.226 0.000; 26.945 1.876 0.000; 27.566 2.607 0.000; 28.122 3.411 0.000; 28.608 4.277 0.000; 28.828 4.735 0.000; 29.033 5.216 0.000; 29.222 5.714 0.000; 29.392 6.224 0.000; 29.543 6.742 0.000; 29.674 7.270 0.000; 29.785 7.807 0.000; 29.880 8.360 0.000; 29.957 8.927 0.000; 30.017 9.500 0.000; 30.061 10.079 0.000; 30.089 10.665 0.000; 30.102 11.259 0.000; 30.101 11.859 0.000; 30.087 12.462 0.000; 30.060 13.073 0.000; 30.023 13.687 0.000; 29.976 14.304 0.000; 29.921 14.924 0.000; 29.857 15.550 0.000; 29.787 16.179 0.000; 29.712 16.811 0.000; 29.633 17.443 0.000; 29.551 18.079 0.000; 29.467 18.717 0.000; 29.381 19.359 0.000; 29.291 20.013 0.000; 29.199 20.669 0.000; 29.104 21.326 0.000; 29.005 21.990 0.000; 28.902 22.656 0.000; 28.795 23.327 0.000; 28.684 24.003 0.000; 28.569 24.682 0.000; 28.451 25.363 0.000; 28.328 26.047 0.000; 28.203 26.733 0.000; 28.073 27.419 0.000];
speed = [8.073; 7.974; 7.918; 7.853; 7.784; 7.624; 7.499; 7.477; 7.322; 6.885; 6.820; 6.656; 6.557; 6.414; 6.242; 6.030; 5.874; 5.719; 5.551; 5.373; 5.231; 5.162; 5.015; 4.730; 4.561; 4.492; 4.384; 4.289; 4.263; 4.173; 4.129; 4.095; 4.078; 4.220; 4.371; 4.492; 4.613; 4.751; 4.846; 4.941; 4.976; 5.183; 5.278; 5.373; 5.373; 5.421; 5.460; 5.507; 5.702; 5.740; 5.784; 5.831; 5.905; 5.991; 5.991; 6.086; 6.134; 6.177; 6.190; 6.276; 6.306; 6.354; 6.358; 6.393; 6.432; 6.432; 6.527; 6.669; 6.587; 6.686; 6.734; 6.756; 6.820; 6.881; 6.894; 6.937; 6.959; 6.984; 6.984];
waittime = [0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000];
trajectory(egoVehicle, waypoints, speed, waittime);

if nargout == 0  % called on its own (or with Run): show it
    driveStart = 373.37;  % drive time (s) at the scenario's start
    eventTimes = [376.37 380.00];
    eventNames = {'c29 turn left blinker'};
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
