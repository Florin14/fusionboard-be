from modules.platform_registry.service_registry import registry, PlatformService


def register_smart_tasks_service() -> None:
    registry.register(PlatformService(
        id="smart_tasks",
        name="Smart Tasks",
        description="Task management with reminders and recurring tasks",
        prefix="/services/tasks",
        icon="checklist",
        color="#EC4899",
    ))
