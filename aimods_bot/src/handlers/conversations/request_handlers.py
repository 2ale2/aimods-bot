from .handler_factory import RequestHandlerFactory
from .handler_config import HandlerType, ParentHandlerConfig

windows_game_request_handler = RequestHandlerFactory.create_nested_handler(HandlerType.WINDOWS_GAME)
windows_adobe_request_handler = RequestHandlerFactory.create_nested_handler(HandlerType.WINDOWS_ADOBE)
windows_daw_request_handler = RequestHandlerFactory.create_nested_handler(HandlerType.WINDOWS_DAW)
windows_software_request_handler = RequestHandlerFactory.create_nested_handler(HandlerType.WINDOWS_SOFTWARE)
macos_daw_request_handler = RequestHandlerFactory.create_nested_handler(HandlerType.MACOS_DAW)
macos_software_request_handler = RequestHandlerFactory.create_nested_handler(HandlerType.MACOS_SOFTWARE)
android_request_handler = RequestHandlerFactory.create_standalone_handler(HandlerType.ANDROID)
ios_request_handler = RequestHandlerFactory.create_standalone_handler(HandlerType.IOS)

windows_request_handler = RequestHandlerFactory.create_parent_handler(
    ParentHandlerConfig.WINDOWS,
    nested_handlers=[
        windows_game_request_handler,
        windows_adobe_request_handler,
        windows_daw_request_handler,
        windows_software_request_handler
    ]
)

macos_request_handler = RequestHandlerFactory.create_parent_handler(
    ParentHandlerConfig.MACOS,
    nested_handlers=[
        macos_daw_request_handler,
        macos_software_request_handler
    ]
)


__all__ = [
    # Nested handlers
    'windows_game_request_handler',
    'windows_adobe_request_handler',
    'windows_daw_request_handler',
    'windows_software_request_handler',
    'macos_daw_request_handler',
    'macos_software_request_handler',
    'android_request_handler',
    'ios_request_handler',
    # Parent handlers
    'windows_request_handler',
    'macos_request_handler',
]
