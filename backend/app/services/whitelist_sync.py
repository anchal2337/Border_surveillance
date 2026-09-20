import os
import json
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from backend.app.core.config import settings
from backend.app.models.entities import RegisteredPersonnel, RegisteredVehicle

logger = logging.getLogger("whitelist_sync")

class WhitelistSyncService:
    """
    Two-way synchronization bridge between SQLite whitelist tables
    and OutLiners_SIH JSON registries (registered_faces.json & registered_vehicles.json).
    Ensures 100% data consistency without modifying OutLiners_SIH scripts.
    """

    def __init__(self):
        self.faces_json_path = settings.DATA_DIR / "registered_faces.json"
        self.vehicles_json_path = settings.DATA_DIR / "registered_vehicles.json"
        self._ensure_files()

    def _ensure_files(self) -> None:
        """Ensures the JSON files exist on disk with valid structure."""
        self.faces_json_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.faces_json_path.exists():
            with open(self.faces_json_path, "w", encoding="utf-8") as f:
                json.dump({}, f)

        if not self.vehicles_json_path.exists():
            with open(self.vehicles_json_path, "w", encoding="utf-8") as f:
                json.dump({"plates": []}, f)

    def sync_from_json_to_db(self, db: Session) -> Dict[str, int]:
        """
        Imports existing entries from legacy JSON files into SQLite database if missing.
        """
        imported_faces = 0
        imported_vehicles = 0

        # 1. Sync Faces
        try:
            with open(self.faces_json_path, "r", encoding="utf-8") as f:
                faces_data = json.load(f)

            for name, info in faces_data.items():
                existing = db.query(RegisteredPersonnel).filter(RegisteredPersonnel.full_name == name).first()
                if not existing and isinstance(info, dict) and "embedding" in info:
                    personnel = RegisteredPersonnel(
                        full_name=name,
                        designation=info.get("designation", "Border Guard"),
                        department="Perimeter Security",
                        face_embedding=json.dumps(info["embedding"]),
                        is_authorized=True,
                    )
                    db.add(personnel)
                    imported_faces += 1
            db.commit()
        except Exception as e:
            logger.warning("Error reading registered_faces.json: %s", e)

        # 2. Sync Vehicles
        try:
            with open(self.vehicles_json_path, "r", encoding="utf-8") as f:
                vehicles_data = json.load(f)

            plates = vehicles_data.get("plates", [])
            for raw_plate in plates:
                cleaned_plate = "".join([c for c in str(raw_plate) if c.isalnum()]).upper()
                if cleaned_plate:
                    existing = db.query(RegisteredVehicle).filter(RegisteredVehicle.license_plate == cleaned_plate).first()
                    if not existing:
                        vehicle = RegisteredVehicle(
                            license_plate=cleaned_plate,
                            vehicle_type="car",
                            owner_name="Official Border Convoy",
                            department="Border Patrol",
                            is_whitelisted=True,
                        )
                        db.add(vehicle)
                        imported_vehicles += 1
            db.commit()
        except Exception as e:
            logger.warning("Error reading registered_vehicles.json: %s", e)

        logger.info("Whitelist sync completed: %d faces, %d vehicles imported into SQLite", imported_faces, imported_vehicles)
        return {"faces_imported": imported_faces, "vehicles_imported": imported_vehicles}

    def sync_from_db_to_json(self, db: Session) -> None:
        """
        Exports SQLite whitelist entries into JSON files so OutLiners_SIH engines read them.
        """
        # 1. Sync faces to JSON
        personnel_records = db.query(RegisteredPersonnel).filter(RegisteredPersonnel.is_authorized == True).all()
        faces_dict = {}
        for p in personnel_records:
            try:
                emb = json.loads(p.face_embedding)
                faces_dict[p.full_name] = {
                    "designation": p.designation,
                    "embedding": emb,
                }
            except Exception:
                continue

        with open(self.faces_json_path, "w", encoding="utf-8") as f:
            json.dump(faces_dict, f, indent=4)

        # 2. Sync vehicles to JSON
        vehicle_records = db.query(RegisteredVehicle).filter(RegisteredVehicle.is_whitelisted == True).all()
        plates_list = [v.license_plate for v in vehicle_records if v.license_plate]

        with open(self.vehicles_json_path, "w", encoding="utf-8") as f:
            json.dump({"plates": plates_list}, f, indent=4)

    def register_personnel(
        self,
        db: Session,
        full_name: str,
        designation: str,
        face_embedding: List[float],
        badge_number: Optional[str] = None,
        department: str = "Perimeter Security",
        photo_path: Optional[str] = None,
        registered_by_id: Optional[str] = None,
    ) -> RegisteredPersonnel:
        """
        Registers a new personnel in SQLite and immediately updates registered_faces.json.
        """
        existing = db.query(RegisteredPersonnel).filter(RegisteredPersonnel.full_name == full_name).first()
        if existing:
            existing.designation = designation
            existing.face_embedding = json.dumps(face_embedding)
            existing.badge_number = badge_number
            existing.photo_path = photo_path
            existing.is_authorized = True
            personnel = existing
        else:
            personnel = RegisteredPersonnel(
                full_name=full_name,
                designation=designation,
                badge_number=badge_number,
                department=department,
                face_embedding=json.dumps(face_embedding),
                photo_path=photo_path,
                is_authorized=True,
                registered_by=registered_by_id,
            )
            db.add(personnel)

        db.commit()
        db.refresh(personnel)

        # Update JSON file immediately so the AI engine catches the new face live
        try:
            with open(self.faces_json_path, "r", encoding="utf-8") as f:
                faces_data = json.load(f)
        except Exception:
            faces_data = {}

        faces_data[full_name] = {
            "designation": designation,
            "embedding": face_embedding,
        }
        with open(self.faces_json_path, "w", encoding="utf-8") as f:
            json.dump(faces_data, f, indent=4)

        return personnel

    def register_vehicle(
        self,
        db: Session,
        license_plate: str,
        vehicle_type: str = "car",
        owner_name: Optional[str] = None,
        department: str = "Border Patrol",
        notes: Optional[str] = None,
        registered_by_id: Optional[str] = None,
    ) -> RegisteredVehicle:
        """
        Registers an authorized vehicle plate in SQLite and updates registered_vehicles.json.
        """
        cleaned = "".join([c for c in license_plate if c.isalnum()]).upper()
        if not cleaned:
            raise ValueError("License plate must contain alphanumeric characters.")

        existing = db.query(RegisteredVehicle).filter(RegisteredVehicle.license_plate == cleaned).first()
        if existing:
            existing.vehicle_type = vehicle_type
            existing.owner_name = owner_name
            existing.is_whitelisted = True
            existing.notes = notes
            vehicle = existing
        else:
            vehicle = RegisteredVehicle(
                license_plate=cleaned,
                vehicle_type=vehicle_type,
                owner_name=owner_name,
                department=department,
                is_whitelisted=True,
                notes=notes,
                registered_by=registered_by_id,
            )
            db.add(vehicle)

        db.commit()
        db.refresh(vehicle)

        # Update JSON plate whitelist
        try:
            with open(self.vehicles_json_path, "r", encoding="utf-8") as f:
                vehicles_data = json.load(f)
        except Exception:
            vehicles_data = {"plates": []}

        plates = vehicles_data.get("plates", [])
        if cleaned not in plates:
            plates.append(cleaned)
            vehicles_data["plates"] = plates
            with open(self.vehicles_json_path, "w", encoding="utf-8") as f:
                json.dump(vehicles_data, f, indent=4)

        return vehicle
