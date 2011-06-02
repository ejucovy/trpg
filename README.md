

Architecture
============

The game is only active when two players are both logged in to the same game room.

In the database, a game room maintains two lists of players:
 * game_room.players: The users who are currently playing the
   game. 

   1. When a player first logs in to the game room, the endpoint
      ``hookbox.subscribe`` is called by hookbox-server, and the user
      is added to the list of players.
   1. When a player leaves the game room, the endpoint
      ``hookbox.unsubscribe`` is called by hookbox-server, and the
      user is removed from the list of players.

 * game_room.ready: Used to signal turn change events within the
   game.  When two players are ready, the next turn can begin.  The
   endpoint ``views.ready`` is called from Javascript to tell
   the server when a user is ready for a turn to begin.

   1. When a player first logs in to the game room and hookbox-client
      indicates successful subscription to the game room's channel,
      the client POSTs to the ``views.ready`` endpoint to signal that
      the user is ready to start the game.
   1. When a player action (move, attack, etc) is received by a
      client, the action's animation is rendered.  When the animation
      is completed, the client POSTs to the ``views.ready`` endpoint
      to signal that the user is ready to proceed to the next turn.