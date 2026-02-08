from app.services.plugins.commands import Command, CommandRegistry


def test_command_registry():
    registry = CommandRegistry()

    async def handler(message, context, args):
        return None

    registry.register(Command("ping", "test", handler))
    assert registry.get("ping") is not None
    assert registry.list_commands()[0]["command"] == "ping"
