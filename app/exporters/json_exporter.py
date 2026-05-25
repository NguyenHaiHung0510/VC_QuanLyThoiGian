import json
from dataclasses import asdict
from .planner_dto import PlannerExportDTO

class JSONExporter:
    @staticmethod
    def export(dto: PlannerExportDTO) -> str:
        # Convert nested dataclasses to dictionary
        dto_dict = asdict(dto)
        return json.dumps(dto_dict, ensure_ascii=False, indent=2, default=str)
