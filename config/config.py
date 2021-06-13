import confuse

__all__ = ["CONFIG"]

CONFIG = confuse.Configuration("parnassius", __name__)
CONFIG.set_file("config.yaml")
CONFIG["discord"]["token"].redact = True
