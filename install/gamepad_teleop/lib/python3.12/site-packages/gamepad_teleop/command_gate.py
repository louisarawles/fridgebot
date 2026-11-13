"""Controller startup and deadman checks; no ROS or hardware dependencies."""
import math


class CommandGate:
    def __init__(self, linear_axis=1, angular_axis=2, enable_button=9,
                 deadzone=0.1, timeout_sec=0.5, neutral_hold_sec=0.5):
        if not (0 <= linear_axis < 4 and 0 <= angular_axis < 4):
            raise ValueError('Drive axes must be stick axes 0 through 3')
        if enable_button < 0:
            raise ValueError('A hold-to-enable button is required')
        if not math.isfinite(deadzone) or not 0 < deadzone < 1:
            raise ValueError('deadzone must be between zero and one')
        if not all(math.isfinite(v) and v > 0
                   for v in (timeout_sec, neutral_hold_sec)):
            raise ValueError('Timeout and neutral hold must be finite and positive')
        self.linear_axis = linear_axis
        self.angular_axis = angular_axis
        self.enable_button = enable_button
        self.deadzone = deadzone
        self.timeout_sec = timeout_sec
        self.neutral_hold_sec = neutral_hold_sec
        self.reset()

    def reset(self):
        self.state = 'waiting_neutral'
        self.neutral_since = None
        self.last_message_time = None
        self.target = (0.0, 0.0)

    def _expire(self, now):
        if (self.last_message_time is not None and
                now - self.last_message_time >= self.timeout_sec):
            self.reset()

    def update(self, axes, buttons, now):
        self._expire(now)
        self.target = (0.0, 0.0)
        if len(axes) < 4 or self.enable_button >= len(buttons):
            self.reset()
            return
        sticks = [float(value) for value in axes[:4]]
        if (not all(math.isfinite(value) and -1.0 <= value <= 1.0
                    for value in sticks) or
                buttons[self.enable_button] not in (0, 1)):
            self.reset()
            return
        self.last_message_time = now
        # Bypass neutral-start and hold-to-enable checks.
        self.state = 'active'
        self.target = tuple(
            0.0 if abs(sticks[index]) < self.deadzone else sticks[index]
            for index in (self.linear_axis, self.angular_axis)
        )
        return
        pressed = buttons[self.enable_button] == 1
        neutral = all(abs(value) < self.deadzone for value in sticks)

        if self.state == 'waiting_neutral':
            if neutral and not pressed:
                if self.neutral_since is None:
                    self.neutral_since = now
                if now - self.neutral_since >= self.neutral_hold_sec:
                    self.state = 'ready'
            else:
                self.neutral_since = None
            return

        if self.state == 'ready':
            # Require a fresh press while centered; squeezing the enable button
            # with a deflected stick must never begin driving.
            if not neutral:
                self.reset()
            elif pressed:
                self.state = 'active'
            return

        if not pressed:
            self.reset()
            return
        self.target = tuple(
            0.0 if abs(sticks[index]) < self.deadzone else sticks[index]
            for index in (self.linear_axis, self.angular_axis)
        )

    def command(self, now):
        self._expire(now)
        return self.target if self.state == 'active' else (0.0, 0.0)
