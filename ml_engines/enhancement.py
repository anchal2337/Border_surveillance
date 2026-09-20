import cv2

_CLAHE = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))

def apply_clahe(bgr_frame, clip_limit=2.5, grid_size=(8, 8)):
    """Applies CLAHE on the L-channel in LAB space to enhance contrast."""
    lab = cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = _CLAHE if clip_limit == 2.5 and grid_size == (8, 8) else cv2.createCLAHE(
        clipLimit=clip_limit, tileGridSize=grid_size
    )
    cl = clahe.apply(l)
    merged = cv2.merge((cl, a, b))
    return cv2.cvtColor(merged, cv2.COLOR_LAB2BGR)