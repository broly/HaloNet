if False:
    from Core.Service import Service

class Globals:
    """
    Глобальные переменные, do not touch this
    """
    no_logging = False
    colored_output = True
    service_name = ""
    detailed_output = True
    this_service: 'Service' = None

    access_token = None

    context_name = "Unknown"

    HaloNet_imported = False
    IsInGenerator = False

    generator_signature = None
    version = None
    disabled_log_categories = []

    workspace = ""
