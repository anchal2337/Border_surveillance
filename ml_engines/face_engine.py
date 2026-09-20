import os
import json
import torch
from PIL import Image
import cv2
from facenet_pytorch import MTCNN, InceptionResnetV1

class FaceRecognitionEngine:
    def __init__(self, db_path="data/registered_faces.json", device=None):
        self.device = device or torch.device('cuda:0' if torch.cuda.is_available() else 'cpu')
        self.db_path = db_path
        self.mtcnn = MTCNN(keep_all=False, device=self.device)
        self.resnet = InceptionResnetV1(pretrained='vggface2').eval().to(self.device)
        self.load_database()

    def load_database(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        if not os.path.exists(self.db_path):
            with open(self.db_path, "w") as f:
                json.dump({}, f)
        with open(self.db_path, "r") as f:
            try:
                self.database = json.load(f)
            except json.JSONDecodeError:
                self.database = {}

    def save_database(self):
        with open(self.db_path, "w") as f:
            json.dump(self.database, f, indent=4)

    def _detect_face(self, bgr_image):
        if bgr_image is None or bgr_image.size == 0:
            return None
        height, width = bgr_image.shape[:2]
        minimum_side = min(height, width)
        if minimum_side < 160:
            scale = 160 / minimum_side
            bgr_image = cv2.resize(
                bgr_image,
                (round(width * scale), round(height * scale)),
                interpolation=cv2.INTER_CUBIC,
            )
            height, width = bgr_image.shape[:2]

        rgb_img = cv2.cvtColor(bgr_image, cv2.COLOR_BGR2RGB)
        face = self.mtcnn(Image.fromarray(rgb_img))
        if face is None and height > 120:
            # Fallback: scan upper 55% where the face is positioned on full-body detections
            upper_crop = rgb_img[:int(height * 0.55), :]
            if upper_crop.size > 0:
                face = self.mtcnn(Image.fromarray(upper_crop))
        return face

    def register_face(self, bgr_image, name: str, designation: str):
        face_tensor = self._detect_face(bgr_image)
        if face_tensor is None:
            return False, "No discernible face detected in the image."

        with torch.no_grad():
            embedding = self.resnet(face_tensor.unsqueeze(0).to(self.device))
            emb_list = embedding[0].cpu().tolist()

        self.database[name] = {
            "designation": designation,
            "embedding": emb_list
        }
        self.save_database()
        return True, f"Identity {name} ({designation}) registered successfully."

    def verify_crop(self, person_bgr_crop, threshold=0.90):
        face_tensor = self._detect_face(person_bgr_crop)
        if face_tensor is None:
            return "No Face Detected", "N/A", False, 0.0

        with torch.no_grad():
            live_emb = self.resnet(face_tensor.unsqueeze(0).to(self.device))

        best_match = "Unknown"
        best_desig = "Unregistered"
        min_dist = float('inf')

        for name, data in self.database.items():
            reg_emb = torch.tensor(data["embedding"]).unsqueeze(0).to(self.device)
            dist = (live_emb - reg_emb).norm().item()
            if dist < min_dist:
                min_dist = dist
                if dist < threshold:
                    best_match = name
                    best_desig = data.get("designation", "Personnel")

        is_authorized = best_match != "Unknown"
        confidence = max(0.0, min(1.0, 1.0 - (min_dist / threshold))) if min_dist != float('inf') else 0.0
        return best_match, best_desig, is_authorized, confidence