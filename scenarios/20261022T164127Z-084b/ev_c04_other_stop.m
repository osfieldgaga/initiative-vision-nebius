function [scenario, egoVehicle] = ev_c04_other_stop(speedup)
%EV_C04_OTHER_STOP other_stop   at 52.3-57.0 s, from a real drive.
%   ev_c04_other_stop                      plays it in a figure (no output requested)
%   ev_c04_other_stop(4)                   plays it 4x faster
%   scenario = ev_c04_other_stop();        returns it without playing
%   drivingScenarioDesigner(ev_c04_other_stop())
%
%   Drive 20261022T164127Z-084b, drive time 49.3-60.0 s (the event +/- 3 s).
%   Event (agent verdict: corrected, validator: passed, hand label: row 4 agrees): type other_stop, side -,
%   detail -, 52.34-57.00 s. Agent's reason (not validated): The car was stationary (mph 0.0) from the start until around 57.0 s, after which it began moving slowly, so the other_stop ends when motion resumes.
%   Validated claims:
%   seq 818 mph = 0.0  (frame 00000818_4601971957000.jpg, CAN row 4601971941261)
%   seq 818 standstill = true  (frame 00000818_4601971957000.jpg, CAN row 4601971941261)
%   seq 884 mph = 1.2  (frame 00000884_4606269657000.jpg, CAN row 4606269878465)
%   seq 884 standstill = false  (frame 00000884_4606269657000.jpg, CAN row 4606269878465)
%
%   Ego: the car's speed profile (CAN front wheel speed) along its path (CAN yaw rate, calibrated
%   (raw - 2.5) * 0.112 deg/s), starting at the origin facing +x. Road: two 3.5 m
%   lanes along the path, ego in the right lane. Made by src/scripts/export_matlab.py.

if nargin < 1, speedup = 1; end
scenario = drivingScenario('SampleTime', 0.1);  % runs until the ego's trajectory ends (10.7 s of drive)

roadCenters = [0.000 1.750 0.000; 19.939 3.306 0.000];
road(scenario, roadCenters, 'Lanes', lanespec([1 1], 'Width', 3.5), 'Name', 'Road');

egoVehicle = vehicle(scenario, 'ClassID', 1, 'Position', [0.000 0.000 0], 'Name', 'Ego');
waypoints = [0.000 0.000 0.000; 0.535 0.009 0.000; 1.109 0.037 0.000; 1.710 0.085 0.000; 2.266 0.140 0.000; 2.870 0.201 0.000; 3.533 0.263 0.000; 3.891 0.292 0.000];
speed = [0.000; 0.808; 1.054; 1.322; 1.438; 1.603; 1.741; 1.827];
waittime = [6.874; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000];
trajectory(egoVehicle, waypoints, speed, waittime);

if nargout == 0  % called on its own (or with Run): show it
    driveStart = 49.34;  % drive time (s) at the scenario's start
    eventTimes = [52.34 57.00];
    eventNames = {'c04 other_stop'};
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
