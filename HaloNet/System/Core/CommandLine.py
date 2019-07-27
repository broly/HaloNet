import argparse


class Arguments:
    service_port:           int = None
    causer_port:            int = None
    causer_ip:              str = None
    causer_exposed_ip:      str = ""
    base_ip:                str = None
    base_port:              str = None
    postfix:                str = ""
    silent:                 int = False
    access_token:           str = ""
    dedic_id:               int
    local_network_version:  int
    no_color_patterns:      int = False
    test:                   int = 0
    region:                 str = "UnknownRegion"

    # unreal port
    port:                   int = 7777

    generate_only_config:   int = False
    is_child_process:       int = False

    clearall:               int = False
    MaxPlayers:             int = 50

    BotsCount:              int = 50


class CommandLine:

    @classmethod
    def get_arguments(cls) -> Arguments:
        parser = argparse.ArgumentParser()
        for arg_name, arg_type in Arguments.__annotations__.items():
            if hasattr(Arguments, arg_name):
                parser.add_argument("-%s" % arg_name, type=arg_type, default=getattr(Arguments, arg_name))
            else:
                parser.add_argument("-%s" % arg_name, type=arg_type)
        args = parser.parse_args()
        return args

    @classmethod
    def get_arg_type(cls, arg_name):
        return Arguments.__annotations__.get(arg_name)

    @classmethod
    def has_arg(cls, arg_name):
        return arg_name in Arguments.__annotations__
