# 09 — Close the socket on unload

Nothing closes the websocket when the page goes away, so a refresh leaves
the server holding a connection until it notices. On a matchmaking server
that means ghost players in the waiting list.

## What it changes

A `beforeunload` — and `pagehide`, which is the one that fires on mobile
— that closes the socket.

## How it will be shown to work

Connect, note the server's user count, reload, and see the count return
rather than climb.
