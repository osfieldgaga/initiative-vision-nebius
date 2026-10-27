function [scenario, egoVehicle] = ev_c14_turn(speedup)
%EV_C14_TURN turn right blinker at 243.7-245.3 s, from a real drive.
%   ev_c14_turn                      plays it in a figure (no output requested)
%   ev_c14_turn(4)                   plays it 4x faster
%   scenario = ev_c14_turn();        returns it without playing
%   drivingScenarioDesigner(ev_c14_turn())
%
%   Drive 20261022T164127Z-084b, drive time 240.7-248.3 s (the event +/- 3 s).
%   Event (agent verdict: confirmed, validator: passed, hand label: row 14 agrees): type turn, side right,
%   detail blinker, 243.70-245.34 s. Agent's reason (not validated): The steer angle went negative (>90 deg magnitude) indicating a right turn, and the right blinker was on before steering began and remained on during the early part of the turn.
%   Validated claims:
%   seq 3745 blinker = right  (frame 00003745_4792971198000.jpg, CAN row 4792929923114)
%   seq 3745 steer = -278.8  (frame 00003745_4792971198000.jpg, CAN row 4792929923114)
%   seq 3749 steer = -285.0  (frame 00003749_4793271044000.jpg, CAN row 4793269858652)
%   seq 3762 blinker = null  (frame 00003762_4794303843000.jpg, CAN row 4794297082197)
%
%   Ego: the car's speed profile (CAN front wheel speed) along its path (CAN yaw rate, calibrated
%   (raw - 2.5) * 0.112 deg/s), starting at the origin facing +x. Road: two 3.5 m
%   lanes along the path, ego in the right lane. Made by src/scripts/export_matlab.py.

if nargin < 1, speedup = 1; end
scenario = drivingScenario('SampleTime', 0.1);  % runs until the ego's trajectory ends (7.6 s of drive)

roadCenters = [0.000 1.750 0.000; 4.090 1.733 0.000; 8.498 1.552 0.000; 12.886 1.133 0.000; 17.246 0.479 0.000; 21.899 -0.943 0.000; 25.394 -4.011 0.000; 28.016 -7.885 0.000; 30.014 -11.953 0.000; 31.526 -15.902 0.000; 33.313 -20.572 0.000];
road(scenario, roadCenters, 'Lanes', lanespec([1 1], 'Width', 3.5), 'Name', 'Road');

egoVehicle = vehicle(scenario, 'ClassID', 1, 'Position', [0.000 0.000 0], 'Name', 'Ego');
waypoints = [0.000 0.000 0.000; 0.722 -0.000 0.000; 1.426 -0.001 0.000; 2.112 -0.002 0.000; 2.780 -0.004 0.000; 3.431 -0.009 0.000; 4.064 -0.016 0.000; 4.684 -0.028 0.000; 5.300 -0.044 0.000; 5.916 -0.064 0.000; 6.532 -0.090 0.000; 7.148 -0.120 0.000; 7.763 -0.155 0.000; 8.378 -0.194 0.000; 8.993 -0.238 0.000; 9.608 -0.287 0.000; 10.222 -0.341 0.000; 10.835 -0.400 0.000; 11.448 -0.463 0.000; 12.061 -0.531 0.000; 12.673 -0.604 0.000; 13.285 -0.681 0.000; 13.896 -0.763 0.000; 14.506 -0.850 0.000; 15.115 -0.941 0.000; 15.724 -1.037 0.000; 16.332 -1.138 0.000; 16.940 -1.244 0.000; 17.546 -1.354 0.000; 18.152 -1.469 0.000; 18.755 -1.595 0.000; 19.243 -1.717 0.000; 19.981 -1.962 0.000; 20.689 -2.278 0.000; 21.361 -2.663 0.000; 22.002 -3.117 0.000; 22.621 -3.633 0.000; 23.214 -4.201 0.000; 23.774 -4.807 0.000; 24.308 -5.453 0.000; 24.818 -6.133 0.000; 25.317 -6.852 0.000; 25.797 -7.590 0.000; 26.266 -8.356 0.000; 26.723 -9.156 0.000; 27.163 -9.983 0.000; 27.591 -10.843 0.000; 28.004 -11.730 0.000; 28.404 -12.639 0.000; 28.600 -13.105 0.000; 28.792 -13.576 0.000; 28.980 -14.049 0.000; 29.164 -14.523 0.000; 29.345 -15.004 0.000; 29.523 -15.488 0.000; 29.699 -15.979 0.000; 29.872 -16.474 0.000; 30.042 -16.974 0.000; 30.212 -17.481 0.000; 30.377 -17.991 0.000];
speed = [7.322; 7.123; 6.950; 6.769; 6.600; 6.419; 6.242; 6.164; 6.164; 6.164; 6.164; 6.164; 6.164; 6.164; 6.164; 6.164; 6.164; 6.164; 6.164; 6.164; 6.164; 6.164; 6.164; 6.164; 6.164; 6.164; 6.164; 6.164; 6.164; 6.164; 6.164; 3.905; 3.892; 3.844; 3.913; 3.978; 4.056; 4.125; 4.147; 4.203; 4.324; 4.393; 4.393; 4.561; 4.626; 4.738; 4.859; 4.924; 5.015; 5.080; 5.101; 5.075; 5.101; 5.166; 5.166; 5.244; 5.244; 5.330; 5.365; 5.365];
waittime = [0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000];
trajectory(egoVehicle, waypoints, speed, waittime);

if nargout == 0  % called on its own (or with Run): show it
    driveStart = 240.70;  % drive time (s) at the scenario's start
    eventTimes = [243.70 245.34];
    eventNames = {'c14 turn right blinker'};
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
