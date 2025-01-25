from app.models import Project

PROJECTS: dict[int, Project] = {i: Project(id=i, name=f"Project {i}") for i in range(1, 11)}


async def get_projects() -> list[Project]:
    return [project for id, project in PROJECTS.items()]


async def add_project(name: str) -> Project:
    new_id = max(id for id in PROJECTS.keys()) + 1
    project = Project(id=new_id, name=name)
    PROJECTS[new_id] = project
    return project


async def delete_project(id: int) -> Project | None:
    return PROJECTS.pop(id, None)
