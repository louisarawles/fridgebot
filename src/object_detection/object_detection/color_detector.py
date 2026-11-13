import cv2
import numpy as np

# HSV ranges for different colors (we need to test and likely tweak these)
color_ranges = {
    "red": [
        ((0, 100, 100), (10, 255, 255)),
        ((170, 100, 100), (179, 255, 255))
    ],
    "orange": [
        ((11, 100, 100), (20, 255, 255))
    ],
    "yellow": [
        ((21, 100, 100), (34, 255, 255))
    ],
    "green": [
        ((35, 50, 50), (85, 255, 255))
    ],
    "cyan": [
        ((86, 100, 100), (100, 255, 255))
    ],
    "blue": [
        ((101, 100, 100), (130, 255, 255))
    ],
    "purple": [
        ((131, 70, 70), (150, 255, 255))
    ],
    "pink": [
        ((151, 70, 70), (169, 255, 255))
    ]
}

cap = cv2.VideoCapture(0)

while True:

    ret, frame = cap.read()
    
    if not ret:
        break
        
    # Convert BGR to HSV
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    
    for color_name, ranges in color_ranges.items():
        # Initialize empty mask
        mask = np.zeros(hsv.shape[:2], dtype=np.uint8)
        
        # Combine all HSV ranges for this color
        for lower, upper in ranges:
            lower_bound = np.array(lower, dtype=np.uint8)
            upper_bound = np.array(upper, dtype=np.uint8)
            
            color_mask = cv2.inRange(
                hsv,
                lower_bound,
                upper_bound
            )
            
            mask = cv2.bitwise_or(mask, color_mask)
    
    # Remove noise
    kernel = np.ones((5, 5), np.uint8)
    
    mask = cv2.morphologyEx(
        mask,
        cv2.MORPH_OPEN,
        kernel
    )
    
    mask = cv2.morphologyEx(
        mask,
        cv2.MORPH_CLOSE,
        kernel
    )
    
    # Find contours
    contours, _ = cv2.findContours(
        mask,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE
    )
    
    for contour in contours:
        # Ignore small objects
        if cv2.contourArea(contour) < 500:
            continue
            
        # Find centroid
        M = cv2.moments(contour)
        
        if M["m00"] == 0:
            continue
            
        center_x = int(M["m10"] / M["m00"])
        center_y = int(M["m01"] / M["m00"])
        
        # Draw contour
        cv2.drawContours(
            frame,
            [contour],
            -1,
            (0, 255, 0),
            2
        )
        
        # Draw center
        cv2.circle(
            frame,
            (center_x, center_y),
            5,
            (0, 0, 255),
            -1
        )
        
        # Label detected object
        cv2.putText(
            frame,
            f"{color_name}: ({center_x}, {center_y})",
            (center_x + 10, center_y - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (255, 255, 255),
            2
        )
    
    cv2.imshow("Multi-Color Detection", frame)
    
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break
        
cap.release()
cv2.destroyAllWindows()
