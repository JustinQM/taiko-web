# 08 — The websocket reconnects

## The bug, found

`p2.open()` watches the socket with `pageEvents.race(socket, "open",
"close")`, and `race` removes **both** listeners as soon as either fires.
So once a connection succeeds, the close listener is gone: a disconnect
after that point is never noticed, `closeEvent` never runs, and there is
no reconnect. The retry that exists inside `closeEvent` has never been
reachable in the case it was written for.

Worse, `closeEvent` opens with `this.removeEventListener(onmessage)`, and
`onmessage` is not defined anywhere. Had it been reached it would have
thrown a ReferenceError before getting to the retry.

## What it changes

A close listener that stays attached, the ReferenceError removed, and a
backoff on the retry rather than a flat 500ms so a server that is down
is not hammered.

## How it will be shown to work

Kill the multiplayer container out from under a connected client and
watch it come back on its own; the existing two-client harness already
knows how to establish a session, so it can assert one survives a
restart.
