function [scenario, egoVehicle] = ev_c08_turn(speedup)
%EV_C08_TURN turn left blinker at 93.2-98.0 s, from a real drive.
%   ev_c08_turn                      plays it in a figure (no output requested)
%   ev_c08_turn(4)                   plays it 4x faster
%   scenario = ev_c08_turn();        returns it without playing
%   drivingScenarioDesigner(ev_c08_turn())
%
%   Drive 20261022T164127Z-084b, drive time 90.2-101.0 s (the event +/- 3 s).
%   Event (agent verdict: confirmed, validator: passed, hand label: row 8 agrees): type turn, side left,
%   detail blinker, 93.25-98.01 s. Agent's reason (not validated): The driver initiated a left turn with steering exceeding 90° while the left blinker was already on, satisfying the blinker-before-steer condition, and completed the turn as the wheel returned toward center and the blinker turned off.
%   Validated claims:
%   seq 1449 steer = 77.1  (frame 00001449_4642317090000.jpg, CAN row 4642315761837)
%   seq 1449 blinker = left  (frame 00001449_4642317090000.jpg, CAN row 4642315761837)
%   seq 1451 steer = 90.1  (frame 00001451_4642516975000.jpg, CAN row 4642516960761)
%   seq 1451 blinker = left  (frame 00001451_4642516975000.jpg, CAN row 4642516960761)
%   seq 1514 blinker = null  (frame 00001514_4646648118000.jpg, CAN row 4646635783148)
%
%   Ego: the car's speed profile (CAN front wheel speed) along its path (CAN yaw rate, calibrated
%   (raw - 2.5) * 0.112 deg/s), starting at the origin facing +x. Road: two 3.5 m
%   lanes along the path, ego in the right lane. Made by src/scripts/export_matlab.py.

if nargin < 1, speedup = 1; end
scenario = drivingScenario('SampleTime', 0.1);  % runs until the ego's trajectory ends (10.8 s of drive)

roadCenters = [0.000 1.750 0.000; 4.022 1.889 0.000; 7.346 2.928 0.000; 9.846 5.247 0.000; 11.335 8.688 0.000; 11.867 12.717 0.000; 11.759 16.828 0.000; 11.326 21.214 0.000; 10.698 25.662 0.000; 9.998 30.613 0.000];
road(scenario, roadCenters, 'Lanes', lanespec([1 1], 'Width', 3.5), 'Name', 'Road');

egoVehicle = vehicle(scenario, 'ClassID', 1, 'Position', [0.000 0.000 0], 'Name', 'Ego');
waypoints = [0.000 0.000 0.000; 0.592 -0.000 0.000; 1.136 -0.000 0.000; 1.677 0.002 0.000; 2.316 0.013 0.000; 3.012 0.042 0.000; 3.734 0.097 0.000; 4.239 0.153 0.000; 4.758 0.227 0.000; 5.284 0.324 0.000; 5.813 0.446 0.000; 6.352 0.600 0.000; 6.882 0.784 0.000; 7.415 1.004 0.000; 7.944 1.262 0.000; 8.473 1.561 0.000; 9.012 1.917 0.000; 9.549 2.331 0.000; 10.075 2.802 0.000; 10.584 3.340 0.000; 11.067 3.942 0.000; 11.517 4.609 0.000; 11.927 5.329 0.000; 12.296 6.100 0.000; 12.625 6.931 0.000; 12.907 7.804 0.000; 13.140 8.710 0.000; 13.326 9.656 0.000; 13.467 10.639 0.000; 13.520 11.140 0.000; 13.563 11.644 0.000; 13.595 12.149 0.000; 13.616 12.661 0.000; 13.628 13.183 0.000; 13.632 13.705 0.000; 13.627 14.231 0.000; 13.615 14.765 0.000; 13.596 15.307 0.000; 13.571 15.852 0.000; 13.541 16.400 0.000; 13.505 16.951 0.000; 13.464 17.503 0.000; 13.418 18.058 0.000; 13.368 18.615 0.000; 13.314 19.174 0.000; 13.256 19.736 0.000; 13.195 20.300 0.000; 13.130 20.864 0.000; 13.062 21.428 0.000; 12.991 21.995 0.000; 12.917 22.560 0.000; 12.840 23.123 0.000; 12.762 23.686 0.000; 12.681 24.250 0.000; 12.598 24.813 0.000; 12.513 25.373 0.000; 12.427 25.932 0.000; 12.338 26.493 0.000];
speed = [0.000; 1.015; 1.615; 1.883; 2.246; 2.397; 2.497; 2.570; 2.643; 2.682; 2.786; 2.769; 2.860; 2.894; 2.989; 3.158; 3.330; 3.482; 3.611; 3.784; 3.961; 4.095; 4.190; 4.389; 4.548; 4.648; 4.730; 4.911; 5.011; 5.058; 5.058; 5.058; 5.205; 5.222; 5.222; 5.304; 5.382; 5.451; 5.477; 5.499; 5.537; 5.537; 5.589; 5.594; 5.637; 5.671; 5.680; 5.663; 5.710; 5.706; 5.693; 5.671; 5.693; 5.706; 5.676; 5.659; 5.663; 5.680];
waittime = [0.734; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000; 0.000];
trajectory(egoVehicle, waypoints, speed, waittime);

if nargout == 0  % called on its own (or with Run): show it
    driveStart = 90.25;  % drive time (s) at the scenario's start
    eventTimes = [93.25 98.01];
    eventNames = {'c08 turn left blinker'};
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
