import math
import unittest

from gamepad_teleop.command_gate import CommandGate


class GateTests(unittest.TestCase):
    def setUp(self):
        self.gate = CommandGate()

    def update(self, t, forward=0.0, turn=0.0, pressed=False, other=0.0):
        axes = [other, forward, turn, 0.0]
        buttons = [0] * 15
        buttons[9] = int(pressed)
        self.gate.update(axes, buttons, t)
        return self.gate.command(t)

    def ready(self, start=0.0):
        for delta in (0.0, 0.2, 0.4, 0.6):
            self.update(start + delta)
        self.assertEqual(self.gate.state, 'ready')

    def active(self):
        self.ready()
        self.update(0.7, pressed=True)
        self.assertEqual(self.gate.state, 'active')

    def test_observed_full_scale_startup_never_moves(self):
        for i in range(20):
            self.assertEqual(self.update(i * .05, 1.0, 1.0), (0.0, 0.0))
        self.assertEqual(self.update(1.0, 1.0, 1.0, True), (0.0, 0.0))
        self.assertEqual(self.gate.state, 'waiting_neutral')

    def test_held_button_at_start_cannot_arm(self):
        for i in range(20):
            self.update(i * .05, pressed=True)
        self.assertEqual(self.gate.state, 'waiting_neutral')

    def test_centered_released_hold_then_fresh_press(self):
        self.ready()
        self.assertEqual(self.update(.7, pressed=True), (0.0, 0.0))
        self.assertEqual(self.update(.8, .6, -.2, True), (.6, -.2))

    def test_short_neutral_hold_does_not_arm(self):
        self.update(0.0)
        self.update(.2)
        self.update(.4)
        self.assertEqual(self.gate.state, 'waiting_neutral')

    def test_deflection_interrupts_neutral_hold(self):
        self.update(0.0)
        self.update(.2)
        self.update(.3, forward=.2)
        self.update(.4)
        self.update(.6)
        self.update(.8)
        self.assertEqual(self.gate.state, 'waiting_neutral')

    def test_press_with_deflected_stick_is_rejected(self):
        self.ready()
        self.assertEqual(self.update(.7, .5, 0.0, True), (0.0, 0.0))
        self.assertEqual(self.gate.state, 'waiting_neutral')

    def test_both_sticks_must_be_centered(self):
        for i in range(20):
            self.update(i * .05, other=.3)
        self.assertEqual(self.gate.state, 'waiting_neutral')

    def test_release_stops_and_requires_neutral_again(self):
        self.active()
        self.update(.8, .5, 0.0, True)
        self.assertEqual(self.update(.9, .5), (0.0, 0.0))
        self.assertEqual(self.update(1.0, .5, 0.0, True), (0.0, 0.0))
        self.assertEqual(self.gate.state, 'waiting_neutral')

    def test_timeout_stops_without_new_callback(self):
        self.active()
        self.update(.8, .5, 0.0, True)
        self.assertEqual(self.gate.command(1.31), (0.0, 0.0))
        self.assertEqual(self.gate.state, 'waiting_neutral')

    def test_reconnect_held_cannot_resume(self):
        self.active()
        self.update(.8, .5, 0.0, True)
        self.assertEqual(self.update(1.4, .5, 0.0, True), (0.0, 0.0))
        self.assertEqual(self.gate.state, 'waiting_neutral')

    def test_reconnect_requires_another_complete_neutral_hold(self):
        self.active()
        self.update(1.5)
        self.update(1.7)
        self.update(1.9)
        self.assertEqual(self.gate.state, 'waiting_neutral')
        self.update(2.1)
        self.assertEqual(self.gate.state, 'ready')

    def test_invalid_axis_values_stop_an_active_session(self):
        for value in (math.nan, math.inf, -math.inf, 1.01, -1.01):
            with self.subTest(value=value):
                self.gate = CommandGate()
                self.active()
                self.assertEqual(self.update(.8, value, 0.0, True), (0.0, 0.0))
                self.assertEqual(self.gate.state, 'waiting_neutral')

    def test_missing_controls_stop_an_active_session(self):
        for axes, buttons in (([], [0] * 15), ([0.0] * 4, [])):
            self.gate = CommandGate()
            self.active()
            self.gate.update(axes, buttons, .8)
            self.assertEqual(self.gate.command(.8), (0.0, 0.0))

    def test_invalid_enable_value_stops(self):
        self.active()
        buttons = [0] * 15
        buttons[9] = 2
        self.gate.update([0.0] * 4, buttons, .8)
        self.assertEqual(self.gate.state, 'waiting_neutral')

    def test_observed_neutral_noise_passes_and_filters_to_zero(self):
        for t in (0.0, .2, .4, .6):
            self.update(t, -.004, -.027, other=-.051)
        self.assertEqual(self.gate.state, 'ready')
        self.update(.7, -.004, -.027, True, other=-.051)
        self.assertEqual(self.update(.8, -.004, -.027, True), (0.0, 0.0))

    def test_cannot_disable_enable_button(self):
        with self.assertRaises(ValueError):
            CommandGate(enable_button=-1)


if __name__ == '__main__':
    unittest.main(verbosity=2)
