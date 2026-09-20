import os
import json
import cv2
import easyocr
import torch
from enhancement import apply_clahe

class VehicleEngine:
    def __init__(self, db_path="data/registered_vehicles.json"):
        self.db_path = db_path
        self.reader = easyocr.Reader(['en'], gpu=torch.cuda.is_available())
        self.load_database()

    def load_database(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        if not os.path.exists(self.db_path):
            with open(self.db_path, "w") as f:
                json.dump({"plates": []}, f)
        with open(self.db_path, "r") as f:
            try:
                self.whitelist = json.load(f).get("plates", [])
            except json.JSONDecodeError:
                self.whitelist = []

    def save_database(self):
        with open(self.db_path, "w") as f:
            json.dump({"plates": self.whitelist}, f, indent=4)

    def register_plate(self, raw_plate: str):
        cleaned = "".join([c for c in raw_plate if c.isalnum()]).upper()
        if cleaned and cleaned not in self.whitelist:
            self.whitelist.append(cleaned)
            self.save_database()
            return True, f"Plate {cleaned} added to whitelist."
        return False, f"Plate {cleaned} already exists or is invalid."

    def extract_plate_text(self, car_bgr_crop):
        if car_bgr_crop is None or car_bgr_crop.size == 0:
            return "", 0.0

        height, width = car_bgr_crop.shape[:2]
        if height < 15 or width < 15:
            return "", 0.0

        enhanced_crop = apply_clahe(car_bgr_crop)
        gray = cv2.cvtColor(enhanced_crop, cv2.COLOR_BGR2GRAY)
        
        # Focus on lower half where vehicle license plates are usually located
        lower_region_gray = gray[round(height * 0.25):, :]
        enlarged = cv2.resize(lower_region_gray, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
        blurred = cv2.GaussianBlur(enlarged, (5, 5), 0)
        _, thresholded = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        full_crop = cv2.resize(gray, None, fx=1.5, fy=1.5, interpolation=cv2.INTER_CUBIC)

        best_plate = ""
        best_confidence = 0.0

        # Try color crop first, then enhanced, then resized gray/thresholded
        candidate_images = (car_bgr_crop, enhanced_crop, enlarged, thresholded, full_crop)

        for image in candidate_images:
            try:
                results = self.reader.readtext(
                    image,
                    detail=1,
                    paragraph=False,
                    allowlist="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
                )
            except Exception:
                continue

            for (_, text, probability) in results:
                cleaned = "".join(character for character in text if character.isalnum()).upper()
                confidence = float(probability)
                # Prioritize whitelisted plates if an exact match is detected
                if cleaned in self.whitelist:
                    return cleaned, max(confidence, 0.90)

                if 3 <= len(cleaned) <= 12 and confidence > best_confidence and confidence >= 0.18:
                    best_plate = cleaned
                    best_confidence = confidence

        return best_plate, best_confidence

    def verify_plate(self, car_bgr_crop):
        plate, confidence = self.extract_plate_text(car_bgr_crop)
        if not plate:
            return None, False, 0.0
        is_whitelisted = plate in self.whitelist
        return plate, is_whitelisted, confidence