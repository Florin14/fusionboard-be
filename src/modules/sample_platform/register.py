from modules.platform_registry.service_registry import registry, PlatformService


def register_sample_service() -> None:
    registry.register(PlatformService(
        id="sample_platform",
        name="Sample Platform",
        description="Template platform service - duplicate and customize",
        prefix="/services/sample",
        icon="extension",
        color="#6366F1",
    ))
