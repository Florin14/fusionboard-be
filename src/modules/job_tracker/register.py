from modules.platform_registry.service_registry import registry, PlatformService


def register_job_tracker_service() -> None:
    registry.register(PlatformService(
        id="job_tracker",
        name="Job Tracker",
        description="Track job applications, interviews, and follow-ups",
        prefix="/services/jobs",
        icon="work",
        color="#8B5CF6",
    ))
