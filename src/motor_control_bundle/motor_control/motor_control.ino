#include <DualVNH5019MotorShield.h>
#include <ctype.h>
#include <math.h>
#include <stdlib.h>

// Serial protocol: "linear.x angular.z\n", in m/s and rad/s.
// Example: "0.0500 0.0000\n". Send at 20 Hz; no ROS messages on USB.
const unsigned long SERIAL_BAUD = 9600;
const unsigned long COMMAND_TIMEOUT_MS = 500;

// Preserved from the original sketch. If 6 inches is the DIAMETER,
// change WHEEL_RADIUS_M to 3.0 * 0.0254 before operating the robot.
const double WHEEL_RADIUS_M = 3.0 * 0.0254;
const double TRACK_WIDTH_M = 17.75 * 0.0254;
const double MAX_WHEEL_RPM = 13.5;  // Wheel output RPM, not motor shaft RPM.
const double TWO_PI_VALUE = 6.283185307179586;

// Preserves original wiring: M1 = left wheel; M2 = right wheel.
// Set a direction to -1 if positive commands turn that wheel backwards.
const int LEFT_DIRECTION = 1;
const int RIGHT_DIRECTION = -1;

DualVNH5019MotorShield md;
char lineBuffer[64];
uint8_t lineLength = 0;
bool discardLine = false;
bool haveCommand = false;
bool faultLatched = false;
unsigned long lastCommandMs = 0;
int leftCommand = 0;
int rightCommand = 0;

void stopMotors() {
  leftCommand = 0;
  rightCommand = 0;
  haveCommand = false;
  md.setSpeeds(0, 0);  // Zero drive / coast, not active braking.
}

bool parseCommand(const char* text, double& v, double& w) {
  char* end;
  v = strtod(text, &end);
  if (end == text || !isfinite(v)) return false;
  // Require whitespace between the two numbers (reject "1-2").
  if (!isspace((unsigned char)*end)) return false;
  while (isspace((unsigned char)*end)) ++end;
  const char* second = end;
  w = strtod(second, &end);
  if (end == second || !isfinite(w)) return false;
  while (isspace((unsigned char)*end)) ++end;
  return *end == '\0';
}

void handleLine(const char* text) {
  if (faultLatched) return;
  double v, w;
  if (!parseCommand(text, v, w)) {
    stopMotors();
    return;
  }

  const double unitsPerMps = 400.0 * 60.0 /
      (MAX_WHEEL_RPM * TWO_PI_VALUE * WHEEL_RADIUS_M);
  double left = (v - w * TRACK_WIDTH_M / 2.0) * unitsPerMps;
  double right = (v + w * TRACK_WIDTH_M / 2.0) * unitsPerMps;
  // Finite inputs can still overflow intermediate arithmetic on an Uno.
  if (!isfinite(left) || !isfinite(right)) {
    stopMotors();
    return;
  }
  const double peak = fmax(fabs(left), fabs(right));
  if (peak > 400.0) {
    left = (left / peak) * 400.0;
    right = (right / peak) * 400.0;
  }
  leftCommand = LEFT_DIRECTION * (int)round(left);
  rightCommand = RIGHT_DIRECTION * (int)round(right);
  lastCommandMs = millis();
  haveCommand = true;
}

void readCommands() {
  // Bound work so continuous serial input cannot starve fault/timeout checks.
  for (uint8_t count = 0; count < 64 && Serial.available() > 0; ++count) {
    const char c = (char)Serial.read();
    if (c == '\n' || c == '\r') {
      if (!discardLine && lineLength > 0) {
        lineBuffer[lineLength] = '\0';
        handleLine(lineBuffer);
      }
      lineLength = 0;
      discardLine = false;
    } else if (!discardLine) {
      if (c == '\0' || lineLength >= sizeof(lineBuffer) - 1) {
        // Discard the ENTIRE remainder of this frame, not just the prefix.
        discardLine = true;
        lineLength = 0;
        stopMotors();
      } else {
        lineBuffer[lineLength++] = c;
      }
    }
  }
}

void setup() {
  md.init();
  stopMotors();
  Serial.begin(SERIAL_BAUD);
}

void loop() {
  if (!faultLatched && (md.getM1Fault() || md.getM2Fault())) {
    faultLatched = true;  // Fix the fault and reset the Arduino to re-enable.
    stopMotors();
    Serial.println(F("FAULT: motor driver; reset required"));
  }
  readCommands();
  if (faultLatched || !haveCommand ||
      (unsigned long)(millis() - lastCommandMs) >= COMMAND_TIMEOUT_MS) {
    stopMotors();
  } else {
    md.setSpeeds(leftCommand, rightCommand);
  }
}
