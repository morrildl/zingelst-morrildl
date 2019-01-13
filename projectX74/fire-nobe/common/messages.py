class Message:
    pass

class ServerMessages:
    MAX_MESSAGE_SIZE = 4096
    message_formats = { }
    message_names = { }
    message_fields = { }

    # this is basically a ping; has no real meaning, just used as a way to
    # send an arbitrary message to/from the server
    HEARTBEAT = 1
    message_names[HEARTBEAT] = "HEARTBEAT"
    message_formats[HEARTBEAT] = "H"
    message_fields[HEARTBEAT] = ["handle"]

    # handshake message; sent by server to client when the server receives a
    # HELLO message from client. Payload contains the client's 'handle'
    ACK_HELLO = 2
    message_names[ACK_HELLO] = "ACK_HELLO"
    message_formats[ACK_HELLO] = "H"
    message_fields[ACK_HELLO] = ["handle"]

    # authoritative client location; client is expected to sync on this
    # This has potential for choppy behavior in client, if the sync rates are
    # too low (e.g. 20Hz) and/or the server and client are too far out of phase
    # with each other. In this case, either increase sync rate (global timer
    # frequencies) to minimize the physical impact, or else have the client
    # essentially ignore the fields if they are within a certain margin of
    # error from where the client currently "thinks" it is. Note that this
    # is merely an allowance for quality of animation on client, since server's
    # state is still authoritative when doing collision detections, etc.
    CLIENT_LOCATION = 3
    message_names[CLIENT_LOCATION] = "CLIENT_LOCATION"
    message_formats[CLIENT_LOCATION] = "HIIf"
    message_fields[CLIENT_LOCATION] = ["handle", "x", "y", "heading"]

    # used by the server to transmit space sector background sprites to client
    # generally we expect these to only be used on startup/connection
    SECTOR_SPRITE_DEF = 4
    message_names[SECTOR_SPRITE_DEF] = "SECTOR_SPRITE_DEF"
    message_formats[SECTOR_SPRITE_DEF] = "IIIf"
    message_fields[SECTOR_SPRITE_DEF] = ["key", "x", "y", "heading"]

class ClientMessages:
    MAX_MESSAGE_SIZE = 4096
    message_formats = { }
    message_names = { }
    message_fields = { }

    # handshake message: announces client to server, requests connection
    HELLO = 1
    message_names[HELLO] = "HELLO"
    message_formats[HELLO] = ""
    message_fields[HELLO] = []

    # handshake message; basically a courtesy to the server notifying it that
    # the client is going away, since otherwise the server will have to wait
    # for a timeout
    GOODBYE = 2
    message_names[GOODBYE] = "GOODBYE"
    message_formats[GOODBYE] = ""
    message_fields[GOODBYE] = []

    # this is basically a ping; has no real meaning, just used as a way to
    # send an arbitrary message to/from the server
    HEARTBEAT = 3
    message_names[HEARTBEAT] = "HEARTBEAT"
    message_formats[HEARTBEAT] = ""
    message_fields[HEARTBEAT] = []

    # update the server's state with the current location/heading of the client
    MY_LOCATION = 4
    message_names[MY_LOCATION] = "MY_LOCATION"
    message_formats[MY_LOCATION] = "IIf"
    message_fields[MY_LOCATION] = ["x", "y", "heading"]
