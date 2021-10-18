import confuse

__all__ = ["CONFIG"]

CONFIG = confuse.Configuration("parnassius", __name__)
# Add the least important files first, as later additions override earlier ones
CONFIG.set_file("resources/discord_logging.yaml")
CONFIG.set_file("resources/forbidden_words.yaml")
CONFIG.set_file("config.yaml", base_for_paths=True)
CONFIG["discord"]["token"].redact = True
