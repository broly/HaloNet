# HaloNet
An Python and Unreal Engine 4 framework which can be used for creating MMO games

This framework aims on easy and fast MMO games development.
Main features: 
 1. Service-oriented scalable structure
 2. Asynchrous Remote Method Invocation (RMI) based API interface (between services and game engine)
 3. Database integration with ORM support (for now is Postgres)
 4. Variable replication between services and game engine
 5. Variable persistence
 6. Variable transactions
 7. Automatic code generation for game engine (reduces time spent)
 8. Admin interface can be used for managment and debug services and database
 9. User registration and logining via game
 10. Log support

Also:
 1. Redmine integration for bug reporting
 2. Sentry integration
 3. Steam auth integration
 4. Match making

Author got inspiration from BigWorld game engine, Python and UE4

In this release used is only Unreal Engine 4. And most features can be also used via blueprints

Some features in screenshots:

Using in blueprints (C++ generated nodes)
![alt text](https://github.com/broly/HaloNet/blob/master/Pics/halonet_blueprint.png?raw=true)

Unreal style RMI declarations (will generate similar C++ code)
![alt text](https://github.com/broly/HaloNet/blob/master/Pics/halonet_rmi.png?raw=true)

Async method call in C++ (using generated code)
![alt text](https://github.com/broly/HaloNet/blob/master/Pics/halonet_ue4_async_call.png?raw=true)

Generated docs for each user-defined RMI and variable
![alt text](https://github.com/broly/HaloNet/blob/master/Pics/halonet_generated_methods.png?raw=true)

Contact me: metrickxxx@gmail.com
